'''
VLM控制器 - 视觉语言模型 REST API
提供类 OpenAI Vision API 风格的接口
所有接口统一使用 POST 方法
'''
import json
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import ValidationError

from domain.service.vlm_service import VLMService
from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

from interfaces.dto.vlm_dto import (
    VisionCompletionRequest, ImageAnalyzeRequest, MultiImageAnalyzeRequest,
    VisionCompletionResponse, VisionCompletionChunk, ImageAnalyzeResponse,
    EmptyRequest, StreamMode, StreamOptions
)
from interfaces.dto.response_dto import ApiResponse, ok, fail
from interfaces.assembler.vlm_assembler import VLMAssembler


@logger()
class VLMController:
    """
    VLM 控制器 - 视觉语言模型接口
    
    所有接口统一使用 POST 方法:
    - POST /v1/vision/completions  - 视觉对话补全
    - POST /v1/vision/analyze      - 单图像分析
    - POST /v1/vision/analyze/multi - 多图像分析
    - POST /vlm/health             - VLM健康检查
    - POST /vlm/metrics            - VLM服务指标
    - POST /vlm/gpu/resources      - GPU资源查询
    - POST /vlm/model/reload       - 重新加载模型
    """
    
    def __init__(self, config: SysConfig, web_app: FastAPI):
        """
        初始化 VLM 控制器
        
        Args:
            config: 系统配置
            web_app: FastAPI 应用实例
        """
        self.config = config
        self.app = web_app
        self.vlm_service = VLMService(config, auto_load=True)
        self._model_name = self._extract_model_name()
        
        # 注册路由
        self._register_routes()
        
        self.log.info("VLMController initialized")
    
    def _extract_model_name(self) -> str:
        """从配置中提取模型名称"""
        model_path = self.config.get_vlm_config().get('model', '')
        return model_path.split("/")[-1] if "/" in model_path else model_path
    
    def _sanitize_request_for_log(self, request_data: dict) -> dict:
        """
        清理请求数据用于日志打印，移除图片内容
        
        Args:
            request_data: 原始请求数据
            
        Returns:
            dict: 清理后的数据（图片内容被替换为占位符）
        """
        import copy
        
        def sanitize_value(value):
            if isinstance(value, str):
                # 检查是否是 base64 图片或 URL
                if value.startswith('data:image'):
                    return f"[BASE64_IMAGE, len={len(value)}]"
                elif len(value) > 500:  # 过长的字符串截断
                    return f"{value[:100]}... [truncated, len={len(value)}]"
            elif isinstance(value, dict):
                return sanitize_dict(value)
            elif isinstance(value, list):
                return [sanitize_value(item) for item in value]
            return value
        
        def sanitize_dict(d):
            result = {}
            for key, value in d.items():
                if key in ('image', 'url', 'image_url') and isinstance(value, str):
                    if value.startswith('data:image'):
                        result[key] = f"[BASE64_IMAGE, len={len(value)}]"
                    elif value.startswith('http'):
                        result[key] = value  # URL 保留
                    else:
                        result[key] = f"[IMAGE_DATA, len={len(value)}]"
                elif key == 'image_url' and isinstance(value, dict):
                    result[key] = sanitize_dict(value)
                else:
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
        
        # ==================== OpenAI Vision 兼容接口 ====================
        
        @self.app.post("/v1/vision/completions", response_model=ApiResponse)
        async def vision_completions(request: VisionCompletionRequest):
            """
            视觉对话补全接口 - 兼容 OpenAI Vision API
            支持多模态消息（文本+图像）
            """
            self._log_request("/v1/vision/completions", request)
            if request.stream:
                return StreamingResponse(
                    self._stream_vision_completions(request),
                    media_type="text/event-stream"
                )
            return await self._handle_vision_completions(request)
        
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: VisionCompletionRequest):
            """
            对话补全接口 - 兼容 OpenAI Chat API（原生格式）
            
            返回标准 OpenAI 格式，不包装 code/data，用于 Mem0 等第三方库
            
            注意：当使用 async 引擎时，会自动使用流式接口收集完整结果
            """
            self._log_request("/v1/chat/completions", request)
            if request.stream:
                return StreamingResponse(
                    self._stream_vision_completions(request),
                    media_type="text/event-stream"
                )
            # 返回原生 OpenAI 格式（不包装 code/data）
            return await self._handle_chat_completions_openai_format(request)
        
        @self.app.post("/v1/vision/analyze", response_model=ApiResponse)
        async def analyze_image(request: ImageAnalyzeRequest):
            """
            单图像分析接口 - 简化版
            """
            self._log_request("/v1/vision/analyze", request)
            return await self._handle_analyze_image(request)
        
        @self.app.post("/v1/vision/analyze/multi", response_model=ApiResponse)
        async def analyze_multi_images(request: MultiImageAnalyzeRequest):
            """
            多图像分析接口
            """
            self._log_request("/v1/vision/analyze/multi", request)
            return await self._handle_analyze_multi_images(request)
        
        # ==================== 服务管理接口 ====================
        
        @self.app.post("/vlm/health", response_model=ApiResponse)
        async def vlm_health_check(request: EmptyRequest = EmptyRequest()):
            """
            VLM 健康检查接口
            """
            return await self._handle_health_check()
        
        @self.app.post("/vlm/metrics", response_model=ApiResponse)
        async def vlm_metrics(request: EmptyRequest = EmptyRequest()):
            """
            VLM 服务指标接口
            """
            return await self._handle_metrics()
        
        @self.app.post("/vlm/gpu/resources", response_model=ApiResponse)
        async def vlm_gpu_resources(request: EmptyRequest = EmptyRequest()):
            """
            VLM GPU 资源查询接口
            """
            return await self._handle_gpu_resources()
        
        @self.app.post("/vlm/model/reload", response_model=ApiResponse)
        async def vlm_reload_model(request: EmptyRequest = EmptyRequest()):
            """
            重新加载 VLM 模型
            """
            return await self._handle_reload_model()
        
        # ==================== 异常处理 ====================
        
        @self.app.exception_handler(ValidationError)
        async def vlm_validation_exception_handler(request: Request, exc: ValidationError):
            """处理 Pydantic 验证错误"""
            return JSONResponse(
                status_code=400,
                content=fail(
                    ErrorCode.INVALID_PARAMETER,
                    f"参数验证失败: {exc.errors()}"
                ).model_dump()
            )
    
    # ==================== 请求处理方法 ====================
    
    async def _handle_vision_completions(self, request: VisionCompletionRequest) -> ApiResponse:
        """
        处理视觉对话补全请求（非流式）
        
        Args:
            request: 视觉补全请求
            
        Returns:
            ApiResponse: 统一响应
        """
        try:
            # 检查模型状态
            if not self.vlm_service.ping():
                return fail(ErrorCode.MODEL_NOT_LOADED, "VLM模型未加载")
            
            # 检查引擎类型
            engine_type = self.vlm_service.get_engine_type()
            
            if engine_type == 'async':
                # async 引擎：使用流式接口收集完整结果
                self.log.debug("Using async engine for vision completions, collecting stream results")
                return await self._collect_stream_to_sync_response(request)
            
            # llm 引擎：使用普通同步方法
            # 转换消息格式
            messages = VLMAssembler.messages_to_dict_list(request.messages)
            stop_words = VLMAssembler.normalize_stop_words(request.stop)
            
            # 调用视觉对话推理（同步方法，仅 llm 引擎支持）
            result = self.vlm_service.chat(
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                stop=stop_words
            )
            
            # 转换为响应格式
            response = VLMAssembler.vision_result_to_response(result, self._model_name)
            
            return ok(response.model_dump())
            
        except RuntimeError as e:
            self.log.error(f"Vision completion failed: {e}")
            return fail(ErrorCode.MODEL_NOT_LOADED, str(e))
        except Exception as e:
            self.log.error(f"Vision completion error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _handle_chat_completions_openai_format(self, request: VisionCompletionRequest) -> JSONResponse:
        """
        处理 /v1/chat/completions 请求，返回原生 OpenAI 格式
        
        不使用 ApiResponse 包装，直接返回 OpenAI 兼容的 JSON 格式
        用于 Mem0 等第三方库的兼容性
        """
        try:
            # 检查模型状态
            if not self.vlm_service.ping():
                return JSONResponse(
                    status_code=503,
                    content={"error": {"message": "Model not loaded", "type": "server_error"}}
                )
            
            # 检查引擎类型
            engine_type = self.vlm_service.get_engine_type()
            
            if engine_type == 'async':
                # async 引擎：使用流式接口收集完整结果
                self.log.debug("Using async engine, collecting stream results")
                return await self._collect_stream_to_openai_response(request)
            else:
                # llm 引擎：使用普通同步方法
                return await self._sync_to_openai_response(request)
                
        except Exception as e:
            self.log.error(f"Chat completion error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": {"message": str(e), "type": "server_error"}}
            )
    
    async def _sync_to_openai_response(self, request: VisionCompletionRequest) -> JSONResponse:
        """使用同步方法，返回 OpenAI 格式"""
        import time
        
        try:
            messages = VLMAssembler.messages_to_dict_list(request.messages)
            stop_words = VLMAssembler.normalize_stop_words(request.stop)
            
            result = self.vlm_service.chat(
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                stop=stop_words
            )
            
            # 构建原生 OpenAI 响应格式
            response = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": self._model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result.text if hasattr(result, 'text') else str(result)
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": result.prompt_tokens if hasattr(result, 'prompt_tokens') else 0,
                    "completion_tokens": result.completion_tokens if hasattr(result, 'completion_tokens') else 0,
                    "total_tokens": result.total_tokens if hasattr(result, 'total_tokens') else 0
                }
            }
            
            return JSONResponse(content=response)
            
        except Exception as e:
            self.log.error(f"Sync chat failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": {"message": str(e), "type": "server_error"}}
            )
    
    async def _collect_stream_to_openai_response(self, request: VisionCompletionRequest) -> JSONResponse:
        """使用流式接口收集完整结果，返回 OpenAI 格式"""
        import time
        start_time = time.time()
        
        try:
            messages = VLMAssembler.messages_to_dict_list(request.messages)
            stop_words = VLMAssembler.normalize_stop_words(request.stop)
            
            full_content = ""
            prompt_tokens = 0
            completion_tokens = 0
            finish_reason = "stop"
            
            async for chunk in self.vlm_service.chat_stream(
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                stop=stop_words
            ):
                if hasattr(chunk, 'delta_text') and chunk.delta_text:
                    full_content += chunk.delta_text
                
                if hasattr(chunk, 'is_finished') and chunk.is_finished:
                    if hasattr(chunk, 'prompt_tokens'):
                        prompt_tokens = chunk.prompt_tokens or 0
                    if hasattr(chunk, 'completion_tokens'):
                        completion_tokens = chunk.completion_tokens or 0
                    if hasattr(chunk, 'finish_reason') and chunk.finish_reason:
                        finish_reason = str(chunk.finish_reason)
            
            latency_ms = (time.time() - start_time) * 1000
            self.log.debug(f"Async stream collected: {len(full_content)} chars in {latency_ms:.0f}ms")
            
            # 构建原生 OpenAI 响应格式
            response = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": self._model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": full_content
                        },
                        "finish_reason": finish_reason
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }
            
            return JSONResponse(content=response)
            
        except Exception as e:
            self.log.error(f"Failed to collect stream: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": {"message": str(e), "type": "server_error"}}
            )
    
    async def _handle_chat_completions_sync(self, request: VisionCompletionRequest) -> ApiResponse:
        """
        处理 /v1/chat/completions 的同步请求
        
        当使用 async 引擎时，通过流式接口收集完整结果后返回
        当使用 llm 引擎时，直接使用同步方法
        
        Args:
            request: 视觉补全请求
            
        Returns:
            ApiResponse: 统一响应
        """
        try:
            # 检查模型状态
            if not self.vlm_service.ping():
                return fail(ErrorCode.MODEL_NOT_LOADED, "VLM模型未加载")
            
            # 检查引擎类型
            engine_type = self.vlm_service.get_engine_type()
            
            if engine_type == 'async':
                # async 引擎：使用流式接口收集完整结果
                self.log.debug("Using async engine, collecting stream results for sync response")
                return await self._collect_stream_to_sync_response(request)
            else:
                # llm 引擎：使用普通同步方法
                return await self._handle_vision_completions(request)
                
        except Exception as e:
            self.log.error(f"Chat completion error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _collect_stream_to_sync_response(self, request: VisionCompletionRequest) -> ApiResponse:
        """
        使用流式接口收集完整结果，返回同步响应
        
        用于 async 引擎处理非流式请求（如 Mem0 的调用）
        """
        import time
        start_time = time.time()
        
        try:
            # 转换消息格式
            messages = VLMAssembler.messages_to_dict_list(request.messages)
            stop_words = VLMAssembler.normalize_stop_words(request.stop)
            
            # 调试日志：检查消息格式
            for i, msg in enumerate(messages):
                content = msg.get("content", "")
                if isinstance(content, list):
                    self.log.debug(f"Message[{i}] has {len(content)} content items")
                    for j, item in enumerate(content):
                        item_type = item.get("type", "unknown") if isinstance(item, dict) else type(item).__name__
                        has_image = "image_url" in item if isinstance(item, dict) else False
                        self.log.debug(f"  Item[{j}]: type={item_type}, has_image={has_image}")
                else:
                    self.log.debug(f"Message[{i}] content type: {type(content).__name__}, len={len(str(content)[:50])}")
            
            # 使用异步流式接口收集结果
            full_content = ""
            prompt_tokens = 0
            completion_tokens = 0
            finish_reason = "stop"
            
            async for chunk in self.vlm_service.chat_stream(
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                stop=stop_words
            ):
                # StreamChunk 包含 delta_text（增量文本）
                if hasattr(chunk, 'delta_text') and chunk.delta_text:
                    full_content += chunk.delta_text
                
                # 获取 token 统计（最终结果中会有）
                if hasattr(chunk, 'is_finished') and chunk.is_finished:
                    if hasattr(chunk, 'prompt_tokens'):
                        prompt_tokens = chunk.prompt_tokens or 0
                    if hasattr(chunk, 'completion_tokens'):
                        completion_tokens = chunk.completion_tokens or 0
                    if hasattr(chunk, 'finish_reason') and chunk.finish_reason:
                        finish_reason = str(chunk.finish_reason)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # 构建响应
            response = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": self._model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": full_content
                        },
                        "finish_reason": finish_reason
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }
            
            self.log.debug(f"Async stream collected: {len(full_content)} chars in {latency_ms:.0f}ms")
            return ok(response)
            
        except Exception as e:
            self.log.error(f"Failed to collect stream: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _stream_vision_completions(
        self,
        request: VisionCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """
        流式视觉对话补全
        
        支持两种流式模式:
        - token: 真正的 token 级流式（使用 AsyncLLMEngine）
        - chunk: 分块流式（先生成完再分块发送）
        - auto: 自动选择（优先使用 token 模式）
        
        Args:
            request: 视觉补全请求
            
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
        engine_type = self.vlm_service.get_engine_type()
        token_available = self.vlm_service.is_token_stream_available()
        
        # 根据引擎类型确定实际使用的流式模式
        # - async 引擎: 只能使用 token 流式
        # - llm 引擎: 只能使用 chunk 流式
        if stream_mode == StreamMode.AUTO:
            if token_available:
                stream_mode = StreamMode.TOKEN
            else:
                stream_mode = StreamMode.CHUNK
        elif stream_mode == StreamMode.TOKEN and not token_available:
            # 请求 token 但不可用，降级为 chunk
            self.log.info(f"Token streaming not available (engine={engine_type}), falling back to chunk mode")
            stream_mode = StreamMode.CHUNK
        elif stream_mode == StreamMode.CHUNK and engine_type == 'async':
            # 请求 chunk 但使用 async 引擎，升级为 token
            self.log.info(f"Chunk streaming not supported with async engine, using token mode")
            stream_mode = StreamMode.TOKEN
        
        try:
            # 检查模型状态
            if not self.vlm_service.ping():
                error_chunk = {
                    "error": {
                        "code": ErrorCode.MODEL_NOT_LOADED.value,
                        "message": "VLM模型未加载"
                    }
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # 发送角色信息（第一个块）
            first_chunk = VLMAssembler.create_vision_chunk(
                chunk_id=chunk_id,
                model_name=self._model_name,
                role="assistant"
            )
            yield f"data: {first_chunk.model_dump_json()}\n\n"
            
            # 转换消息格式
            messages = VLMAssembler.messages_to_dict_list(request.messages)
            stop_words = VLMAssembler.normalize_stop_words(request.stop)
            
            # 记录最终的 usage 信息
            final_usage = None
            
            if stream_mode == StreamMode.TOKEN:
                # Token 级流式（真正的流式输出，需要 AsyncLLMEngine）
                self.log.debug(f"Using token-level streaming mode (engine={engine_type})")
                async for stream_chunk in self.vlm_service.chat_stream(
                    messages=messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k,
                    stop=stop_words
                ):
                    if stream_chunk.delta_text:
                        chunk = VLMAssembler.create_vision_chunk(
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
                        # 发送结束标记
                        final_chunk = VLMAssembler.create_vision_chunk(
                            chunk_id=chunk_id,
                            model_name=self._model_name,
                            finish_reason=stream_chunk.finish_reason or "stop"
                        )
                        yield f"data: {final_chunk.model_dump_json()}\n\n"
            
            elif stream_mode == StreamMode.CHUNK:
                # 分块流式（伪流式）
                self.log.debug(f"Using chunk-level streaming mode (chunk_size={chunk_size})")
                for stream_chunk in self.vlm_service.chat_stream_chunk(
                    messages=messages,
                    chunk_size=chunk_size,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    top_k=request.top_k,
                    stop=stop_words
                ):
                    if stream_chunk.delta_text:
                        chunk = VLMAssembler.create_vision_chunk(
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
                        # 发送结束标记
                        final_chunk = VLMAssembler.create_vision_chunk(
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
            self.log.error(f"Stream vision completion error: {e}")
            error_chunk = {
                "error": {
                    "code": ErrorCode.MODEL_INFERENCE_FAILED.value,
                    "message": str(e)
                }
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
    
    async def _handle_analyze_image(self, request: ImageAnalyzeRequest) -> ApiResponse:
        """
        处理单图像分析请求
        
        Args:
            request: 图像分析请求
            
        Returns:
            ApiResponse: 统一响应
        """
        try:
            # 检查模型状态
            if not self.vlm_service.ping():
                return fail(ErrorCode.MODEL_NOT_LOADED, "VLM模型未加载")
            
            # 检查引擎类型
            engine_type = self.vlm_service.get_engine_type()
            
            if engine_type == 'async':
                # async 引擎：使用流式接口收集完整结果
                self.log.debug("Using async engine for image analysis, collecting stream results")
                return await self._collect_stream_for_analyze(request.image, request.prompt, request.max_tokens, request.temperature)
            
            # llm 引擎：使用普通同步方法
            result = self.vlm_service.analyze_image(
                image=request.image,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            # 转换为响应格式
            response = VLMAssembler.vision_result_to_analyze_response(result)
            
            return ok(response.model_dump())
            
        except RuntimeError as e:
            self.log.error(f"Image analysis failed: {e}")
            return fail(ErrorCode.MODEL_NOT_LOADED, str(e))
        except Exception as e:
            self.log.error(f"Image analysis error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _handle_analyze_multi_images(self, request: MultiImageAnalyzeRequest) -> ApiResponse:
        """
        处理多图像分析请求
        
        Args:
            request: 多图像分析请求
            
        Returns:
            ApiResponse: 统一响应
        """
        try:
            # 检查模型状态
            if not self.vlm_service.ping():
                return fail(ErrorCode.MODEL_NOT_LOADED, "VLM模型未加载")
            
            # 检查引擎类型
            engine_type = self.vlm_service.get_engine_type()
            
            if engine_type == 'async':
                # async 引擎：使用流式接口收集完整结果
                self.log.debug("Using async engine for multi-image analysis, collecting stream results")
                return await self._collect_stream_for_analyze_multi(request.images, request.prompt, request.max_tokens, request.temperature)
            
            # llm 引擎：使用普通同步方法
            result = self.vlm_service.analyze_images(
                images=request.images,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            # 转换为响应格式
            response = VLMAssembler.vision_result_to_analyze_response(result)
            
            return ok(response.model_dump())
            
        except RuntimeError as e:
            self.log.error(f"Multi-image analysis failed: {e}")
            return fail(ErrorCode.MODEL_NOT_LOADED, str(e))
        except Exception as e:
            self.log.error(f"Multi-image analysis error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _collect_stream_for_analyze(self, image: str, prompt: str, max_tokens: int, temperature: float) -> ApiResponse:
        """
        使用流式接口收集单图像分析结果
        
        用于 async 引擎处理 /v1/vision/analyze 请求
        """
        import time
        start_time = time.time()
        
        try:
            # 构建消息格式
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image}}
                    ]
                }
            ]
            
            # 使用流式接口收集结果
            collected_text = ""
            async for chunk in self.vlm_service.chat_stream(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                if hasattr(chunk, 'delta_text') and chunk.delta_text:
                    collected_text += chunk.delta_text
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            self.log.debug(f"Async stream collected for analyze: {len(collected_text)} chars in {elapsed_ms}ms")
            
            # 构建分析响应
            response = {
                "description": collected_text,
                "model": self._model_name,
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": len(collected_text),
                    "total_tokens": len(collected_text)
                }
            }
            
            return ok(response)
            
        except Exception as e:
            self.log.error(f"Stream collect for analyze error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _collect_stream_for_analyze_multi(self, images: list, prompt: str, max_tokens: int, temperature: float) -> ApiResponse:
        """
        使用流式接口收集多图像分析结果
        
        用于 async 引擎处理 /v1/vision/analyze/multi 请求
        """
        import time
        start_time = time.time()
        
        try:
            # 构建消息格式
            content = [{"type": "text", "text": prompt}]
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": img}})
            
            messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            # 使用流式接口收集结果
            collected_text = ""
            async for chunk in self.vlm_service.chat_stream(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                if hasattr(chunk, 'delta_text') and chunk.delta_text:
                    collected_text += chunk.delta_text
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            self.log.debug(f"Async stream collected for multi-analyze: {len(collected_text)} chars in {elapsed_ms}ms")
            
            # 构建分析响应
            response = {
                "description": collected_text,
                "model": self._model_name,
                "image_count": len(images),
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": len(collected_text),
                    "total_tokens": len(collected_text)
                }
            }
            
            return ok(response)
            
        except Exception as e:
            self.log.error(f"Stream collect for multi-analyze error: {e}")
            return fail(ErrorCode.MODEL_INFERENCE_FAILED, str(e))
    
    async def _handle_health_check(self) -> ApiResponse:
        """
        处理VLM健康检查请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            health = self.vlm_service.health_check()
            active_requests = self.vlm_service.get_active_requests()
            
            response = VLMAssembler.health_status_to_response(health, active_requests)
            
            if health.is_healthy:
                return ok(response, "VLM服务健康")
            else:
                return fail(
                    ErrorCode.SERVICE_UNAVAILABLE,
                    health.error_message or "VLM服务不健康",
                    response
                )
                
        except Exception as e:
            self.log.error(f"VLM health check error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_metrics(self) -> ApiResponse:
        """
        处理VLM指标请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            model_info = self.vlm_service.get_model_info()
            return ok(model_info)
            
        except Exception as e:
            self.log.error(f"VLM metrics error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_gpu_resources(self) -> ApiResponse:
        """
        处理 VLM GPU 资源查询请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            resources = self.vlm_service.get_gpu_resources()
            resource_dtos = [VLMAssembler.resource_info_to_dto(r) for r in resources]
            return ok(resource_dtos)
            
        except Exception as e:
            self.log.error(f"VLM GPU resources error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_reload_model(self) -> ApiResponse:
        """
        处理VLM模型重载请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            # 先卸载
            self.vlm_service.unload_model()
            
            # 重新加载
            success_result = self.vlm_service.load_model()
            
            if success_result:
                return ok(None, "VLM模型重载成功")
            else:
                return fail(ErrorCode.MODEL_LOAD_FAILED, "VLM模型重载失败")
                
        except Exception as e:
            self.log.error(f"VLM reload model error: {e}")
            return fail(ErrorCode.MODEL_LOAD_FAILED, str(e))
    
    def shutdown(self) -> None:
        """关闭控制器，释放资源"""
        try:
            if self.vlm_service:
                self.vlm_service.shutdown()
            self.log.info("VLMController shutdown complete")
        except Exception as e:
            self.log.error(f"VLMController shutdown error: {e}")

