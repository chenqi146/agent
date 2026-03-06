'''
@File    :   qdrant_persistence.py
@Time    :   2025/11/25 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   Qdrant向量数据库持久化操作
'''

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger


PointType = Union[rest.PointStruct, Dict[str, Any]]


@logger()
class QDrantPersistence:
    """
    为Qdrant提供基础的增删改查能力，统一封装错误处理与日志。
    默认向量维度为512，可通过 `vector_size` 自定义。
    """

    def __init__(
        self,
        url: str,
        api_key: Optional[str],
        timeout: Optional[float] = 0,
        vector_size: int = 512,
    ):
        self.url = url
        self.api_key = api_key
        self.collection_name = None
        self.vector_size = vector_size
        self.client = QdrantClient(url=url, api_key=api_key, timeout=timeout,prefer_grpc=False)

    def _collection_exists(self) -> bool:
        if hasattr(self.client, "collection_exists"):
            return bool(self.client.collection_exists(self.collection_name))  # type: ignore[attr-defined]
        if hasattr(self.client, "has_collection"):
            return bool(self.client.has_collection(self.collection_name))  # type: ignore[attr-defined]
        # 如果都不存在，尝试通过获取集合判断
        try:
            self.client.get_collection(self.collection_name)
            return True
        except Exception:
            return False

    def init_collection(self,collection_name: str,vectors_config:Dict[str,Any]=None):
        """
        确保目标集合已经存在；如不存在则创建。
        """
        try:
            if collection_name is None:
                raise ValueError("collection_name and vectors_config are required")
            
            self.log.debug(f"init_collection - collection_name: {collection_name}")
            self.collection_name = collection_name
            if self._collection_exists():
                self.log.info(
                    "Qdrant collection %s already exists, skipping creation",
                    self.collection_name
                )
                return
            self.log.debug(f"init_collection - vectors_config: {vectors_config}")
            if vectors_config is None:  #默认使用512维向量，余弦距离
                vectors_config = rest.VectorParams(
                    size=self.vector_size,
                    distance=rest.Distance.COSINE,
                )
                '''普通的向量数据操作,元数据中没有向量字段'''
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=vectors_config,
                )
            else:
                '''向量数据,元数据中有向量字段'''
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=vectors_config,
                )
            self.log.info( f"Created Qdrant collection {self.collection_name} with vectors_config: {vectors_config}")
        except Exception as exc:
            # 如果集合已存在（409 Conflict），这是正常情况，不需要报错
            error_str = str(exc)
            if "409" in error_str or "already exists" in error_str.lower() or "Conflict" in error_str:
                self.log.info(
                    "Qdrant collection %s already exists (detected from error), skipping creation",
                    self.collection_name
                )
                return
            # 其他错误才抛出异常
            self.log.error(f"Failed to ensure Qdrant collection: {exc}")
            raise

    def _validate_vector(self, vector: Sequence[float]) -> List[float]:
        if len(vector) != self.vector_size:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.vector_size}, got {len(vector)}"
            )
        return [float(v) for v in vector]

    def _normalize_points(self, points: Iterable[PointType]) -> List[rest.PointStruct]:
        normalized: List[rest.PointStruct] = []
        for point in points:
            if isinstance(point, rest.PointStruct):
                self._validate_vector(point.vector)
                normalized.append(point)
                continue

            if not isinstance(point, dict):
                raise ValueError("Point must be PointStruct or dict with id/vector/payload")

            if "id" not in point or "vector" not in point:
                raise ValueError("Point dict must contain 'id' and 'vector'")

            normalized.append(
                rest.PointStruct(
                    id=point["id"],
                    vector=self._validate_vector(point["vector"]),
                    payload=point.get("payload"),
                )
            )
        return normalized
    

    '''向量数据,元数据中有向量字段，则直接插入。
       这里直接使用 HTTP client 支持的 PointStruct 或 dict 结构。
    '''
    def insert_point_struct(self, point: Any, collection_name: str = None) -> Tuple[ErrorCode, int]:
        try:
            target_collection = collection_name or self.collection_name
            self.client.upsert(
                collection_name=target_collection,
                points=[point],
                wait=True,
            )
            return ErrorCode.SUCCESS, 1
        except Exception as exc:
            self.log.error(f"Failed to insert point into Qdrant: {exc}")
            return ErrorCode.DATABASE_INSERT_ERROR, 0

    def delete_point_struct(
        self,
        *,
        ids: Optional[Sequence[Union[int, str]]] = None,
        filter: Optional[rest.Filter] = None,
    ) -> Tuple[ErrorCode, int]:
        """
        删除 PointStruct 类型的数据。
        实际上底层还是调用 HTTP delete，与普通 delete 逻辑一致，
        只是语义上用于“向量在 payload 中”的场景。
        """
        return self.delete(ids=ids, filter=filter)

    def query_point_struct_by_vector(
        self, 
        vectors_dict: Dict[str, List[float]], 
        limit: int = 10,
        threshold: float = 0.85
    ) -> Tuple[ErrorCode, List[Any]]:
        """
        根据多个向量进行查询，支持多向量集合。
        对每个向量进行相似度查询，合并结果并去重，按相似度排序。
        
        Args:
            vectors_dict: 字典，键为向量名称（如 "vehicle_global_vec"），值为对应的向量列表
            limit: 每个向量查询返回的最大结果数
            threshold: 相似度阈值，低于此值的结果会被过滤
            
        Returns:
            Tuple[ErrorCode, List[Any]]: (错误码, PointStruct 列表)
        """
        if not vectors_dict:
            self.log.warn("vectors_dict is empty, returning empty list")
            return ErrorCode.SUCCESS, []
        
        try:
            import requests
            from qdrant_client.http.models import ScoredPoint
            
            all_results = {}  # 使用字典存储，key 为 point id，value 为 (point, max_score)
            
            # 对每个向量进行查询
            for vector_name, query_vector in vectors_dict.items():
                if not query_vector or len(query_vector) == 0:
                    self.log.warn(f"Empty vector for {vector_name}, skipping")
                    continue
                
                try:
                    # 使用 HTTP API 查询（支持多向量集合）
                    base_url = self.url.rstrip('/')
                    url = f"{base_url}/collections/{self.collection_name}/points/search"
                    headers = {"Content-Type": "application/json"}
                    if self.api_key:
                        headers["api-key"] = self.api_key
                    
                    # ✅ 使用正确的 API 格式
                    payload = {
                        "vector": {  # 直接使用 vector 字段，而不是 query
                            "name": vector_name,  # 命名向量
                            "vector": query_vector
                        },
                        "limit": limit,
                        "score_threshold": threshold,
                        "with_payload": True,
                        "with_vector": True  # 注意字段名是 with_vector，不是 with_vectors
                    }
                    
                    self.log.debug(f"Querying vector {vector_name} (dim={len(query_vector)})")
                    response = requests.post(url, headers=headers, json=payload, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.log.debug(f"Response for {vector_name}: status=200, found {len(data.get('result', []))} results")
                        
                        if "result" in data:
                            for point_data in data["result"]:
                                if isinstance(point_data, dict):
                                    point_id = point_data.get("id")
                                    score = point_data.get("score", 0.0)
                                    
                                    # 只保留超过阈值的结果
                                    if score < threshold:
                                        continue
                                    
                                    # 如果该点已存在，保留相似度更高的
                                    if point_id in all_results:
                                        existing_score = all_results[point_id][1]
                                        if score > existing_score:
                                            # 构造 PointStruct
                                            scored_point = ScoredPoint(
                                                id=point_id,
                                                version=point_data.get("version", 0),
                                                score=score,
                                                payload=point_data.get("payload"),
                                                vector=point_data.get("vector"),
                                                shard_key=point_data.get("shard_key")
                                            )
                                            all_results[point_id] = (scored_point, score)
                                    else:
                                        # 构造 PointStruct
                                        scored_point = ScoredPoint(
                                            id=point_id,
                                            version=point_data.get("version", 0),
                                            score=score,
                                            payload=point_data.get("payload"),
                                            vector=point_data.get("vector"),
                                            shard_key=point_data.get("shard_key")
                                        )
                                        all_results[point_id] = (scored_point, score)
                        else:
                            self.log.warn(f"Unexpected response format for {vector_name}: {data}")
                    else:
                        # ✅ 更清晰的错误处理和备选方案
                        error_msg = f"Failed to query {vector_name}: status={response.status_code}"
                        try:
                            error_body = response.json()
                            error_msg += f", body={error_body}"
                        except:
                            error_msg += f", body={response.text}"
                        
                        self.log.error(error_msg)
                        
                        # 如果是因为格式错误，尝试其他可能的格式
                        if response.status_code == 400:
                            # 尝试不带 name 的简单格式（如果集合只有一个向量）
                            self.log.debug(f"Trying simple vector format for {vector_name}")
                            payload_simple = {
                                "vector": query_vector,  # 直接传向量
                                "limit": limit,
                                "score_threshold": threshold,
                                "with_payload": True,
                                "with_vector": True
                            }
                            
                            response_simple = requests.post(url, headers=headers, json=payload_simple, timeout=30)
                            if response_simple.status_code == 200:
                                data = response_simple.json()
                                self.log.debug(f"Simple format worked for {vector_name}")
                                if "result" in data:
                                    for point_data in data["result"]:
                                        if isinstance(point_data, dict):
                                            point_id = point_data.get("id")
                                            score = point_data.get("score", 0.0)
                                            
                                            if score < threshold:
                                                continue
                                            
                                            if point_id in all_results:
                                                existing_score = all_results[point_id][1]
                                                if score > existing_score:
                                                    scored_point = ScoredPoint(
                                                        id=point_id,
                                                        version=point_data.get("version", 0),
                                                        score=score,
                                                        payload=point_data.get("payload"),
                                                        vector=point_data.get("vector")
                                                    )
                                                    all_results[point_id] = (scored_point, score)
                                            else:
                                                scored_point = ScoredPoint(
                                                    id=point_id,
                                                    version=point_data.get("version", 0),
                                                    score=score,
                                                    payload=point_data.get("payload"),
                                                    vector=point_data.get("vector")
                                                )
                                                all_results[point_id] = (scored_point, score)
                            else:
                                self.log.error(f"Simple format also failed: status={response_simple.status_code}")
                            
                except Exception as e:
                    self.log.error(f"Error querying vector {vector_name}: {e}", exc_info=True)
                    continue
            
            # 将结果转换为 PointStruct 列表，并按相似度排序
            results = [point for point, score in all_results.values()]
            # 按相似度降序排序
            results.sort(key=lambda x: getattr(x, 'score', 0.0), reverse=True)
            
            # 限制返回数量
            if len(results) > limit:
                results = results[:limit]
            
            self.log.debug(f"query_point_struct_by_vector returned {len(results)} unique results from {len(vectors_dict)} vectors")
            return ErrorCode.SUCCESS, results
            
        except ImportError as e:
            self.log.error(f"Failed to import requests: {e}. Please install requests library.")
            return ErrorCode.DATABASE_QUERY_ERROR, []
        except Exception as e:
            self.log.error(f"Failed to query by vectors: {e}", exc_info=True)
            return ErrorCode.DATABASE_QUERY_ERROR, []

    def query_point_struct(
        self,
        *,
        collection_name: str = None,
        limit: int = 10,
        offset: Optional[int] = None,
        filter: Optional[rest.Filter] = None,
        with_payload: bool = True,
        with_vectors: bool = True,
    ) -> Tuple[ErrorCode, List[Any]]:
        """
        以 PointStruct 形式查询数据（适用于向量在 payload 中的场景）。
        使用 scroll 接口按过滤条件分页拉取，不做向量相似度排序。
        """
        try:
            target_collection = collection_name or self.collection_name
            points, next_page = self.client.scroll(
                collection_name=target_collection,
                scroll_filter=filter,
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vectors=with_vectors,
            )
            # points 已经是 PointStruct 列表
            return ErrorCode.SUCCESS, list(points)
        except Exception as exc:
            self.log.error(f"Failed to scroll/query PointStructs from Qdrant: {exc}")
            return ErrorCode.DATABASE_QUERY_ERROR, []

    def update_point_struct(self, point: Any) -> Tuple[ErrorCode, int]:
        """
        更新单个 PointStruct（向量或 payload）
        本质上是一次 upsert：同 id 则覆盖，新的则插入。
        直接接受 HTTP PointStruct 或 dict，底层统一使用 upsert。
        """
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
                wait=True,
            )
            return ErrorCode.SUCCESS, 1
        except Exception as exc:
            self.log.error(f"Failed to update PointStruct in Qdrant: {exc}")
            return ErrorCode.DATABASE_UPDATE_ERROR, 0

    def query_by_file_id(
        self,
        file_id: int,
        *,
        collection_name: str = None,
        limit: int = 1,
    ) -> Tuple[ErrorCode, List[Any]]:
        """
        根据 file_id 查询向量化记录
        """
        try:
            target_collection = collection_name or self.collection_name
            filter_condition = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="file_id",
                        match=rest.MatchValue(value=file_id)
                    )
                ]
            )
            
            points, next_page = self.client.scroll(
                collection_name=target_collection,
                scroll_filter=filter_condition,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            
            return ErrorCode.SUCCESS, list(points)
        except Exception as exc:
            self.log.error(f"Failed to query by file_id from Qdrant: {exc}")
            return ErrorCode.DATABASE_QUERY_ERROR, []

    '''普通的向量数据操作,元数据中没有向量字段'''
    def insert(self, points: Sequence[PointType]) -> Tuple[ErrorCode, int]:
        """
        插入/更新一批向量。
        Args:
            points: list[dict|PointStruct]，字典需要包含 id/vector/payload
        """
        if not points:
            return ErrorCode.SUCCESS, 0

        try:
            normalized = self._normalize_points(points)
            self.client.upsert(
                collection_name=self.collection_name,
                points=normalized,
                wait=True,
            )
            return ErrorCode.SUCCESS, len(normalized)
        except ValueError as err:
            self.log.error(f"Invalid point data: {err}")
            return ErrorCode.INVALID_PARAMETER, 0
        except Exception as exc:
            self.log.error(f"Failed to insert points into Qdrant: {exc}")
            return ErrorCode.DATABASE_INSERT_ERROR, 0

    def delete(
        self,
        *,
        ids: Optional[Sequence[Union[int, str]]] = None,
        filter: Optional[rest.Filter] = None,
        collection_name: Optional[str] = None,
    ) -> Tuple[ErrorCode, int]:
        """
        删除指定id或满足过滤条件的数据。
        至少需要提供 `ids` 或 `filter` 其中之一。
        collection_name 可选，不传则使用默认集合。
        """
        if not ids and filter is None:
            return ErrorCode.INVALID_PARAMETER, 0

        target = collection_name or self.collection_name
        try:
            if ids:
                points_selector = rest.PointIdsList(points=list(ids))
            else:
                points_selector = rest.FilterSelector(filter=filter)
            result = self.client.delete(
                collection_name=target,
                points_selector=points_selector,
                wait=True,
            )
            affected = getattr(result, "result", None)
            if affected and hasattr(affected, "points"):
                # 某些版本会返回删除数量
                return ErrorCode.SUCCESS, len(affected.points)  # type: ignore[attr-defined]
            return ErrorCode.SUCCESS, 0
        except Exception as exc:
            self.log.error(f"Failed to delete points from Qdrant: {exc}")
            return ErrorCode.DATABASE_DELETE_ERROR, 0

    def query(
        self,
        vector: Sequence[float],
        *,
        limit: int = 10,
        filter: Optional[rest.Filter] = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        score_threshold: Optional[float] = None,
    ) -> Tuple[ErrorCode, List[rest.ScoredPoint]]:
        """
        基于向量相似度的查询。
        """
        try:
            query_vector = self._validate_vector(vector)
            # 兼容不同版本 qdrant-client（老版本、新版 HTTP、未来版本）
            if hasattr(self.client, "query_points"):
                # 新版官方推荐接口
                result = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    query_filter=filter,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    score_threshold=score_threshold,
                )
            elif hasattr(self.client, "points") and hasattr(self.client.points, "search"):
                # 部分版本通过 client.points.search
                result = self.client.points.search(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    query_filter=filter,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    score_threshold=score_threshold,
                )
            elif hasattr(self.client, "search_points"):
                # 某些版本提供 client.search_points
                result = self.client.search_points(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=filter,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    score_threshold=score_threshold,
                )
            elif hasattr(self.client, "search"):
                # 旧版 client.search
                result = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=filter,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    score_threshold=score_threshold,
                )
            else:
                raise AttributeError("QdrantClient has no compatible search method (query_points / points.search / search_points / search)")
            
            # 部分接口会返回带 .points 的响应对象（如 QueryResponse），统一归一化为 ScoredPoint 列表
            if hasattr(result, "points"):
                points = getattr(result, "points")
            else:
                points = result

            # 确保返回的是 list
            return ErrorCode.SUCCESS, list(points)
        except ValueError as err:
            self.log.error(f"Invalid query vector: {err}")
            return ErrorCode.INVALID_PARAMETER, []
        except Exception as exc:
            self.log.error(f"Failed to query Qdrant: {exc}")
            return ErrorCode.DATABASE_QUERY_ERROR, []

    def query_by_vector(
        self,
        query_vector: List[float],
        *,
        collection_name: str = None,
        limit: int = 10,
        score_threshold: float = 0.5,
        with_payload: bool = True,
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """
        根据向量搜索相似点（支持指定集合名）
        
        Args:
            query_vector: 查询向量
            collection_name: 集合名称（可选，默认使用当前集合）
            limit: 返回的最大数量
            score_threshold: 相似度阈值
            with_payload: 是否返回 payload
        
        Returns:
            Tuple[ErrorCode, List[Dict]]: (错误码, 结果列表)
            每个结果包含: id, score, payload
        """
        try:
            target_collection = collection_name or self.collection_name
            # 不使用 _validate_vector，因为不同集合有不同的向量维度
            query_vector = [float(v) for v in query_vector]
            
            # 使用 search 方法
            if hasattr(self.client, "search"):
                results = self.client.search(
                    collection_name=target_collection,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=with_payload,
                    score_threshold=score_threshold,
                )
            elif hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=target_collection,
                    query=query_vector,
                    limit=limit,
                    with_payload=with_payload,
                    score_threshold=score_threshold,
                )
                results = getattr(response, 'points', response)
            else:
                self.log.error("No compatible search method found")
                return ErrorCode.INTERNAL_ERROR, []
            
            # 格式化结果
            formatted = []
            for point in results:
                formatted.append({
                    'id': getattr(point, 'id', None),
                    'score': getattr(point, 'score', 0.0),
                    'payload': getattr(point, 'payload', {}) or {},
                })
            
            return ErrorCode.SUCCESS, formatted
            
        except ValueError as err:
            self.log.error(f"Invalid query vector: {err}")
            return ErrorCode.INVALID_PARAMETER, []
        except Exception as exc:
            self.log.error(f"query_by_vector failed: {exc}", exc_info=True)
            return ErrorCode.DATABASE_QUERY_ERROR, []

    def query_by_vector_with_filter(
        self,
        query_vector: List[float],
        *,
        collection_name: str = None,
        qdrant_filter: Dict[str, Any] = None,
        limit: int = 10,
        score_threshold: float = 0.5,
        with_payload: bool = True,
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """
        带过滤条件的向量搜索
        
        Args:
            query_vector: 查询向量
            collection_name: 集合名称（可选）
            qdrant_filter: Qdrant 过滤条件，格式:
                {
                    'must': [
                        {'key': 'field_name', 'match': {'value': 'xxx'}},
                        ...
                    ]
                }
            limit: 返回的最大数量
            score_threshold: 相似度阈值
            with_payload: 是否返回 payload
        
        Returns:
            Tuple[ErrorCode, List[Dict]]: (错误码, 结果列表)
        """
        try:
            target_collection = collection_name or self.collection_name
            # 不使用 _validate_vector，因为不同集合有不同的向量维度
            # 向量维度验证应该在调用方（repository层）完成
            query_vector = [float(v) for v in query_vector]
            
            # 构建 Qdrant Filter 对象
            filter_obj = None
            if qdrant_filter and qdrant_filter.get('must'):
                must_conditions = []
                for cond in qdrant_filter['must']:
                    key = cond.get('key')
                    match = cond.get('match', {})
                    value = match.get('value')
                    if key and value is not None:
                        must_conditions.append(
                            rest.FieldCondition(
                                key=key,
                                match=rest.MatchValue(value=value)
                            )
                        )
                
                if must_conditions:
                    filter_obj = rest.Filter(must=must_conditions)
                    self.log.debug(f"Created filter with {len(must_conditions)} conditions")
            
            # 使用 search 方法（带过滤）
            if hasattr(self.client, "search"):
                results = self.client.search(
                    collection_name=target_collection,
                    query_vector=query_vector,
                    query_filter=filter_obj,
                    limit=limit,
                    with_payload=with_payload,
                    score_threshold=score_threshold,
                )
            elif hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=target_collection,
                    query=query_vector,
                    query_filter=filter_obj,
                    limit=limit,
                    with_payload=with_payload,
                    score_threshold=score_threshold,
                )
                results = getattr(response, 'points', response)
            else:
                self.log.error("No compatible search method found")
                return ErrorCode.INTERNAL_ERROR, []
            
            # 格式化结果
            formatted = []
            for point in results:
                formatted.append({
                    'id': getattr(point, 'id', None),
                    'score': getattr(point, 'score', 0.0),
                    'payload': getattr(point, 'payload', {}) or {},
                })
            
            self.log.debug(f"Filtered search found {len(formatted)} results")
            return ErrorCode.SUCCESS, formatted
            
        except ValueError as err:
            self.log.error(f"Invalid query vector for filtered search: {err}")
            return ErrorCode.INVALID_PARAMETER, []
        except Exception as exc:
            self.log.error(f"query_by_vector_with_filter failed: {exc}", exc_info=True)
            return ErrorCode.DATABASE_QUERY_ERROR, []

    def update(
        self,
        point_id: Union[int, str],
        *,
        collection_name: str = None,
        vector: Optional[Sequence[float]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ErrorCode, int]:
        """
        更新单个向量或其payload。
        如果同时提供 vector & payload，则执行一次 upsert；
        若仅payload，会调用 set_payload。
        """
        if vector is None and payload is None:
            return ErrorCode.INVALID_PARAMETER, 0

        target_collection = collection_name or self.collection_name
        
        try:
            if vector is not None:
                point = rest.PointStruct(
                    id=point_id,
                    vector=self._validate_vector(vector),
                    payload=payload,
                )
                self.client.upsert(
                    collection_name=target_collection,
                    points=[point],
                    wait=True,
                )
            else:
                self.client.set_payload(
                    collection_name=target_collection,
                    payload=payload or {},
                    points=[point_id],
                    wait=True,
                )
            return ErrorCode.SUCCESS, 1
        except ValueError as err:
            self.log.error(f"Invalid update payload: {err}")
            return ErrorCode.INVALID_PARAMETER, 0
        except Exception as exc:
            self.log.error(f"Failed to update Qdrant point: {exc}")
            return ErrorCode.DATABASE_UPDATE_ERROR, 0

    def count(self) -> Tuple[ErrorCode, int]:
        """
        返回集合中的点数量。
        """
        try:
            info = self.client.get_collection(self.collection_name)
            points_count = getattr(info, "points_count", None)
            if points_count is None and hasattr(info, "result"):
                points_count = getattr(info.result, "points_count", 0)
            return ErrorCode.SUCCESS, points_count or 0
        except Exception as exc:
            self.log.error(f"Failed to count Qdrant points: {exc}")
            return ErrorCode.DATABASE_QUERY_ERROR, 0