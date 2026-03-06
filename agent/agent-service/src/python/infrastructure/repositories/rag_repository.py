from typing import Any, Dict, List, Tuple, Optional

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.config.sys_config import SysConfig
from infrastructure.persistences.mysql_persistence import MysqlPersistence


@logger()
class RagRepository:
    """
    RAG 知识库持久化仓储
    - 负责对 rag_tbl / rag_file_tbl 的所有 MySQL 访问
    - 不包含任何业务规则，只做数据读写
    """

    def __init__(self, config: SysConfig, mysql_client=None):
        if mysql_client:
            self.mysql = mysql_client
        else:
            # 兼容性：如果没有传入mysql_client，则从配置创建
            system_cfg = config.get_system_config() or {}
            mysql_cfg = system_cfg.get("persistence", {}).get("mysql", {}) or {}
            self.mysql = MysqlPersistence(
                host=mysql_cfg.get("host", "127.0.0.1"),
                port=mysql_cfg.get("port", 3306),
                username=mysql_cfg.get("username", "root"),
                password=mysql_cfg.get("password", ""),
                database=mysql_cfg.get("database", "pg-platform-db"),
                charset=mysql_cfg.get("charset", "utf8mb4"),
            )
        self.log.info(
            f"RagRepository initialized with MySQL[{self.mysql.host}:{self.mysql.port}/{self.mysql.database}]"
        )

    # ---------- rag_tbl ----------

    def exists_by_name(
        self,
        name: str,
        binding_user_id: int,
        exclude_id: Optional[int] = None,
    ) -> Tuple[ErrorCode, bool]:
        """检查 rag_tbl 中 rag_name 是否存在（同用户下），支持排除某个 id（更新时使用）"""
        if exclude_id is None:
            return self.mysql.exists(
                "rag_tbl", "rag_name = %s AND binding_user_id = %s", params=(name, binding_user_id)
            )
        return self.mysql.exists(
            "rag_tbl",
            "rag_name = %s AND binding_user_id = %s AND id <> %s",
            params=(name, binding_user_id, exclude_id),
        )

    def insert_knowledge_base(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        """插入一条知识库记录，返回 (错误码, 新ID)"""
        return self.mysql.insert("rag_tbl", data)

    def get_knowledge_base_by_id(
        self, kb_id: int, binding_user_id: Optional[int] = None
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """根据 ID 查询单个知识库；若传 binding_user_id 则校验归属"""
        if binding_user_id is not None:
            return self.mysql.select_one(
                "rag_tbl",
                condition="id = %s AND binding_user_id = %s",
                params=(kb_id, binding_user_id),
            )
        return self.mysql.select_one("rag_tbl", condition="id = %s", params=(kb_id,))

    def update_knowledge_base(self, kb_id: int, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        """更新知识库"""
        return self.mysql.update(
            "rag_tbl", data=data, condition="id = %s", params=(kb_id,)
        )

    def calc_kb_file_stats(self, kb_id: int) -> Tuple[ErrorCode, Tuple[int, int]]:
        """
        计算指定知识库下已完成嵌入文件的总字符数和文件数
        返回 (错误码, (total_chars, file_count))
        """
        err, rows = self.mysql.select(
            "rag_file_tbl",
            columns=[
                "COALESCE(SUM(file_char_count), 0) AS total_chars",
                "COUNT(*) AS file_count",
            ],
            condition="rag_id = %s AND status = 1 AND embedding_process = 3",
            params=(kb_id,),
        )
        if err != ErrorCode.SUCCESS:
            return err, (0, 0)
        row = rows[0] if rows else {}
        total_chars = int(row.get("total_chars", 0) or 0)
        file_count = int(row.get("file_count", 0) or 0)
        return ErrorCode.SUCCESS, (total_chars, file_count)

    def update_kb_file_stats(
        self, kb_id: int, file_capacity: int, file_count: int
    ) -> Tuple[ErrorCode, int]:
        """更新知识库的容量和文件数量"""
        data = {
            "file_capacity": int(file_capacity),
            "file_count": int(file_count),
        }
        return self.update_knowledge_base(kb_id, data)

    def delete_knowledge_base(self, kb_id: int) -> Tuple[ErrorCode, int]:
        """删除知识库主表记录（调用方需先删 rag_file_tbl，并在事务内调用）"""
        return self.mysql.delete(
            "rag_tbl", condition="id = %s", params=(kb_id,)
        )

    def delete_files_by_kb(self, kb_id: int) -> Tuple[ErrorCode, int]:
        """删除指定知识库下所有文件记录（rag_file_tbl），应在事务内与 delete_knowledge_base 一起使用"""
        return self.mysql.delete(
            "rag_file_tbl", condition="rag_id = %s", params=(kb_id,)
        )

    def delete_file_by_id(self, file_id: int) -> Tuple[ErrorCode, int]:
        """按文件ID删除单个文件记录"""
        return self.mysql.delete(
            "rag_file_tbl", condition="id = %s", params=(file_id,)
        )

    def begin_transaction(self) -> ErrorCode:
        """开启 MySQL 事务（与 commit/rollback 配合使用）"""
        return self.mysql.begin_transaction()

    def commit(self) -> ErrorCode:
        """提交 MySQL 事务"""
        return self.mysql.commit()

    def rollback(self) -> ErrorCode:
        """回滚 MySQL 事务"""
        return self.mysql.rollback()

    def count_knowledge_bases(
        self,
        binding_user_id: int,
        keyword: Optional[str] = None,
    ) -> Tuple[ErrorCode, int]:
        """统计当前用户知识库数量，支持名称关键字模糊搜索"""
        condition = "binding_user_id = %s"
        params: Tuple[Any, ...] = (binding_user_id,)
        if keyword:
            condition += " AND rag_name LIKE %s"
            params = (binding_user_id, f"%{keyword}%")
        return self.mysql.count("rag_tbl", condition=condition, params=params)

    def list_knowledge_bases(
        self,
        binding_user_id: int,
        keyword: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """
        分页查询当前用户知识库列表
        使用 rag_tbl 与 rag_file_tbl 关联统计文件容量与数量：
        - file_capacity: 该知识库下已完成嵌入文件的总字符数
        - file_count:   该知识库下已完成嵌入文件的数量
        """
        sql = """
SELECT
    k.*,
    COALESCE(fs.total_chars, 0) AS file_capacity,
    COALESCE(fs.file_count, 0) AS file_count
FROM rag_tbl AS k
LEFT JOIN (
    SELECT
        rag_id,
        COALESCE(SUM(file_char_count), 0) AS total_chars,
        COUNT(*) AS file_count
    FROM rag_file_tbl
    WHERE status = 1 AND embedding_process = 3
    GROUP BY rag_id
) AS fs ON fs.rag_id = k.id
WHERE k.binding_user_id = %s
"""
        params: list[Any] = [binding_user_id]
        if keyword:
            sql += " AND k.rag_name LIKE %s"
            params.append(f"%{keyword}%")
        sql += " ORDER BY k.create_time DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        return self.mysql.execute_sql(sql, tuple(params))

    # ---------- rag_file_tbl ----------

    def list_files_by_kb(
        self, kb_id: int, limit: int
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """按知识库 ID 查询部分文件记录，用于构造 RAG 来源信息"""
        return self.mysql.select(
            "rag_file_tbl",
            condition="rag_id = %s",
            params=(kb_id,),
            order_by="upload_time DESC",
            limit=limit,
        )

    def get_file_by_id(self, file_id: int) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """根据文件ID查询文件记录"""
        err, row = self.mysql.select_one(
            "rag_file_tbl",
            condition="id = %s",
            params=(file_id,),
        )
        return err, row

    def get_file_by_name_and_kb(
        self, file_name: str, kb_id: int
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """根据文件名和知识库ID查询文件记录"""
        return self.mysql.select_one(
            "rag_file_tbl",
            condition="file_name = %s AND rag_id = %s",
            params=(file_name, kb_id),
        )

    def insert_file_record(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        """插入一条 rag_file_tbl 文件记录"""
        return self.mysql.insert("rag_file_tbl", data)

    def update_file_record(self, file_id: int, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        """按文件ID更新 rag_file_tbl 记录（如 embedding_process、file_embedding_offset 等）"""
        return self.mysql.update(
            "rag_file_tbl", data=data, condition="id = %s", params=(file_id,)
        )

    def list_knowledge_items_by_kb(
        self,
        kb_id: int,
        min_recall_count: Optional[int] = None,
        max_recall_count: Optional[int] = None,
        recent_days: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        # 使用 LEFT JOIN 聚合查询实时计算 recall_count
        sql = """
SELECT
    f.id,
    f.file_name,
    CAST(COALESCE(SUM(s.recall_count), 0) AS UNSIGNED) as recall_count,
    f.upload_time
FROM rag_file_tbl f
LEFT JOIN rag_knowledge_segment_tbl s ON f.id = s.file_id
WHERE f.rag_id = %s AND f.status = 1 AND f.embedding_process = 3
"""
        params: list[Any] = [kb_id]
        
        # WHERE 条件 (针对 f 表字段)
        if recent_days is not None:
            sql += " AND f.upload_time >= DATE_SUB(NOW(), INTERVAL %s DAY)"
            params.append(int(recent_days))
            
        sql += " GROUP BY f.id, f.file_name, f.upload_time"

        # HAVING 条件 (针对聚合后的 recall_count)
        having_clauses = []
        if min_recall_count is not None:
            having_clauses.append("recall_count >= %s")
            params.append(int(min_recall_count))
        if max_recall_count is not None:
            having_clauses.append("recall_count <= %s")
            params.append(int(max_recall_count))
            
        if having_clauses:
            sql += " HAVING " + " AND ".join(having_clauses)

        # ORDER BY
        if sort_by == "upload_time":
            order_column = "f.upload_time"
        else:
            order_column = "recall_count"

        direction = "ASC" if sort_order and sort_order.lower() == "asc" else "DESC"

        if order_column == "recall_count":
            sql += f" ORDER BY recall_count {direction}, f.upload_time DESC"
        else:
            sql += f" ORDER BY {order_column} {direction}, recall_count DESC"

        return self.mysql.execute_sql(sql, tuple(params))

    # ---------- rag_knowledge_segment_tbl ----------
    def insert_segment(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        """插入一条知识片段记录，返回 (错误码, 新ID)"""
        return self.mysql.insert("rag_knowledge_segment_tbl", data)

    def delete_segments_by_file(self, file_id: int) -> Tuple[ErrorCode, int]:
        """按文件ID删除该文件下的所有知识片段"""
        return self.mysql.delete(
            "rag_knowledge_segment_tbl", condition="file_id = %s", params=(file_id,)
        )

    def delete_segments_by_kb(self, kb_id: int) -> Tuple[ErrorCode, int]:
        """按知识库ID删除该知识库下所有文件的知识片段"""
        sql = """
        DELETE s FROM rag_knowledge_segment_tbl s
        INNER JOIN rag_file_tbl f ON s.file_id = f.id
        WHERE f.rag_id = %s
        """
        return self.mysql.execute_non_query(sql, params=(kb_id,))

    def list_segments_by_file(
        self,
        file_id: int,
        status: Optional[int],
        binding_user_id: Optional[int],
        limit: int,
        offset: int,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """
        查询指定文件下的知识片段列表。
        """
        condition = "file_id = %s"
        params: list[Any] = [file_id]
        if binding_user_id is not None:
            condition += " AND binding_user_id = %s"
            params.append(int(binding_user_id))
        if status is not None:
            condition += " AND status = %s"
            params.append(int(status))

        # 构建排序逻辑
        # 默认：sort_index ASC, update_time DESC
        order_by_clause = "sort_index ASC, update_time DESC"
        
        direction = "ASC" if sort_order and sort_order.lower() == "asc" else "DESC"

        if sort_by == "recall_count":
             # 召回次数排序
             order_by_clause = f"recall_count {direction}, update_time DESC"
        elif sort_by == "updated_at":
             # 更新时间排序
             order_by_clause = f"update_time {direction}"

        return self.mysql.select(
            "rag_knowledge_segment_tbl",
            columns=[
                "id",
                "title",
                "content",
                "summary",
                "snippet_type",
                "sort_index",
                "status",
                "recall_count",
                "last_search_time",
                "average_retrieval_score",
                "command_score",
                "relevance_score",
                "is_noise",
                "is_redundant",
                "qdrant_vector_id",
                "neo4j_node_id",
                "create_time",
                "update_time",
            ],
            condition=condition,
            params=tuple(params),
            order_by=order_by_clause,
            limit=limit,
            offset=offset,
        )

    def update_segment(self, segment_id: int, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        """更新知识片段"""
        return self.mysql.update(
            "rag_knowledge_segment_tbl",
            data=data,
            condition="id = %s",
            params=(segment_id,)
        )

    def delete_segment(self, segment_id: int) -> Tuple[ErrorCode, int]:
        """根据ID删除单个知识片段"""
        return self.mysql.delete(
            "rag_knowledge_segment_tbl",
            condition="id = %s",
            params=(segment_id,)
        )

    def get_segment_by_id(self, segment_id: int) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """根据ID查询单个知识片段"""
        return self.mysql.select_one(
            "rag_knowledge_segment_tbl",
            condition="id = %s",
            params=(segment_id,)
        )



    def get_segments_by_ids(self, segment_ids: List[int]) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """根据ID列表批量查询知识片段"""
        if not segment_ids:
            return ErrorCode.SUCCESS, []
        placeholders = ",".join(["%s"] * len(segment_ids))
        return self.mysql.select(
            "rag_knowledge_segment_tbl",
            condition=f"id IN ({placeholders})",
            params=tuple(segment_ids),
        )

    def increment_segment_recall(self, segment_ids: List[int]) -> Tuple[ErrorCode, int]:
        """批量增加知识片段的召回次数"""
        if not segment_ids:
            return ErrorCode.SUCCESS, 0
        placeholders = ",".join(["%s"] * len(segment_ids))
        sql = f"UPDATE rag_knowledge_segment_tbl SET recall_count = recall_count + 1, last_search_time = NOW() WHERE id IN ({placeholders})"
        return self.mysql.execute_non_query(sql, params=tuple(segment_ids))

    def get_max_sort_index(self, file_id: int) -> Tuple[ErrorCode, int]:
        """获取指定文件下最大的排序索引"""
        sql = "SELECT MAX(sort_index) as max_idx FROM rag_knowledge_segment_tbl WHERE file_id = %s"
        err, rows = self.mysql.execute_sql(sql, params=(file_id,))
        if err != ErrorCode.SUCCESS:
            return err, 0
        if rows and rows[0].get("max_idx") is not None:
            return ErrorCode.SUCCESS, int(rows[0]["max_idx"])
        return ErrorCode.SUCCESS, -1  # 如果没有记录，返回-1，使得下一个是0

    def get_total_recall_count(self) -> Tuple[ErrorCode, int]:
        """获取所有知识片段的总召回次数"""
        sql = "SELECT CAST(COALESCE(SUM(recall_count), 0) AS UNSIGNED) as total_recall FROM rag_knowledge_segment_tbl"
        err, rows = self.mysql.execute_sql(sql)
        if err != ErrorCode.SUCCESS:
            return err, 0
        return ErrorCode.SUCCESS, int(rows[0]["total_recall"]) if rows else 0
