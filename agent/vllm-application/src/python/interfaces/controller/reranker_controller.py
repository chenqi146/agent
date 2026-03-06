'''
Reranker 控制器 - 提供 REST API
负责处理 HTTP 请求、DTO 转换、统一响应
所有接口统一使用 POST 方法
'''
import json
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from domain.service.reranker_service import RerankerService
from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

from interfaces.dto.reranker_dto import (
    RerankRequest, RerankResponse, RerankResultItem, DocumentInfo,
    ScoreRequest, ScoreResponse, EmptyRequest
)
from interfaces.dto.response_dto import ApiResponse, ok, fail


@logger()
class RerankerController:
    """
    Reranker 控制器
    
    所有接口统一使用 POST 方法:
    - POST /v1/rerank              - 文档重排序
    - POST /v1/score               - query-document 评分
    - POST /reranker/health        - 健康检查
    - POST /reranker/metrics       - 服务指标
    - POST /reranker/gpu/resources - GPU资源查询
    """
    
    def __init__(self, config: SysConfig, web_app: FastAPI):
        """
        初始化 Reranker 控制器
        
        Args:
            config: 系统配置
            web_app: FastAPI 应用实例
        """
        self.config = config
        self.app = web_app
        self.reranker_service = RerankerService(config, auto_load=True)
        self._model_name = self._extract_model_name()
        
        # 注册路由
        self._register_routes()
        
        self.log.info("RerankerController initialized")
    
    def _extract_model_name(self) -> str:
        """从配置中提取模型名称"""
        model_path = self.config.get_reranker_config().get('model', '')
        return model_path.split("/")[-1] if "/" in model_path else model_path
    
    def _sanitize_request_for_log(self, request_data: dict) -> dict:
        """
        清理请求数据用于日志打印，截断过长内容
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
        """打印请求参数（debug 级别）"""
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
        
        # ==================== 核心接口 ====================
        
        @self.app.post("/v1/rerank", response_model=ApiResponse)
        async def rerank(request: RerankRequest):
            """
            文档重排序接口 - 兼容 Jina/Cohere /v1/rerank
            """
            self._log_request("/v1/rerank", request)
            return await self._handle_rerank(request)
        
        @self.app.post("/v1/score", response_model=ApiResponse)
        async def score(request: ScoreRequest):
            """
            Query-Document 评分接口
            """
            self._log_request("/v1/score", request)
            return await self._handle_score(request)
        
        # ==================== 服务管理接口 ====================
        
        @self.app.post("/reranker/health", response_model=ApiResponse)
        async def reranker_health_check(request: EmptyRequest = EmptyRequest()):
            """健康检查接口"""
            return await self._handle_health_check()
        
        @self.app.post("/reranker/metrics", response_model=ApiResponse)
        async def reranker_metrics(request: EmptyRequest = EmptyRequest()):
            """服务指标接口"""
            return await self._handle_metrics()
        
        @self.app.post("/reranker/gpu/resources", response_model=ApiResponse)
        async def reranker_gpu_resources(request: EmptyRequest = EmptyRequest()):
            """GPU 资源查询接口"""
            return await self._handle_gpu_resources()
        
        # ==================== 异常处理 ====================
        
        @self.app.exception_handler(ValidationError)
        async def reranker_validation_exception_handler(request: Request, exc: ValidationError):
            """处理 Pydantic 验证错误"""
            return JSONResponse(
                status_code=400,
                content=fail(
                    ErrorCode.INVALID_PARAMETER,
                    f"参数验证失败: {exc.errors()}"
                ).model_dump()
            )
    
    # ==================== 请求处理方法 ====================
    
    async def _handle_rerank(self, request: RerankRequest) -> ApiResponse:
        """
        处理文档重排序请求
        """
        try:
            # 检查模型状态
            if not self.reranker_service.ping():
                return fail(ErrorCode.MODEL_NOT_LOADED, "Reranker模型未加载")
            
            # 调用 reranker 服务
            result = self.reranker_service.rerank(
                query=request.query,
                documents=request.documents,
                top_n=request.top_n,
                return_documents=request.return_documents
            )
            
            # 构建响应
            results = []
            for item in result.results:
                result_item = RerankResultItem(
                    index=item["index"],
                    relevance_score=item["relevance_score"],
                    document=DocumentInfo(text=item["document"]["text"]) if item.get("document") else None
                )
                results.append(result_item)
            
            response = RerankResponse(
                model=self._model_name,
                results=results,
                usage=result.usage
            )
            
            return ok(response.model_dump())
            
        except RuntimeError as e:
            self.log.error(f"Rerank failed: {e}")
            return fail(ErrorCode.MODEL_NOT_LOADED, str(e))
        except Exception as e:
            self.log.error(f"Rerank error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _handle_score(self, request: ScoreRequest) -> ApiResponse:
        """
        处理评分请求
        """
        try:
            # 检查模型状态
            if not self.reranker_service.ping():
                return fail(ErrorCode.MODEL_NOT_LOADED, "Reranker模型未加载")
            
            # 调用 reranker 服务
            result = self.reranker_service.score(
                query=request.query,
                documents=request.documents
            )
            
            response = ScoreResponse(
                model=self._model_name,
                scores=result.scores,
                latency_ms=result.latency_ms
            )
            
            return ok(response.model_dump())
            
        except RuntimeError as e:
            self.log.error(f"Score failed: {e}")
            return fail(ErrorCode.MODEL_NOT_LOADED, str(e))
        except Exception as e:
            self.log.error(f"Score error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _handle_health_check(self) -> ApiResponse:
        """处理健康检查请求"""
        try:
            health = self.reranker_service.health_check()
            gpu_resources = self.reranker_service.get_gpu_resources()
            
            return ok({
                "is_healthy": health.is_healthy,
                "model_status": health.model_status,
                "model_name": self._model_name,
                "mode": self.reranker_service.get_mode(),
                "uptime_seconds": health.uptime_seconds,
                "total_requests": health.total_requests,
                "successful_requests": health.successful_requests,
                "failed_requests": health.failed_requests,
                "active_requests": self.reranker_service.get_active_requests(),
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
        """处理服务指标请求"""
        try:
            model_info = self.reranker_service.get_model_info()
            health = self.reranker_service.health_check()
            
            return ok({
                "model_name": self._model_name,
                "model_status": model_info.get("status", "unknown"),
                "enable": model_info.get("enable", False),
                "mode": model_info.get("mode", "unknown"),
                "total_requests": health.total_requests,
                "successful_requests": health.successful_requests,
                "failed_requests": health.failed_requests,
                "active_requests": self.reranker_service.get_active_requests(),
                "avg_latency_ms": health.avg_latency_ms,
                "uptime_seconds": health.uptime_seconds
            })
        except Exception as e:
            self.log.error(f"Metrics error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_gpu_resources(self) -> ApiResponse:
        """处理 GPU 资源查询请求"""
        try:
            resources = self.reranker_service.get_gpu_resources()
            
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
