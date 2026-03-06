'''
VLM服务 - 视觉语言模型服务，基于vLLM框架实现
提供图像理解、多模态推理等功能

并发支持说明:
- vLLM内部使用异步调度器，天然支持并发推理请求
- generate() / analyze_image() 等方法可被多线程同时调用
- 统计信息使用锁保护，确保计数准确

资源管理说明:
- 进程退出时自动释放GPU资源
- 支持上下文管理器自动清理
- 注册atexit确保异常退出时也能清理
'''
import time
import threading
import atexit
import gc
import base64
import re
import io
import requests
from typing import Dict, Any, List, Optional, Generator, Union
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image

import asyncio
from vllm import LLM, SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.outputs import RequestOutput

from infrastructure.common.logging.logging import logger, init_logging
from infrastructure.common.error.errcode import (
    ErrorCode, create_error, success, is_success,
    ErrorCode as EC
)
from infrastructure.config.sys_config import SysConfig
from infrastructure.llm.llm_model_status import ModelStatus
from infrastructure.llm.llm_work_info import InferenceResult, ResourceInfo, HealthStatus


@dataclass
class VisionInferenceResult:
    """视觉推理结果数据类"""
    request_id: str                          # 请求ID
    prompt: str                              # 输入提示词
    images: List[str]                        # 输入图像列表
    generated_text: str                      # 生成的文本
    finish_reason: str                       # 完成原因
    prompt_tokens: int = 0                   # 输入token数
    completion_tokens: int = 0               # 输出token数
    total_tokens: int = 0                    # 总token数
    latency_ms: float = 0.0                  # 推理延迟(毫秒)
    tokens_per_second: float = 0.0           # 每秒生成token数


@dataclass
class StreamChunk:
    """流式输出块数据类"""
    request_id: str                          # 请求ID
    delta_text: str                          # 增量文本
    is_finished: bool = False                # 是否完成
    finish_reason: Optional[str] = None      # 完成原因
    prompt_tokens: int = 0                   # 输入token数（仅在完成时有效）
    completion_tokens: int = 0               # 输出token数（仅在完成时有效）
    total_tokens: int = 0                    # 总token数（仅在完成时有效）


@logger()
class VLMService:
    """
    VLM服务类 - 视觉语言模型服务，基于vLLM框架
    
    提供以下功能:
    - 模型加载与初始化
    - 图像理解与分析
    - 多模态对话
    - 模型健康检测
    - GPU资源查询
    
    线程安全说明:
    - vLLM内部使用异步调度器，generate()方法天然支持多线程并发调用
    - 统计信息使用锁保护，确保计数准确
    """
    
    def __init__(self, config: SysConfig, auto_load: bool = True):
        """
        初始化VLM服务
        
        Args:
            config: 系统配置对象
            auto_load: 是否自动加载模型，默认True
        """
        try:
            self.vlm_config = config.get_vlm_config()
            self._llm: Optional[LLM] = None
            self._async_engine: Optional[AsyncLLMEngine] = None  # 异步引擎（用于流式输出）
            self._status = ModelStatus.UNINITIALIZED
            self._start_time: Optional[float] = None
            
            # 统计信息（使用锁保护以确保并发安全）
            self._stats_lock = threading.Lock()
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._total_latency_ms = 0.0
            
            # 当前并发请求数（用于监控）
            self._active_requests = 0
            
            # 模型配置
            self._model_path = self.vlm_config.get('model', '')
            self._device = self.vlm_config.get('device', 'cuda:0')
            self._gpu_memory_utilization = self.vlm_config.get('gpu_memory_utilization', 0.9)
            self._tensor_parallel_size = self.vlm_config.get('tensor_parallel_size', 1)
            self._max_model_len = self.vlm_config.get('max_model_len', 4096)
            
            # 生成参数配置
            self._max_gen_len = self.vlm_config.get('max_gen_len', 1024)
            self._temperature = self.vlm_config.get('temperature', 0.6)
            self._top_p = self.vlm_config.get('top_p', 0.9)
            self._top_k = self.vlm_config.get('top_k', 40)
            
            # 引擎类型配置: 'llm' 或 'async'
            # - llm: 使用 LLM 类（同步模式，支持 chunk 流式）
            # - async: 使用 AsyncLLMEngine（异步模式，支持真正的 token 级流式）
            self._engine_type = self.vlm_config.get('engine_type', 'llm').lower()
            
            self.log.info(f"VLMService initialized with model: {self._model_path}, engine_type: {self._engine_type}")
            
            # 是否启用模型
            self._enable = self.vlm_config.get('enable', True)
            
            # 注册进程退出清理函数
            self._cleanup_registered = False
            self._register_cleanup()
            
            # 根据 enable 配置决定是否加载模型
            if auto_load and self._enable:
                self.load_model()
            elif not self._enable:
                self.log.info(f"VLM model disabled by config (enable=false)")
                
        except Exception as e:
            self._status = ModelStatus.ERROR
            self.log.error(f"VLMService initialization failed: {e}")
            raise e
    
    def _register_cleanup(self) -> None:
        """注册进程退出时的清理函数"""
        if not self._cleanup_registered:
            atexit.register(self._cleanup_on_exit)
            self._cleanup_registered = True
            self.log.debug("Cleanup function registered for process exit")
    
    def _cleanup_on_exit(self) -> None:
        """进程退出时的清理函数"""
        try:
            if self._llm is not None:
                self.log.info("Process exiting, releasing VLM GPU resources...")
                self.unload_model()
        except Exception as e:
            print(f"Warning: Error during VLM cleanup on exit: {e}")
    
    # ==================== 统计信息线程安全更新方法 ====================
    
    def _increment_total_requests(self, count: int = 1) -> None:
        """线程安全地增加总请求数"""
        with self._stats_lock:
            self._total_requests += count
            self._active_requests += count
    
    def _increment_success(self, latency_ms: float, count: int = 1) -> None:
        """线程安全地增加成功请求数"""
        with self._stats_lock:
            self._successful_requests += count
            self._total_latency_ms += latency_ms
            self._active_requests -= count
    
    def _increment_failed(self, count: int = 1) -> None:
        """线程安全地增加失败请求数"""
        with self._stats_lock:
            self._failed_requests += count
            self._active_requests -= count
    
    def get_active_requests(self) -> int:
        """获取当前正在处理的请求数"""
        with self._stats_lock:
            return self._active_requests
    
    def load_model(self) -> bool:
        """
        加载视觉语言模型
        
        Returns:
            bool: 加载是否成功
        """
        if self._status == ModelStatus.READY:
            self.log.info("VLM Model already loaded")
            return True
        
        # 设置 CUDA_VISIBLE_DEVICES 环境变量来指定 GPU
        if self._device and self._device.startswith("cuda:"):
            gpu_id = self._device.split(":")[1]
            import os
            os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id
            self.log.info(f"Set CUDA_VISIBLE_DEVICES={gpu_id} for device {self._device}")
        
        try:
            self._status = ModelStatus.LOADING
            self.log.info(f"Loading VLM model from: {self._model_path}, engine_type: {self._engine_type}")
            
            if self._engine_type == 'async':
                # 使用 AsyncLLMEngine（支持真正的 token 级流式）
                self._init_async_engine()
                if self._async_engine is None:
                    raise RuntimeError("Failed to initialize AsyncLLMEngine")
                self.log.info("Using AsyncLLMEngine for token-level streaming")
            else:
                # 使用 LLM 类（同步模式，支持 chunk 流式）
                self._llm = LLM(
                    model=self._model_path,
                    gpu_memory_utilization=self._gpu_memory_utilization,
                    tensor_parallel_size=self._tensor_parallel_size,
                    max_model_len=self._max_model_len,
                    trust_remote_code=True,
                    dtype="auto",
                    # VLM 特定配置
                    limit_mm_per_prompt={"image": 10}  # 限制每个提示最多10张图片
                )
                self.log.info("Using LLM engine for chunk-level streaming")
            
            self._status = ModelStatus.READY
            self._start_time = time.time()
            self.log.info(f"VLM Model loaded successfully: {self._model_path}")
            return True
            
        except Exception as e:
            self._status = ModelStatus.ERROR
            self.log.error(f"Failed to load VLM model: {e}")
            return False
    
    def _init_async_engine(self) -> None:
        """
        初始化异步引擎（用于 token 级流式输出）
        
        Note:
            AsyncLLMEngine 会复用已加载的模型，不会重复加载
        """
        try:
            engine_args = AsyncEngineArgs(
                model=self._model_path,
                gpu_memory_utilization=self._gpu_memory_utilization,
                tensor_parallel_size=self._tensor_parallel_size,
                max_model_len=self._max_model_len,
                trust_remote_code=True,
                dtype="auto",
                limit_mm_per_prompt={"image": 10}
            )
            self._async_engine = AsyncLLMEngine.from_engine_args(engine_args)
            self.log.info("AsyncLLMEngine initialized for streaming")
        except Exception as e:
            self.log.info(f"AsyncLLMEngine not initialized: {e}. Using chunk-level streaming.")
            self._async_engine = None
    
    def unload_model(self) -> bool:
        """卸载模型，释放GPU资源"""
        try:
            if self._llm is not None:
                del self._llm
                self._llm = None
            
            # 清理异步引擎
            if self._async_engine is not None:
                del self._async_engine
                self._async_engine = None
                
            self._release_gpu_memory()
            self._status = ModelStatus.UNLOADED
            self.log.info("VLM Model unloaded successfully")
            return True
            
        except Exception as e:
            self.log.error(f"Failed to unload VLM model: {e}")
            return False
    
    def _release_gpu_memory(self) -> None:
        """释放GPU内存资源"""
        try:
            gc.collect()
            
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                    torch.cuda.empty_cache()
                    
                    for i in range(torch.cuda.device_count()):
                        try:
                            torch.cuda.reset_peak_memory_stats(i)
                            torch.cuda.reset_accumulated_memory_stats(i)
                        except Exception:
                            pass
                    
                    self.log.debug("PyTorch CUDA cache cleared for VLM")
            except ImportError:
                pass
            except Exception as e:
                self.log.debug(f"Failed to clear PyTorch CUDA cache: {e}")
            
            gc.collect()
            
        except Exception as e:
            self.log.debug(f"Error during GPU memory release: {e}")
    
    def _create_sampling_params(
        self,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> SamplingParams:
        """创建采样参数"""
        return SamplingParams(
            max_tokens=max_tokens or self._max_gen_len,
            temperature=temperature if temperature is not None else self._temperature,
            top_p=top_p if top_p is not None else self._top_p,
            top_k=top_k if top_k is not None else self._top_k,
            stop=stop,
            **kwargs
        )
    
    def _parse_image_input(self, image: str) -> Image.Image:
        """
        解析图像输入，返回 PIL Image 对象
        
        Args:
            image: 图像URL或base64编码
            
        Returns:
            PIL.Image.Image: PIL 图像对象
        """
        try:
            # 检查是否是 base64 编码
            if image.startswith("data:image"):
                # 解析 data URL: data:image/jpeg;base64,xxxxx
                match = re.match(r'data:image/(\w+);base64,(.+)', image)
                if match:
                    image_data = match.group(2)
                    # 解码 base64 并创建 PIL Image
                    image_bytes = base64.b64decode(image_data)
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    # 确保是 RGB 模式
                    if pil_image.mode != 'RGB':
                        pil_image = pil_image.convert('RGB')
                    return pil_image
            
            # 检查是否是纯 base64（没有 data URL 前缀）
            if len(image) > 100 and not image.startswith(('http://', 'https://')):
                try:
                    image_bytes = base64.b64decode(image)
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    if pil_image.mode != 'RGB':
                        pil_image = pil_image.convert('RGB')
                    return pil_image
                except Exception:
                    pass  # 不是 base64，尝试作为 URL 处理
            
            # 否则认为是 URL，下载图片
            if image.startswith(('http://', 'https://')):
                response = requests.get(image, timeout=30)
                response.raise_for_status()
                pil_image = Image.open(io.BytesIO(response.content))
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                return pil_image
            
            # 尝试作为本地文件路径
            pil_image = Image.open(image)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            return pil_image
            
        except Exception as e:
            self.log.error(f"Failed to parse image input: {e}")
            raise ValueError(f"无法解析图像: {e}")
    
    def _build_prompt_from_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> tuple:
        """
        从消息列表构建 Qwen3-VL 格式的 prompt
        
        Args:
            messages: 原始消息列表（OpenAI 格式）
            
        Returns:
            tuple: (prompt, pil_images) - 构建的 prompt 和图片列表
        """
        prompt_parts = []
        pil_images = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"<|im_start|>system\n{content}<|im_end|>\n")
            elif role == "user":
                if isinstance(content, str):
                    # 纯文本消息
                    prompt_parts.append(f"<|im_start|>user\n{content}<|im_end|>\n")
                elif isinstance(content, list):
                    # 多模态消息
                    text_parts = []
                    image_placeholders = []
                    
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            elif item.get("type") == "image_url":
                                image_url = item.get("image_url", {})
                                url = image_url.get("url", "") if isinstance(image_url, dict) else image_url
                                if url:
                                    pil_image = self._parse_image_input(url)
                                    pil_images.append(pil_image)
                                    image_placeholders.append("<|vision_start|><|image_pad|><|vision_end|>")
                    
                    # 图片占位符 + 文本
                    user_content = "".join(image_placeholders) + " ".join(text_parts)
                    prompt_parts.append(f"<|im_start|>user\n{user_content}<|im_end|>\n")
            elif role == "assistant":
                prompt_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>\n")
        
        # 添加 assistant 开始标记
        prompt_parts.append("<|im_start|>assistant\n")
        
        return "".join(prompt_parts), pil_images
    
    def analyze_image(
        self,
        image: str,
        prompt: str = "请描述这张图片",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> VisionInferenceResult:
        """
        分析单张图像（同步方法，仅支持 llm 引擎）
        
        注意：此方法仅在 engine_type='llm' 时可用。
        如果使用 async 引擎，请使用流式接口 (stream=true)。
        
        Args:
            image: 图像URL或base64编码
            prompt: 分析提示词
            max_tokens: 最大生成token数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            VisionInferenceResult: 推理结果
            
        Raises:
            RuntimeError: 当使用 async 引擎时抛出，提示使用流式接口
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("VLM Model is not ready. Please load the model first.")
        
        # async 引擎不支持同步调用
        if self._engine_type == 'async':
            raise RuntimeError(
                "Async engine does not support synchronous requests. "
                "Please use streaming mode (stream=true) for async engine, "
                "or use /v1/vision/completions with stream=true."
            )
        
        # 使用 LLM 引擎
        if self._llm is None:
            raise RuntimeError("LLM engine is not initialized.")
        
        start_time = time.time()
        self._increment_total_requests()
        
        try:
            sampling_params = self._create_sampling_params(
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # 解析图片
            pil_image = self._parse_image_input(image)
            
            # 使用 Qwen3-VL 格式的 prompt（带有 <image> 占位符）
            # vLLM 会自动替换占位符
            full_prompt = f"<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>{prompt}<|im_end|>\n<|im_start|>assistant\n"
            
            # 准备多模态输入
            multi_modal_data = {"image": pil_image}
            
            # 执行推理
            outputs = self._llm.generate(
                [{
                    "prompt": full_prompt,
                    "multi_modal_data": multi_modal_data
                }],
                sampling_params=sampling_params
            )
            
            output = outputs[0]
            latency_ms = (time.time() - start_time) * 1000
            
            prompt_tokens = len(output.prompt_token_ids) if hasattr(output, 'prompt_token_ids') else 0
            completion_tokens = len(output.outputs[0].token_ids) if output.outputs else 0
            total_tokens = prompt_tokens + completion_tokens
            tokens_per_second = (completion_tokens / (latency_ms / 1000)) if latency_ms > 0 else 0
            
            result = VisionInferenceResult(
                request_id=getattr(output, 'request_id', 'unknown'),
                prompt=prompt,
                images=[image],
                generated_text=output.outputs[0].text if output.outputs else "",
                finish_reason=output.outputs[0].finish_reason if output.outputs else "unknown",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                tokens_per_second=tokens_per_second
            )
            
            self._increment_success(latency_ms)
            self.log.debug(f"Image analysis completed: {completion_tokens} tokens in {latency_ms:.2f}ms")
            return result
            
        except Exception as e:
            self._increment_failed()
            self.log.error(f"Image analysis failed: {e}")
            raise
    
    def analyze_images(
        self,
        images: List[str],
        prompt: str = "请分析这些图片",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> VisionInferenceResult:
        """
        分析多张图像（同步方法，仅支持 llm 引擎）
        
        注意：此方法仅在 engine_type='llm' 时可用。
        如果使用 async 引擎，请使用流式接口 (stream=true)。
        
        Args:
            images: 图像URL或base64编码列表
            prompt: 分析提示词
            max_tokens: 最大生成token数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            VisionInferenceResult: 推理结果
            
        Raises:
            RuntimeError: 当使用 async 引擎时抛出，提示使用流式接口
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("VLM Model is not ready. Please load the model first.")
        
        # async 引擎不支持同步调用
        if self._engine_type == 'async':
            raise RuntimeError(
                "Async engine does not support synchronous requests. "
                "Please use streaming mode (stream=true) for async engine, "
                "or use /v1/vision/completions with stream=true."
            )
        
        # 使用 LLM 引擎
        if self._llm is None:
            raise RuntimeError("LLM engine is not initialized.")
        
        start_time = time.time()
        self._increment_total_requests()
        
        try:
            sampling_params = self._create_sampling_params(
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # 解析所有图片
            pil_images = [self._parse_image_input(img) for img in images]
            
            # 使用 Qwen3-VL 格式，每个图片一个占位符
            image_placeholders = "".join(["<|vision_start|><|image_pad|><|vision_end|>" for _ in pil_images])
            full_prompt = f"<|im_start|>user\n{image_placeholders}{prompt}<|im_end|>\n<|im_start|>assistant\n"
            
            # 准备多模态输入
            multi_modal_data = {"image": pil_images}
            
            # 执行推理
            outputs = self._llm.generate(
                [{
                    "prompt": full_prompt,
                    "multi_modal_data": multi_modal_data
                }],
                sampling_params=sampling_params
            )
            
            output = outputs[0]
            latency_ms = (time.time() - start_time) * 1000
            
            prompt_tokens = len(output.prompt_token_ids) if hasattr(output, 'prompt_token_ids') else 0
            completion_tokens = len(output.outputs[0].token_ids) if output.outputs else 0
            total_tokens = prompt_tokens + completion_tokens
            tokens_per_second = (completion_tokens / (latency_ms / 1000)) if latency_ms > 0 else 0
            
            result = VisionInferenceResult(
                request_id=getattr(output, 'request_id', 'unknown'),
                prompt=prompt,
                images=images,
                generated_text=output.outputs[0].text if output.outputs else "",
                finish_reason=output.outputs[0].finish_reason if output.outputs else "unknown",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                tokens_per_second=tokens_per_second
            )
            
            self._increment_success(latency_ms)
            self.log.debug(f"Multi-image analysis completed: {completion_tokens} tokens in {latency_ms:.2f}ms")
            return result
            
        except Exception as e:
            self._increment_failed()
            self.log.error(f"Multi-image analysis failed: {e}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> VisionInferenceResult:
        """
        多模态对话（同步方法，仅支持 llm 引擎）
        
        注意：此方法仅在 engine_type='llm' 时可用。
        如果使用 async 引擎，请使用流式接口 (stream=true)。
        
        Args:
            messages: 消息列表（支持图像内容）
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            **kwargs: 其他参数
            
        Returns:
            VisionInferenceResult: 推理结果
            
        Raises:
            RuntimeError: 当使用 async 引擎时抛出，提示使用流式接口
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("VLM Model is not ready. Please load the model first.")
        
        # async 引擎不支持同步调用
        if self._engine_type == 'async':
            raise RuntimeError(
                "Async engine does not support synchronous requests. "
                "Please use streaming mode (stream=true) for async engine."
            )
        
        # 使用 LLM 引擎同步执行
        if self._llm is None:
            raise RuntimeError("LLM engine is not initialized.")
        return self._chat_sync(messages, max_tokens, temperature, top_p, top_k, stop, **kwargs)
    
    def _chat_sync(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> VisionInferenceResult:
        """使用 LLM 类的同步推理"""
        start_time = time.time()
        self._increment_total_requests()
        
        try:
            sampling_params = self._create_sampling_params(
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
                **kwargs
            )
            
            # 构建 prompt 和提取图片
            prompt, pil_images = self._build_prompt_from_messages(messages)
            
            # 执行推理
            if pil_images:
                multi_modal_data = {"image": pil_images if len(pil_images) > 1 else pil_images[0]}
                outputs = self._llm.generate(
                    [{
                        "prompt": prompt,
                        "multi_modal_data": multi_modal_data
                    }],
                    sampling_params=sampling_params
                )
            else:
                outputs = self._llm.generate([prompt], sampling_params=sampling_params)
            
            output = outputs[0]
            latency_ms = (time.time() - start_time) * 1000
            
            prompt_tokens = len(output.prompt_token_ids) if hasattr(output, 'prompt_token_ids') else 0
            completion_tokens = len(output.outputs[0].token_ids) if output.outputs else 0
            total_tokens = prompt_tokens + completion_tokens
            tokens_per_second = (completion_tokens / (latency_ms / 1000)) if latency_ms > 0 else 0
            
            result = VisionInferenceResult(
                request_id=getattr(output, 'request_id', 'unknown'),
                prompt=str(messages),
                images=[],  # 图片已嵌入消息
                generated_text=output.outputs[0].text if output.outputs else "",
                finish_reason=output.outputs[0].finish_reason if output.outputs else "unknown",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                tokens_per_second=tokens_per_second
            )
            
            self._increment_success(latency_ms)
            self.log.debug(f"Vision chat (sync) completed: {completion_tokens} tokens in {latency_ms:.2f}ms")
            return result
            
        except Exception as e:
            self._increment_failed()
            self.log.error(f"Vision chat (sync) failed: {e}")
            raise
    
    async def _chat_async(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> VisionInferenceResult:
        """使用 AsyncLLMEngine 的异步推理"""
        import uuid as uuid_module
        request_id = f"async-{uuid_module.uuid4().hex[:16]}"
        start_time = time.time()
        self._increment_total_requests()
        
        try:
            sampling_params = self._create_sampling_params(
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
                **kwargs
            )
            
            # 构建 prompt 和提取图片
            prompt, pil_images = self._build_prompt_from_messages(messages)
            
            # 准备输入
            if pil_images:
                multi_modal_data = {"image": pil_images if len(pil_images) > 1 else pil_images[0]}
                inputs = {
                    "prompt": prompt,
                    "multi_modal_data": multi_modal_data
                }
            else:
                inputs = {"prompt": prompt}
            
            # 使用异步引擎生成（收集完整结果）
            generated_text = ""
            prompt_tokens = 0
            completion_tokens = 0
            finish_reason = None
            
            async for output in self._async_engine.generate(
                inputs,
                sampling_params,
                request_id=request_id
            ):
                if output.outputs:
                    generated_text = output.outputs[0].text
                    if hasattr(output, 'prompt_token_ids'):
                        prompt_tokens = len(output.prompt_token_ids)
                    completion_tokens = len(output.outputs[0].token_ids)
                    if output.finished:
                        finish_reason = output.outputs[0].finish_reason
            
            latency_ms = (time.time() - start_time) * 1000
            total_tokens = prompt_tokens + completion_tokens
            tokens_per_second = (completion_tokens / (latency_ms / 1000)) if latency_ms > 0 else 0
            
            result = VisionInferenceResult(
                request_id=request_id,
                prompt=str(messages),
                images=[],
                generated_text=generated_text,
                finish_reason=finish_reason or "unknown",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                tokens_per_second=tokens_per_second
            )
            
            self._increment_success(latency_ms)
            self.log.debug(f"Vision chat (async) completed: {completion_tokens} tokens in {latency_ms:.2f}ms")
            return result
            
        except Exception as e:
            self._increment_failed()
            self.log.error(f"Vision chat (async) failed: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> Generator[StreamChunk, None, None]:
        """
        Token 级流式多模态对话（真正的流式输出）
        
        使用 AsyncLLMEngine 实现真正的 token 级流式输出，
        每生成一个 token 就立即返回。
        
        Args:
            messages: 消息列表（支持图像内容）
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            **kwargs: 其他参数
            
        Yields:
            StreamChunk: 流式输出块
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("VLM Model is not ready. Please load the model first.")
        
        if self._async_engine is None:
            raise RuntimeError("AsyncLLMEngine is not available. Token-level streaming is disabled.")
        
        import uuid as uuid_module
        request_id = f"stream-{uuid_module.uuid4().hex[:16]}"
        start_time = time.time()
        self._increment_total_requests()
        
        try:
            sampling_params = self._create_sampling_params(
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
                **kwargs
            )
            
            # 构建 prompt 和提取图片
            prompt, pil_images = self._build_prompt_from_messages(messages)
            
            # 准备输入
            if pil_images:
                multi_modal_data = {"image": pil_images if len(pil_images) > 1 else pil_images[0]}
                inputs = {
                    "prompt": prompt,
                    "multi_modal_data": multi_modal_data
                }
            else:
                inputs = {"prompt": prompt}
            
            # 使用异步引擎进行流式生成
            generated_text = ""
            prompt_tokens = 0
            completion_tokens = 0
            finish_reason = None
            
            async for output in self._async_engine.generate(
                inputs,
                sampling_params,
                request_id=request_id
            ):
                # 获取最新生成的文本
                if output.outputs:
                    current_text = output.outputs[0].text
                    # 计算增量
                    delta_text = current_text[len(generated_text):]
                    generated_text = current_text
                    
                    # 更新 token 计数
                    if hasattr(output, 'prompt_token_ids'):
                        prompt_tokens = len(output.prompt_token_ids)
                    completion_tokens = len(output.outputs[0].token_ids) if output.outputs else 0
                    
                    # 检查是否完成
                    is_finished = output.finished
                    if is_finished:
                        finish_reason = output.outputs[0].finish_reason
                    
                    # 只在有增量内容或完成时 yield
                    if delta_text or is_finished:
                        yield StreamChunk(
                            request_id=request_id,
                            delta_text=delta_text,
                            is_finished=is_finished,
                            finish_reason=finish_reason,
                            prompt_tokens=prompt_tokens if is_finished else 0,
                            completion_tokens=completion_tokens if is_finished else 0,
                            total_tokens=(prompt_tokens + completion_tokens) if is_finished else 0
                        )
            
            latency_ms = (time.time() - start_time) * 1000
            self._increment_success(latency_ms)
            self.log.debug(f"Stream chat completed: {completion_tokens} tokens in {latency_ms:.2f}ms")
            
        except Exception as e:
            self._increment_failed()
            self.log.error(f"Stream chat failed: {e}")
            # 发送错误块
            yield StreamChunk(
                request_id=request_id,
                delta_text="",
                is_finished=True,
                finish_reason="error"
            )
            raise
    
    def chat_stream_chunk(
        self,
        messages: List[Dict[str, Any]],
        chunk_size: int = 10,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> Generator[StreamChunk, None, None]:
        """
        分块流式多模态对话（伪流式输出）
        
        先完整生成内容，再按 chunk_size 分块返回。
        适用于不支持 AsyncLLMEngine 的场景。
        
        Args:
            messages: 消息列表（支持图像内容）
            chunk_size: 每块字符数
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            **kwargs: 其他参数
            
        Yields:
            StreamChunk: 流式输出块
        """
        import uuid as uuid_module
        request_id = f"chunk-{uuid_module.uuid4().hex[:16]}"
        
        try:
            # 先完整生成（直接使用同步方法，避免在事件循环中调用 asyncio.run）
            if self._engine_type == 'async':
                # async 引擎模式下，chunk 流式不可用，应该使用 token 流式
                raise RuntimeError("Chunk streaming is not supported with async engine. Use token streaming instead.")
            
            # 使用 LLM 引擎同步生成
            result = self._chat_sync(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
                **kwargs
            )
            
            text = result.generated_text
            
            # 分块输出
            pos = 0
            while pos < len(text):
                chunk_text = text[pos:pos + chunk_size]
                is_last = (pos + chunk_size >= len(text))
                
                yield StreamChunk(
                    request_id=request_id,
                    delta_text=chunk_text,
                    is_finished=is_last,
                    finish_reason=result.finish_reason if is_last else None,
                    prompt_tokens=result.prompt_tokens if is_last else 0,
                    completion_tokens=result.completion_tokens if is_last else 0,
                    total_tokens=result.total_tokens if is_last else 0
                )
                
                pos += chunk_size
                
        except Exception as e:
            self.log.error(f"Chunk stream chat failed: {e}")
            yield StreamChunk(
                request_id=request_id,
                delta_text="",
                is_finished=True,
                finish_reason="error"
            )
            raise
    
    def is_token_stream_available(self) -> bool:
        """检查 token 级流式是否可用"""
        return self._engine_type == 'async' and self._async_engine is not None
    
    def get_engine_type(self) -> str:
        """获取当前使用的引擎类型"""
        return self._engine_type
    
    def is_enabled(self) -> bool:
        """检查模型是否启用"""
        return self._enable
    
    def get_gpu_resources(self) -> List[ResourceInfo]:
        """获取GPU资源使用情况"""
        resources = []
        
        try:
            import pynvml
            pynvml.nvmlInit()
            
            device_count = pynvml.nvmlDeviceGetCount()
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_mb = mem_info.total / (1024 * 1024)
                used_mb = mem_info.used / (1024 * 1024)
                free_mb = mem_info.free / (1024 * 1024)
                mem_util = used_mb / total_mb if total_mb > 0 else 0
                
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_util = util.gpu / 100.0
                except:
                    gpu_util = 0.0
                
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temp = 0.0
                
                resource = ResourceInfo(
                    gpu_id=i,
                    gpu_name=name,
                    total_memory_mb=total_mb,
                    used_memory_mb=used_mb,
                    free_memory_mb=free_mb,
                    memory_utilization=mem_util,
                    gpu_utilization=gpu_util,
                    temperature=temp
                )
                resources.append(resource)
            
            pynvml.nvmlShutdown()
            
        except ImportError:
            self.log.debug("pynvml not available, falling back to torch")
            try:
                import torch
                if torch.cuda.is_available():
                    for i in range(torch.cuda.device_count()):
                        props = torch.cuda.get_device_properties(i)
                        torch.cuda.set_device(i)
                        total_mb = props.total_memory / (1024 * 1024)
                        reserved_mb = torch.cuda.memory_reserved(i) / (1024 * 1024)
                        
                        resource = ResourceInfo(
                            gpu_id=i,
                            gpu_name=props.name,
                            total_memory_mb=total_mb,
                            used_memory_mb=reserved_mb,
                            free_memory_mb=total_mb - reserved_mb,
                            memory_utilization=reserved_mb / total_mb if total_mb > 0 else 0
                        )
                        resources.append(resource)
            except Exception as e:
                self.log.error(f"Failed to get GPU resources via torch: {e}")
                
        except Exception as e:
            self.log.error(f"Failed to get GPU resources: {e}")
        
        return resources
    
    def health_check(self) -> HealthStatus:
        """模型健康检测"""
        uptime = time.time() - self._start_time if self._start_time else 0
        avg_latency = self._total_latency_ms / self._successful_requests if self._successful_requests > 0 else 0
        
        health = HealthStatus(
            is_healthy=self._status == ModelStatus.READY,
            model_status=self._status,
            model_name=self._model_path,
            uptime_seconds=uptime,
            total_requests=self._total_requests,
            successful_requests=self._successful_requests,
            failed_requests=self._failed_requests,
            avg_latency_ms=avg_latency,
            gpu_resources=self.get_gpu_resources()
        )
        
        if self._status == ModelStatus.READY:
            try:
                if self._engine_type == 'async' and self._async_engine is not None:
                    # AsyncLLMEngine 健康检查 - 只检查引擎是否存在
                    health.is_healthy = True
                elif self._llm is not None:
                    # LLM 引擎健康检查 - 简单测试
                    test_output = self._llm.generate(
                        ["Hello"],
                        SamplingParams(max_tokens=1, temperature=0)
                    )
                    if not test_output:
                        health.is_healthy = False
                        health.error_message = "VLM inference test failed"
                else:
                    health.is_healthy = False
                    health.error_message = "No engine initialized"
            except Exception as e:
                health.is_healthy = False
                health.error_message = f"VLM health check failed: {str(e)}"
        
        return health
    
    def ping(self) -> bool:
        """简单的可用性检测"""
        if self._status != ModelStatus.READY:
            return False
        if self._engine_type == 'async':
            return self._async_engine is not None
        else:
            return self._llm is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        with self._stats_lock:
            statistics = {
                "total_requests": self._total_requests,
                "successful_requests": self._successful_requests,
                "failed_requests": self._failed_requests,
                "active_requests": self._active_requests,
                "avg_latency_ms": self._total_latency_ms / self._successful_requests if self._successful_requests > 0 else 0
            }
        
        return {
            "model_path": self._model_path,
            "device": self._device,
            "status": self._status.value,
            "model_type": "vlm",
            "enable": self._enable,
            "engine_type": self._engine_type,
            "token_stream_available": self.is_token_stream_available(),
            "gpu_memory_utilization": self._gpu_memory_utilization,
            "tensor_parallel_size": self._tensor_parallel_size,
            "max_model_len": self._max_model_len,
            "max_gen_len": self._max_gen_len,
            "temperature": self._temperature,
            "top_p": self._top_p,
            "top_k": self._top_k,
            "uptime_seconds": time.time() - self._start_time if self._start_time else 0,
            "statistics": statistics
        }
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        with self._stats_lock:
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._total_latency_ms = 0.0
            self._active_requests = 0
        self.log.info("VLM Statistics reset")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.shutdown()
        return False
    
    def shutdown(self) -> None:
        """关闭服务，释放所有资源"""
        try:
            if self._llm is not None:
                self.unload_model()
            
            if self._cleanup_registered:
                try:
                    atexit.unregister(self._cleanup_on_exit)
                    self._cleanup_registered = False
                except Exception:
                    pass
            
            self.log.info("VLMService shutdown complete")
            
        except Exception as e:
            self.log.error(f"Error during VLM shutdown: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            if hasattr(self, '_llm') and self._llm is not None:
                del self._llm
                self._llm = None
                
                try:
                    gc.collect()
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                        torch.cuda.empty_cache()
                except Exception:
                    pass
        except Exception:
            pass

