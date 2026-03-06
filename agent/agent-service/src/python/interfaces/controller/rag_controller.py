from fastapi import FastAPI, Depends, UploadFile, File, Form
import time
import os
import uuid
import asyncio
import traceback
from io import BytesIO

from minio import Minio

from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

from interfaces.dto.response_dto import ApiResponse, ok, fail
from interfaces.deps.user_context import UserContext, get_validated_user_context
from interfaces.controller.base_controller import BaseController
from interfaces.dto.rag_dto import (
    KnowledgeBaseCreateApiRequest,
    KnowledgeBaseUpdateApiRequest,
    KnowledgeBaseIdApiRequest,
    KnowledgeBaseListApiRequest,
    FileProcessApiRequest,
    FileVectorizationStatusApiRequest,
    FileIdWithKbApiRequest,
    FileUpdateStatusApiRequest,
    KnowledgeItemListApiRequest,
    KnowledgeSegmentListApiRequest,
    KnowledgeSegmentUpdateApiRequest,
    KnowledgeSegmentCreateApiRequest,
    KnowledgeSegmentIdApiRequest,
    OntologyNodeCreateApiRequest,
    OntologyNodeUpdateApiRequest,
    OntologyNodeDeleteApiRequest,
    OntologyNodeListApiRequest,
    HybridRagQueryApiRequest,
)
from domain.service.rag_service import RagService

""" RAG混合检索
[阶段1: 向量初筛]
输入查询 → 向量化 → Qdrant相似性搜索 → 获取Top-N初筛结果
    ↓
[阶段2: 元数据过滤]
初筛结果 → MySQL元数据/关键词过滤 → 过滤后结果
    ↓
[阶段3: 语义扩展]
过滤结果 → 提取关键实体 → Neo4j图遍历/推理 → 获取相关概念
    ↓
[阶段4: 二次检索增强]
相关概念 + 原始查询 → 构造增强查询 → Qdrant二次检索 → 增强结果
    ↓
[阶段5: 结果映射与合并]
增强结果 → 映射到MySQL知识片段 → 片段合并策略 → 最终输出
"""


@logger()
class RagController(BaseController):
    """
    RAG 控制器 - 知识库管理与检索接口（接口层，仅做编排，不包含具体实现细节）
    """

    def __init__(self, config: SysConfig, web_app: FastAPI, rag_service: RagService):
        self.config = config
        self.app = web_app
        self._start_time = time.time()
        self._app_name = "pg-agent-application"
        self._version = self._get_version_from_config()
        
        # 接收客户端实例
        self.rag_service = rag_service
        self.mysql_client = rag_service._mysql
        self.minio_client = rag_service._minio_client
        self.qdrant_client = rag_service._qdrant
        
        # MinIO 配置
        system_cfg = self.config.get_system_config() or {}
        persistence_cfg = system_cfg.get("persistence", {}) or {}
        minio_cfg = persistence_cfg.get("minio", {}) or {}
        self._minio_bucket = minio_cfg.get("bucket", "rag-files")
        
        # 确保MinIO桶存在（如果minio_client可用）
        if self.minio_client:
            try:
                if not self.minio_client.bucket_exists(self._minio_bucket):
                    self.minio_client.make_bucket(self._minio_bucket)
            except Exception:
                # 这里不抛出异常，避免影响服务启动；具体错误在实际上传时再返回
                pass
        
        # 注册路由
        self._register_routes()

    def _get_version_from_config(self) -> str:
        """从配置中获取版本号（与其它 Controller 保持一致风格）"""
        try:
            system_config = self.config.get_system_config()
            return system_config.get("version", "1.0.0")
        except Exception:
            return "1.0.0"

    def _register_routes(self):
        """注册所有 RAG 相关路由"""

        @self.app.post("/v1/agent/rag/kb/file/upload", response_model=ApiResponse)
        async def upload_kb_file(
            file: UploadFile = File(...),
            kb_id: str = Form(None),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """
            上传知识库文件到 MinIO，返回对象名（filename）供后续 process 使用。
            不创建 DB 记录，file_id 由 process 接口写入。
            """
            if not self.minio_client:
                return fail(ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, "MinIO 未配置或不可用")
            user_id = int(user_ctx.user_id)
            prefix = (kb_id or "").strip() or "temp"
            safe_name = (file.filename or "unnamed").replace("..", "_").strip()
            object_name = f"{prefix}/{uuid.uuid4().hex}_{safe_name}"
            try:
                content = await file.read()
                length = len(content)
                self.minio_client.put_object(
                    self._minio_bucket,
                    object_name,
                    BytesIO(content),
                    length,
                    content_type=file.content_type or "application/octet-stream",
                )
            except Exception as e:
                self.log.error(f"upload_kb_file: MinIO put_object failed: {e}")
                return fail(ErrorCode.EXTERNAL_SERVICE_ERROR, f"文件上传失败: {e}")
            return ok({"filename": object_name})

        def _process_kb_file_sync(user_id: int, data, kb_id: int):
            """同步执行 DB 校验与写入，避免阻塞事件循环；返回 (err_code, err_msg, file_id)。"""
            err, row = self.rag_service.repo.get_knowledge_base_by_id(kb_id, binding_user_id=user_id)
            if err != ErrorCode.SUCCESS or not row:
                return (ErrorCode.DATA_NOT_FOUND, "知识库不存在或无权操作", None)
            file_info = data.fileInfo
            file_char_count = getattr(file_info, "charCount", None) or 0
            name = getattr(file_info, "name", None) or ""
            _, file_ext = os.path.splitext(name)
            chunk_strategy = getattr(data.chunkStrategy, "value", data.chunkStrategy)
            if not isinstance(chunk_strategy, str):
                chunk_strategy = str(chunk_strategy)
            insert_data = {
                "file_name": name,
                "file_path": data.filename,
                "extension": (file_ext.lstrip(".") or "").lower(),
                "status": 1,
                "file_char_count": int(file_char_count),
                "recall_count": 0,
                "rag_id": kb_id,
                "binding_user_id": user_id,
                "segmentation_type": chunk_strategy,
                "embedding_process": 0,
                "file_embedding_offset": 0,
            }
            err_check, is_vectorized = self.rag_service.check_file_vectorized(name, kb_id)
            if err_check != ErrorCode.SUCCESS:
                return (err_check, "检查文件向量化状态失败", None)
            if is_vectorized:
                return (None, None, None)
            err2, file_id = self.rag_service.repo.insert_file_record(insert_data)
            if err2 != ErrorCode.SUCCESS:
                return (err2, "保存文件记录失败", None)
            return (None, None, file_id)

        @self.app.post("/v1/agent/rag/kb/file/process", response_model=ApiResponse)
        async def process_kb_file(
            request: FileProcessApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """
            处理已上传的知识库文件：校验知识库、写 DB、异步启动向量化。
            同步 DB 操作放入线程执行，避免阻塞事件循环导致 process/status 同时 pending。
            """
            try:
                user_id = int(user_ctx.user_id)
                data = request.data
                kb_id = data.kbId
                if kb_id is None:
                    return fail(ErrorCode.INVALID_PARAMETER, "kbId 不能为空")

                err_code, err_msg, file_id = await asyncio.to_thread(
                    _process_kb_file_sync, user_id, data, kb_id
                )
                if err_code is not None:
                    return fail(err_code, err_msg or "处理失败")
                if file_id is None:
                    return ok({"message": "文件已向量化", "file_id": None})

                try:
                    asyncio.create_task(
                        self._async_embed_and_index_file(
                            kb_id=kb_id,
                            file_id=file_id,
                            binding_user_id=user_id,
                            object_name=data.filename,
                            bucket=self._minio_bucket,
                        )
                    )
                    self.log.info(f"Started async embedding task for file_id: {file_id}")
                except Exception as e:
                    self.log.error(f"Failed to start async embedding task: {e}")
                    return fail(ErrorCode.SYSTEM_ERROR, str(e))

                self.log.info(f"Process response for file_id={file_id}, kb_id={kb_id}")
                return ok({
                    "file_id": file_id,
                    "message": "文件处理已开始，请通过状态查询接口检查进度",
                    "processing_status": "started",
                })
            except Exception as e:
                self.log.error("process_kb_file error: %s\n%s", e, traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/rag/kb/file/status", response_model=ApiResponse)
        async def get_file_vectorization_status(
            request: FileVectorizationStatusApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """查询文件向量化状态（仅当前用户绑定的知识库）。同步 DB/Redis 放入线程，避免阻塞事件循环。"""
            try:
                user_id = int(user_ctx.user_id)
                revalue, result = await asyncio.to_thread(
                    self.rag_service.get_file_vectorization_status, request.data, user_id
                )
                if revalue == ErrorCode.SUCCESS:
                    try:
                        data = result.model_dump() if hasattr(result, "model_dump") else {}
                    except Exception as ser:
                        self.log.warning("status model_dump failed: %s", ser)
                        data = {}
                    return ok(data)
                msg = getattr(result, "error_message", None) or (str(result) if result is not None else "查询失败")
                data = result.model_dump() if hasattr(result, "model_dump") else None
                return fail(revalue, msg, data)
            except Exception as e:
                self.log.error("get_file_vectorization_status error: %s\n%s", e, traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/rag/kb/segment/list", response_model=ApiResponse)
        async def list_segments(
            request: KnowledgeSegmentListApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """按文件ID查询知识片段列表"""
            try:
                user_id = int(user_ctx.user_id)
                err, data = await self.rag_service.list_segments(request.data, user_id)
                if err == ErrorCode.SUCCESS:
                    return ok(data)
                return fail(err, data if isinstance(data, str) else None)
            except Exception as e:
                self.log.error("list_segments error: %s\n%s", e, traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/rag/kb/segment/create", response_model=ApiResponse)
        async def create_segment(
            request: KnowledgeSegmentCreateApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """创建知识片段"""
            try:
                user_id = int(user_ctx.user_id)
                err, data = await self.rag_service.create_knowledge_segment(request.data, user_id)
                if err == ErrorCode.SUCCESS:
                    return ok(data)
                return fail(err, data if isinstance(data, str) else None)
            except Exception as e:
                self.log.error("create_segment error: %s\n%s", e, traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/rag/kb/segment/update", response_model=ApiResponse)
        async def update_segment(
            request: KnowledgeSegmentUpdateApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """更新知识片段信息"""
            try:
                user_id = int(user_ctx.user_id)
                err, data = await self.rag_service.update_knowledge_segment(request.data, user_id)
                if err == ErrorCode.SUCCESS:
                    return ok(data)
                return fail(err, data if isinstance(data, str) else None)
            except Exception as e:
                self.log.error("update_segment error: %s\n%s", e, traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/rag/kb/segment/delete", response_model=ApiResponse)
        async def delete_segment(
            request: KnowledgeSegmentIdApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """删除知识片段"""
            try:
                user_id = int(user_ctx.user_id)
                err, data = await self.rag_service.delete_knowledge_segment(request.data, user_id)
                if err == ErrorCode.SUCCESS:
                    return ok(data)
                return fail(err, data if isinstance(data, str) else None)
            except Exception as e:
                self.log.error("delete_segment error: %s\n%s", e, traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/rag/kb/file/update_status", response_model=ApiResponse)
        async def update_kb_file_status(
            request: FileUpdateStatusApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """更新单个文件的启用状态（仅当前用户绑定的知识库）"""
            try:
                user_id = int(user_ctx.user_id)
                revalue, result = await self.rag_service.update_file_status(request.data, user_id)
                if revalue == ErrorCode.SUCCESS:
                    return ok(result)
                else:
                    return fail(revalue, result)
            except Exception as e:
                self.log.error("update_kb_file_status error: %s\n%s", e, traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/rag/kb/file/delete", response_model=ApiResponse)
        async def delete_kb_file(
            request: FileIdWithKbApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """删除单个文件（仅当前用户绑定的知识库）"""
            try:
                user_id = int(user_ctx.user_id)
                revalue, result = await self.rag_service.delete_file(request.data, user_id)
                if revalue == ErrorCode.SUCCESS:
                    return ok(result)
                else:
                    return fail(revalue, result)
            except Exception as e:
                self.log.error("delete_kb_file error: %s\n%s", e, traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/rag/kb/file/download", response_model=ApiResponse)
        async def get_kb_file_download_url(
            request: FileIdWithKbApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """获取单个文件的下载链接（MinIO 预签名 URL）"""
            try:
                user_id = int(user_ctx.user_id)
                revalue, result = await self.rag_service.get_file_download_url(request.data, user_id)
                if revalue == ErrorCode.SUCCESS:
                    return ok(result)
                else:
                    return fail(revalue, result)
            except Exception as e:
                self.log.error("get_kb_file_download_url error: %s\n%s", e, traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/rag/kb/list", response_model=ApiResponse)
        async def list_knowledge_bases(
            request: KnowledgeBaseListApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """查询当前用户绑定的知识库列表"""
            user_id = int(user_ctx.user_id)
            revalue, result = await self.rag_service.list_knowledge_bases(request.data, user_id)
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump() if hasattr(result, "model_dump") else result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/kb/create", response_model=ApiResponse)
        async def create_knowledge_base(
            request: KnowledgeBaseCreateApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """创建知识库（仅绑定当前用户）"""
            user_id = int(user_ctx.user_id)
            revalue, result = await self.rag_service.create_knowledge_base(request.data, user_id)
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump() if hasattr(result, "model_dump") else result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/kb/get", response_model=ApiResponse)
        async def get_knowledge_base(
            request: KnowledgeBaseIdApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """查询单个知识库详情（仅当前用户绑定的知识库）"""
            user_id = int(user_ctx.user_id)
            revalue, result = await self.rag_service.get_knowledge_base(request.data, user_id)
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump() if hasattr(result, "model_dump") else result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/kb/update", response_model=ApiResponse)
        async def update_knowledge_base(
            request: KnowledgeBaseUpdateApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """更新知识库信息（仅当前用户绑定的知识库）"""
            user_id = int(user_ctx.user_id)
            revalue, result = await self.rag_service.update_knowledge_base(request.data, user_id)
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump() if hasattr(result, "model_dump") else result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/kb/delete", response_model=ApiResponse)
        async def delete_knowledge_base(
            request: KnowledgeBaseIdApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """删除知识库（仅当前用户绑定的知识库）"""
            user_id = int(user_ctx.user_id)
            revalue, result = await self.rag_service.delete_knowledge_base(request.data, user_id)
            if revalue == ErrorCode.SUCCESS:
                return ok(result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/kb/export", response_model=ApiResponse)
        async def export_knowledge_base(
            request: KnowledgeBaseIdApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            user_id = int(user_ctx.user_id)
            revalue, result = await self.rag_service.export_knowledge_base(request.data, user_id)
            if revalue == ErrorCode.SUCCESS:
                return ok(result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/kb/knowledge/list", response_model=ApiResponse)
        async def list_knowledge_items(
            request: KnowledgeItemListApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """查询知识库下的知识信息列表（当前按文件聚合）"""
            user_id = int(user_ctx.user_id)
            revalue, result = await self.rag_service.list_knowledge_items(request.data, user_id)
            if revalue == ErrorCode.SUCCESS:
                return ok(result)
            else:
                return fail(revalue, result)

        @self.app.get("/v1/agent/rag/ontology/schema", response_model=ApiResponse)
        async def get_ontology_schema(
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """获取本体Schema（标签和关系类型）"""
            revalue, result = await self.rag_service.get_ontology_schema()
            if revalue == ErrorCode.SUCCESS:
                return ok(result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/ontology/nodes", response_model=ApiResponse)
        async def get_ontology_nodes(
            request: OntologyNodeListApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """获取本体节点列表"""
            data = request.data
            revalue, result = await self.rag_service.get_ontology_nodes(
                data.label, data.page, data.page_size, data.keyword
            )
            if revalue == ErrorCode.SUCCESS:
                return ok(result)
            else:
                return fail(revalue, result)

        @self.app.get("/v1/agent/rag/ontology/statistics", response_model=ApiResponse)
        async def get_ontology_statistics(
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """获取本体统计信息"""
            revalue, result = await self.rag_service.get_ontology_statistics()
            if revalue == ErrorCode.SUCCESS:
                return ok(result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/ontology/node/create", response_model=ApiResponse)
        async def create_ontology_node(
            request: OntologyNodeCreateApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """创建本体节点"""
            revalue, result = await self.rag_service.create_ontology_node(request.data)
            if revalue == ErrorCode.SUCCESS:
                return ok(result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/ontology/node/update", response_model=ApiResponse)
        async def update_ontology_node(
            request: OntologyNodeUpdateApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """更新本体节点"""
            revalue, result = await self.rag_service.update_ontology_node(request.data)
            if revalue == ErrorCode.SUCCESS:
                return ok(result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/ontology/node/delete", response_model=ApiResponse)
        async def delete_ontology_node(
            request: OntologyNodeDeleteApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """删除本体节点"""
            revalue, result = await self.rag_service.delete_ontology_node(request.data)
            if revalue == ErrorCode.SUCCESS:
                return ok(result)
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/rag/query/hybrid", response_model=ApiResponse)
        async def hybrid_rag_query(
            request: HybridRagQueryApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """混合 RAG 查询接口"""
            err, result = await self.rag_service.hybrid_rag_query(request.data)
            if err == ErrorCode.SUCCESS:
                return ok(result.model_dump() if hasattr(result, "model_dump") else result)
            else:
                return fail(err, result)

    async def _async_embed_and_index_file(self, kb_id: int, file_id: int, binding_user_id: int, object_name: str, bucket: str):
        """异步执行文件向量化处理；进度写入 Redis 供前端轮询。向量化放入线程执行，避免阻塞事件循环导致 status 等接口无响应。"""
        try:
            self.rag_service.repo.update_file_record(file_id, {"embedding_process": 2})
            self.rag_service.set_rag_file_progress(file_id, embedding_process=2, embedding_progress=0.0)
            self.log.info(f"Updated file {file_id} status to uploading (2)")

            self.rag_service.repo.update_file_record(file_id, {"embedding_process": 1})
            self.rag_service.set_rag_file_progress(file_id, embedding_process=1, embedding_progress=0.0)
            self.log.info(f"Updated file {file_id} status to vectorizing (1)")

            # 向量化为同步耗时操作（embed + Qdrant），放入线程执行，否则会阻塞事件循环导致 status 轮询无返回
            err = await asyncio.to_thread(
                self.rag_service.embed_and_index_file,
                kb_id=kb_id,
                file_id=file_id,
                binding_user_id=binding_user_id,
                object_name=object_name,
                bucket=bucket,
            )
            if err != ErrorCode.SUCCESS:
                # 单个文件失败：清理相关资源并标记失败，不影响其他文件
                self.rag_service.repo.update_file_record(file_id, {"embedding_process": 4})
                self.rag_service.set_rag_file_progress(
                    file_id,
                    embedding_process=4,
                    embedding_progress=0.0,
                    error_message=f"文件向量化失败，错误码: {err}"
                )
                self.rag_service.cleanup_file_resources(kb_id, file_id, object_name, bucket)
                self.log.error(f"Async embedding failed for file_id {file_id} with err={err}, resources cleaned")
                return

            # 成功路径下，embed_and_index_file 已在线程中完成：
            # - Qdrant 写入
            # - 文件 embedding_process=3 标记
            # - rag_tbl.file_capacity / file_count 统计更新
            self.log.info(f"Completed embedding for file_id: {file_id}")

        except Exception as e:
            self.rag_service.repo.update_file_record(file_id, {"embedding_process": 4})
            self.rag_service.set_rag_file_progress(
                file_id, embedding_process=4, embedding_progress=0.0,
                error_message=str(e)
            )
            # 异常视为失败，同样清理资源
            self.rag_service.cleanup_file_resources(kb_id, file_id, object_name, bucket)
            self.log.error(f"Async embedding exception for file_id {file_id}: {e}, resources cleaned")
