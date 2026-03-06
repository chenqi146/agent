'''
Embedding 控制器 - 提供类 OpenAI 风格的 REST API
负责处理 HTTP 请求、DTO 转换、统一响应
所有接口统一使用 POST 方法
'''
import json
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from domain.service.embedding_service import EmbeddingService
from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

from interfaces.dto.embedding_dto import (
    EmbeddingRequest, EmbeddingResponse, EmbeddingData, EmbeddingUsage, EmptyRequest
)
from interfaces.dto.response_dto import ApiResponse, ok, fail


@logger()
class EmbeddingController:
    """
    Embedding 控制器
    
    所有接口统一使用 POST 方法:
    - POST /v1/embeddings          - 文本向量化
    - POST /embedding/health       - 健康检查
    - POST /embedding/metrics      - 服务指标
    - POST /embedding/gpu/resources - GPU资源查询
    """
    
    def __init__(self, config: SysConfig, web_app: FastAPI):
        """
        初始化 Embedding 控制器
        
        Args:
            config: 系统配置
            web_app: FastAPI 应用实例
        """
        self.config = config
        self.app = web_app
        self.embedding_service = EmbeddingService(config, auto_load=True)
        self._model_name = self._extract_model_name()
        
        # 注册路由
        self._register_routes()
        
        self.log.info("EmbeddingController initialized")
    
    def _extract_model_name(self) -> str:
        """从配置中提取模型名称"""
        model_path = self.config.get_embedding_config().get('model', '')
        return model_path.split("/")[-1] if "/" in model_path else model_path
    
    def _sanitize_request_for_log(self, request_data: dict) -> dict:
        """
        清理请求数据用于日志打印，截断过长内容
        
        Args:
            request_data: 原始请求数据
            
        Returns:
            dict: 清理后的数据
        """
        def sanitize_value(value):
            if isinstance(value, str):
                if len(value) > 200:
                    return f"{value[:100]}... [truncated, len={len(value)}]"
            elif isinstance(value, dict):
                return {k: sanitize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                if len(value) > 5:
                    return [sanitize_value(item) for item in value[:3]] + [f"... ({len(value)} items total)"]
                return [sanitize_value(item) for item in value]
            return value
        
        return {k: sanitize_value(v) for k, v in request_data.items()}
    
    def _log_request(self, endpoint: str, request) -> None:
        """
        打印请求参数（debug 级别）
        
        Args:
            endpoint: 接口路径
            request: 请求对象
        """
        try:
            if hasattr(request, 'model_dump'):
                request_data = request.model_dump()
            elif hasattr(request, 'dict'):
                request_data = request.dict()
            else:
                request_data = str(request)
            
            sanitized = self._sanitize_request_for_log(request_data) if isinstance(request_data, dict) else request_data
            self.log.debug(f"[{endpoint}] Request: {json.dumps(sanitized, ensure_ascii=False, default=str)}")
        except Exception as e:
            self.log.debug(f"[{endpoint}] Request logging failed: {e}")
    
    def _register_routes(self):
        """注册所有路由（统一使用 POST 方法）"""
        
        # ==================== OpenAI 兼容接口 ====================
        
        @self.app.post("/v1/embeddings")
        async def create_embeddings(request: EmbeddingRequest):
            """
            文本向量化接口 - 兼容 OpenAI /v1/embeddings
            返回原生 OpenAI 格式，用于 Mem0 等第三方库
            """
            self._log_request("/v1/embeddings", request)
            return await self._handle_embeddings_openai_format(request)
        
        # ==================== 服务管理接口 ====================
        
        @self.app.post("/embedding/health", response_model=ApiResponse)
        async def embedding_health_check(request: EmptyRequest = EmptyRequest()):
            """
            健康检查接口
            """
            return await self._handle_health_check()
        
        @self.app.post("/embedding/metrics", response_model=ApiResponse)
        async def embedding_metrics(request: EmptyRequest = EmptyRequest()):
            """
            服务指标接口
            """
            return await self._handle_metrics()
        
        @self.app.post("/embedding/gpu/resources", response_model=ApiResponse)
        async def embedding_gpu_resources(request: EmptyRequest = EmptyRequest()):
            """
            GPU 资源查询接口
            """
            return await self._handle_gpu_resources()
        
        # ==================== 异常处理 ====================
        
        @self.app.exception_handler(ValidationError)
        async def embedding_validation_exception_handler(request: Request, exc: ValidationError):
            """处理 Pydantic 验证错误"""
            return JSONResponse(
                status_code=400,
                content=fail(
                    ErrorCode.INVALID_PARAMETER,
                    f"参数验证失败: {exc.errors()}"
                ).model_dump()
            )
    
    # ==================== 请求处理方法 ====================
    
    async def _handle_embeddings_openai_format(self, request: EmbeddingRequest) -> JSONResponse:
        """
        处理文本向量化请求，返回原生 OpenAI 格式
        
        Args:
            request: Embedding 请求
            
        Returns:
            JSONResponse: 原生 OpenAI 格式的响应
        """
        try:
            # 检查模型状态
            if not self.embedding_service.ping():
                return JSONResponse(
                    status_code=503,
                    content={"error": {"message": "Embedding model not loaded", "type": "server_error"}}
                )
            
            # 获取输入文本
            texts = request.input
            if isinstance(texts, str):
                texts = [texts]
            
            # 获取 dimensions 参数
            dimensions = request.dimensions
            
            # 调用 embedding 服务
            result = self.embedding_service.encode(texts, dimensions=dimensions)
            
            # 构建原生 OpenAI 响应格式
            embedding_data = []
            for i, embedding in enumerate(result.embeddings):
                embedding_data.append({
                    "object": "embedding",
                    "index": i,
                    "embedding": embedding if isinstance(embedding, list) else embedding.tolist()
                })
            
            response = {
                "object": "list",
                "model": self._model_name,
                "data": embedding_data,
                "usage": {
                    "prompt_tokens": result.usage.get("prompt_tokens", 0),
                    "total_tokens": result.usage.get("total_tokens", 0)
                }
            }
            
            return JSONResponse(content=response)
            
        except RuntimeError as e:
            self.log.error(f"Embedding failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": {"message": str(e), "type": "server_error"}}
            )
        except Exception as e:
            self.log.error(f"Embedding error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": {"message": str(e), "type": "server_error"}}
            )
    
    async def _handle_embeddings(self, request: EmbeddingRequest) -> ApiResponse:
        """
        处理文本向量化请求
        
        Args:
            request: Embedding 请求
            
        Returns:
            ApiResponse: 统一响应
        """
        try:
            # 检查模型状态
            if not self.embedding_service.ping():
                return fail(ErrorCode.MODEL_NOT_LOADED, "Embedding模型未加载")
            
            # 获取输入文本
            texts = request.input
            if isinstance(texts, str):
                texts = [texts]
            
            # 获取 dimensions 参数
            dimensions = request.dimensions
            
            # 调用 embedding 服务
            result = self.embedding_service.encode(texts, dimensions=dimensions)
            
            # 构建响应
            embedding_data = []
            for i, embedding in enumerate(result.embeddings):
                embedding_data.append(EmbeddingData(
                    object="embedding",
                    index=i,
                    embedding=embedding
                ))
            
            response = EmbeddingResponse(
                object="list",
                model=self._model_name,
                data=embedding_data,
                usage=EmbeddingUsage(
                    prompt_tokens=result.usage.get("prompt_tokens", 0),
                    total_tokens=result.usage.get("total_tokens", 0)
                )
            )
            
            return ok(response.model_dump())
            
        except RuntimeError as e:
            self.log.error(f"Embedding failed: {e}")
            return fail(ErrorCode.MODEL_NOT_LOADED, str(e))
        except Exception as e:
            self.log.error(f"Embedding error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _handle_health_check(self) -> ApiResponse:
        """
        处理健康检查请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            health = self.embedding_service.health_check()
            gpu_resources = self.embedding_service.get_gpu_resources()
            
            return ok({
                "is_healthy": health.is_healthy,
                "model_status": health.model_status,
                "model_name": self._model_name,
                "uptime_seconds": health.uptime_seconds,
                "total_requests": health.total_requests,
                "successful_requests": health.successful_requests,
                "failed_requests": health.failed_requests,
                "active_requests": self.embedding_service.get_active_requests(),
                "avg_latency_ms": health.avg_latency_ms,
                "gpu_resources": [
                    {
                        "gpu_id": r.gpu_id,
                        "gpu_name": r.gpu_name,
                        "total_memory_mb": r.total_memory_mb,
                        "used_memory_mb": r.used_memory_mb,
                        "free_memory_mb": r.free_memory_mb,
                        "memory_utilization": r.memory_utilization,
                        "gpu_utilization": r.gpu_utilization,
                        "temperature": r.temperature
                    }
                    for r in gpu_resources
                ]
            })
        except Exception as e:
            self.log.error(f"Health check error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_metrics(self) -> ApiResponse:
        """
        处理服务指标请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            model_info = self.embedding_service.get_model_info()
            health = self.embedding_service.health_check()
            
            return ok({
                "model_name": self._model_name,
                "model_status": model_info.get("status", "unknown"),
                "enable": model_info.get("enable", False),
                "total_requests": health.total_requests,
                "successful_requests": health.successful_requests,
                "failed_requests": health.failed_requests,
                "active_requests": self.embedding_service.get_active_requests(),
                "avg_latency_ms": health.avg_latency_ms,
                "uptime_seconds": health.uptime_seconds
            })
        except Exception as e:
            self.log.error(f"Metrics error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_gpu_resources(self) -> ApiResponse:
        """
        处理 GPU 资源查询请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            resources = self.embedding_service.get_gpu_resources()
            
            return ok({
                "gpu_count": len(resources),
                "gpus": [
                    {
                        "gpu_id": r.gpu_id,
                        "gpu_name": r.gpu_name,
                        "total_memory_mb": r.total_memory_mb,
                        "used_memory_mb": r.used_memory_mb,
                        "free_memory_mb": r.free_memory_mb,
                        "memory_utilization": r.memory_utilization,
                        "gpu_utilization": r.gpu_utilization,
                        "temperature": r.temperature
                    }
                    for r in resources
                ]
            })
        except Exception as e:
            self.log.error(f"GPU resources error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
