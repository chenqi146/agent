'''
LLM控制器 - 提供类 OpenAI 风格的 REST API
负责处理 HTTP 请求、DTO 转换、统一响应
所有接口统一使用 POST 方法
'''
import json
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import ValidationError

from domain.service.llm_service import LLMService
from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

from interfaces.dto.llm_dto import (
    CompletionRequest, ChatCompletionRequest,
    CompletionResponse, ChatCompletionResponse,
    ChatCompletionChunk, ModelListResponse, ModelInfo,
    HealthCheckResponse, EmptyRequest, ModelReloadRequest,
    StreamMode, StreamOptions
)
from interfaces.dto.response_dto import ApiResponse, ok, fail
from interfaces.assembler.llm_assembler import LLMAssembler


@logger()
class LLMController:
    """
    LLM 控制器
    
    所有接口统一使用 POST 方法:
    - POST /v1/completions       - 文本补全
    - POST /v1/chat/completions  - 对话补全
    - POST /v1/models            - 获取模型列表
    - POST /health               - 健康检查
    - POST /metrics              - 服务指标
    - POST /gpu/resources        - GPU资源查询
    - POST /model/reload         - 重新加载模型
    """
    
    def __init__(self, config: SysConfig, web_app: FastAPI):
        """
        初始化 LLM 控制器
        
        Args:
            config: 系统配置
            web_app: FastAPI 应用实例
        """
        self.config = config
        self.app = web_app
        self.llm_service = LLMService(config, auto_load=True)
        self._model_name = self._extract_model_name()
        
        # 注册路由
        self._register_routes()
        
        self.log.info("LLMController initialized")
    
    def _extract_model_name(self) -> str:
        """从配置中提取模型名称"""
        model_path = self.config.get_llm_config().get('model', '')
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
                if len(value) > 500:  # 过长的字符串截断
                    return f"{value[:200]}... [truncated, len={len(value)}]"
            elif isinstance(value, dict):
                return sanitize_dict(value)
            elif isinstance(value, list):
                return [sanitize_value(item) for item in value]
            return value
        
        def sanitize_dict(d):
            result = {}
            for key, value in d.items():
                result[key] = sanitize_value(value)
            return result
        
        return sanitize_dict(request_data)
    
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
        
        @self.app.post("/v1/completions", response_model=ApiResponse)
        async def completions(request: CompletionRequest):
            """
            文本补全接口 - 兼容 OpenAI /v1/completions
            """
            self._log_request("/v1/completions", request)
            return await self._handle_completions(request)
        
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: ChatCompletionRequest):
            """
            对话补全接口 - 兼容 OpenAI /v1/chat/completions
            支持流式和非流式响应
            """
            self._log_request("/v1/chat/completions", request)
            if request.stream:
                return StreamingResponse(
                    self._stream_chat_completions(request),
                    media_type="text/event-stream"
                )
            return await self._handle_chat_completions(request)
        
        @self.app.post("/v1/models", response_model=ApiResponse)
        async def list_models(request: EmptyRequest = EmptyRequest()):
            """
            获取模型列表 - 兼容 OpenAI /v1/models
            """
            return await self._handle_list_models()
        
        # ==================== 服务管理接口 ====================
        
        @self.app.post("/health", response_model=ApiResponse)
        async def health_check(request: EmptyRequest = EmptyRequest()):
            """
            健康检查接口
            """
            return await self._handle_health_check()
        
        @self.app.post("/metrics", response_model=ApiResponse)
        async def metrics(request: EmptyRequest = EmptyRequest()):
            """
            服务指标接口
            """
            return await self._handle_metrics()
        
        @self.app.post("/gpu/resources", response_model=ApiResponse)
        async def gpu_resources(request: EmptyRequest = EmptyRequest()):
            """
            GPU 资源查询接口
            """
            return await self._handle_gpu_resources()
        
        @self.app.post("/model/reload", response_model=ApiResponse)
        async def reload_model(request: ModelReloadRequest = ModelReloadRequest()):
            """
            重新加载模型
            """
            return await self._handle_reload_model(request)
        
        # ==================== 异常处理 ====================
        
        @self.app.exception_handler(ValidationError)
        async def validation_exception_handler(request: Request, exc: ValidationError):
            """处理 Pydantic 验证错误"""
            return JSONResponse(
                status_code=400,
                content=fail(
                    ErrorCode.INVALID_PARAMETER,
                    f"参数验证失败: {exc.errors()}"
                ).model_dump()
            )
        
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            """全局异常处理"""
            self.log.error(f"Unhandled exception: {exc}")
            return JSONResponse(
                status_code=500,
                content=fail(
                    ErrorCode.INTERNAL_ERROR,
                    str(exc)
                ).model_dump()
            )
    
    # ==================== 请求处理方法 ====================
    
    async def _handle_completions(self, request: CompletionRequest) -> ApiResponse:
        """
        处理文本补全请求
        
        Args:
            request: 补全请求
            
        Returns:
            ApiResponse: 统一响应
        """
        try:
            # 检查模型状态
            if not self.llm_service.ping():
                return fail(ErrorCode.MODEL_NOT_LOADED, "模型未加载")
            
            # 标准化停止词
            stop_words = LLMAssembler.normalize_stop_words(request.stop)
            
            # 判断是单条还是批量
            if isinstance(request.prompt, str):
                # 单条推理
                result = self.llm_service.generate(
                    prompt=request.prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k,
                    stop=stop_words
                )
                response = LLMAssembler.inference_result_to_completion_response(
                    result, self._model_name
                )
            else:
                # 批量推理
                results = self.llm_service.generate_batch(
                    prompts=request.prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k,
                    stop=stop_words
                )
                response = LLMAssembler.inference_results_to_completion_response(
                    results, self._model_name
                )
            
            return ok(response.model_dump())
            
        except RuntimeError as e:
            self.log.error(f"Completion failed: {e}")
            return fail(ErrorCode.MODEL_NOT_LOADED, str(e))
        except Exception as e:
            self.log.error(f"Completion error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _handle_chat_completions(self, request: ChatCompletionRequest) -> ApiResponse:
        """
        处理对话补全请求（非流式）
        
        Args:
            request: 对话补全请求
            
        Returns:
            ApiResponse: 统一响应
        """
        try:
            # 检查模型状态
            if not self.llm_service.ping():
                return fail(ErrorCode.MODEL_NOT_LOADED, "模型未加载")
            
            # 转换消息格式
            messages = LLMAssembler.chat_messages_to_dict_list(request.messages)
            stop_words = LLMAssembler.normalize_stop_words(request.stop)
            
            # 调用对话推理
            result = self.llm_service.chat(
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                stop=stop_words
            )
            
            # 转换为响应格式
            response = LLMAssembler.inference_result_to_chat_completion_response(
                result, self._model_name
            )
            
            return ok(response.model_dump())
            
        except RuntimeError as e:
            self.log.error(f"Chat completion failed: {e}")
            return fail(ErrorCode.MODEL_NOT_LOADED, str(e))
        except Exception as e:
            self.log.error(f"Chat completion error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _stream_chat_completions(
        self, 
        request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """
        流式对话补全
        
        支持两种流式模式:
        - token: 真正的 token 级流式（使用 AsyncLLMEngine）
        - chunk: 分块流式（先生成完再分块发送）
        - auto: 自动选择（优先使用 token 模式）
        
        Args:
            request: 对话补全请求
            
        Yields:
            str: SSE 格式的数据块
        """
        chunk_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        
        # 解析流式选项
        stream_options = request.stream_options or StreamOptions()
        stream_mode = stream_options.mode
        chunk_size = stream_options.chunk_size
        include_usage = stream_options.include_usage
        
        # 获取引擎类型
        engine_type = self.llm_service.get_engine_type()
        token_available = self.llm_service.is_token_stream_available()
        
        # 根据引擎类型确定实际使用的流式模式
        if stream_mode == StreamMode.AUTO:
            if token_available:
                stream_mode = StreamMode.TOKEN
            else:
                stream_mode = StreamMode.CHUNK
        elif stream_mode == StreamMode.TOKEN and not token_available:
            self.log.info(f"Token streaming not available (engine={engine_type}), falling back to chunk mode")
            stream_mode = StreamMode.CHUNK
        elif stream_mode == StreamMode.CHUNK and engine_type == 'async':
            self.log.info(f"Chunk streaming not supported with async engine, using token mode")
            stream_mode = StreamMode.TOKEN
        
        try:
            # 检查模型状态
            if not self.llm_service.ping():
                error_chunk = {
                    "error": {
                        "code": ErrorCode.MODEL_NOT_LOADED.value,
                        "message": "模型未加载"
                    }
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # 转换消息格式
            messages = LLMAssembler.chat_messages_to_dict_list(request.messages)
            stop_words = LLMAssembler.normalize_stop_words(request.stop)
            
            # 发送角色信息（第一个块）
            first_chunk = LLMAssembler.create_chat_completion_chunk(
                chunk_id=chunk_id,
                model_name=self._model_name,
                role="assistant"
            )
            yield f"data: {first_chunk.model_dump_json()}\n\n"
            
            # 记录最终的 usage 信息
            final_usage = None
            
            if stream_mode == StreamMode.TOKEN:
                # Token 级流式（真正的流式输出，需要 AsyncLLMEngine）
                self.log.debug(f"Using token-level streaming mode (engine={engine_type})")
                async for stream_chunk in self.llm_service.chat_stream(
                    messages=messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k,
                    stop=stop_words
                ):
                    if stream_chunk.delta_text:
                        chunk = LLMAssembler.create_chat_completion_chunk(
                            chunk_id=chunk_id,
                            model_name=self._model_name,
                            content=stream_chunk.delta_text
                        )
                        yield f"data: {chunk.model_dump_json()}\n\n"
                    
                    if stream_chunk.is_finished:
                        final_usage = {
                            "prompt_tokens": stream_chunk.prompt_tokens,
                            "completion_tokens": stream_chunk.completion_tokens,
                            "total_tokens": stream_chunk.total_tokens
                        }
                        final_chunk = LLMAssembler.create_chat_completion_chunk(
                            chunk_id=chunk_id,
                            model_name=self._model_name,
                            finish_reason=stream_chunk.finish_reason or "stop"
                        )
                        yield f"data: {final_chunk.model_dump_json()}\n\n"
            
            elif stream_mode == StreamMode.CHUNK:
                # 分块流式（伪流式）
                self.log.debug(f"Using chunk-level streaming mode (chunk_size={chunk_size})")
                for stream_chunk in self.llm_service.chat_stream_chunk(
                    messages=messages,
                    chunk_size=chunk_size,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k,
                    stop=stop_words
                ):
                    if stream_chunk.delta_text:
                        chunk = LLMAssembler.create_chat_completion_chunk(
                            chunk_id=chunk_id,
                            model_name=self._model_name,
                            content=stream_chunk.delta_text
                        )
                        yield f"data: {chunk.model_dump_json()}\n\n"
                    
                    if stream_chunk.is_finished:
                        final_usage = {
                            "prompt_tokens": stream_chunk.prompt_tokens,
                            "completion_tokens": stream_chunk.completion_tokens,
                            "total_tokens": stream_chunk.total_tokens
                        }
                        final_chunk = LLMAssembler.create_chat_completion_chunk(
                            chunk_id=chunk_id,
                            model_name=self._model_name,
                            finish_reason=stream_chunk.finish_reason or "stop"
                        )
                        yield f"data: {final_chunk.model_dump_json()}\n\n"
            
            # 如果需要，发送 usage 信息
            if include_usage and final_usage:
                usage_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "model": self._model_name,
                    "usage": final_usage
                }
                yield f"data: {json.dumps(usage_chunk, ensure_ascii=False)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            self.log.error(f"Stream chat completion error: {e}")
            error_chunk = {
                "error": {
                    "code": ErrorCode.MODEL_INFERENCE_FAILED.value,
                    "message": str(e)
                }
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
    
    def _build_chat_prompt(self, messages: list) -> str:
        """
        构建对话 prompt
        
        Args:
            messages: 消息列表
            
        Returns:
            str: 构建的 prompt
        """
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"<|system|>\n{content}\n")
            elif role == "user":
                prompt_parts.append(f"<|user|>\n{content}\n")
            elif role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{content}\n")
        
        prompt_parts.append("<|assistant|>\n")
        return "".join(prompt_parts)
    
    async def _handle_list_models(self) -> ApiResponse:
        """
        处理模型列表请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            model_info = ModelInfo(
                id=self._model_name,
                owned_by="local"
            )
            response = ModelListResponse(data=[model_info])
            return ok(response.model_dump())
            
        except Exception as e:
            self.log.error(f"List models error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_health_check(self) -> ApiResponse:
        """
        处理健康检查请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            health = self.llm_service.health_check()
            active_requests = self.llm_service.get_active_requests()
            
            response = LLMAssembler.health_status_to_response(health, active_requests)
            
            if health.is_healthy:
                return ok(response.model_dump(), "服务健康")
            else:
                return fail(
                    ErrorCode.SERVICE_UNAVAILABLE,
                    health.error_message or "服务不健康",
                    response.model_dump()
                )
                
        except Exception as e:
            self.log.error(f"Health check error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_metrics(self) -> ApiResponse:
        """
        处理指标请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            model_info = self.llm_service.get_model_info()
            return ok(model_info)
            
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
            resources = self.llm_service.get_gpu_resources()
            resource_dtos = [
                LLMAssembler.resource_info_to_dto(r).model_dump() 
                for r in resources
            ]
            return ok(resource_dtos)
            
        except Exception as e:
            self.log.error(f"GPU resources error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_reload_model(self, request: ModelReloadRequest) -> ApiResponse:
        """
        处理模型重载请求
        
        Args:
            request: 重载请求
            
        Returns:
            ApiResponse: 统一响应
        """
        try:
            # 先卸载
            self.llm_service.unload_model()
            
            # 重新加载
            success = self.llm_service.load_model()
            
            if success:
                return ok(None, "模型重载成功")
            else:
                return fail(ErrorCode.MODEL_LOAD_FAILED, "模型重载失败")
                
        except Exception as e:
            self.log.error(f"Reload model error: {e}")
            return fail(ErrorCode.MODEL_LOAD_FAILED, str(e))
