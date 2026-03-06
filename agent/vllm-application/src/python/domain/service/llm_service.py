'''
LLM服务,基于vllm框架实现
提供模型推理、健康检测、资源查询等功能

并发支持说明:
- vLLM内部使用异步调度器，天然支持并发推理请求
- generate() / generate_batch() / chat() 等方法可被多线程同时调用
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
import asyncio
from typing import Dict, Any, List, Optional, Generator, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

from vllm import LLM, SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.outputs import RequestOutput


@dataclass
class StreamChunk:
    """流式输出块数据类"""
    request_id: str
    delta_text: str
    is_finished: bool = False
    finish_reason: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

from infrastructure.common.logging.logging import logger, init_logging
from infrastructure.common.error.errcode import (
    ErrorCode, create_error, success, is_success,
    ErrorCode as EC
)
from infrastructure.config.sys_config import SysConfig
from infrastructure.llm.llm_model_status import ModelStatus
from infrastructure.llm.llm_work_info import InferenceResult, ResourceInfo, HealthStatus


@logger()
class LLMService:
    """
    LLM服务类 - 基于vLLM框架
    
    提供以下功能:
    - 模型加载与初始化
    - 单条/批量推理（支持并发）
    - 流式推理
    - 模型健康检测
    - GPU资源查询
    
    线程安全说明:
    - vLLM内部使用异步调度器，generate()方法天然支持多线程并发调用
    - 统计信息使用锁保护，确保计数准确
    """
    
    def __init__(self, config: SysConfig, auto_load: bool = True):
        """
        初始化LLM服务
        
        Args:
            config: 系统配置对象
            auto_load: 是否自动加载模型，默认True
        """
        try:
            self.llm_config = config.get_llm_config()
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
            self._model_path = self.llm_config.get('model', '')
            self._device = self.llm_config.get('device', 'cuda:0')
            self._gpu_memory_utilization = self.llm_config.get('gpu_memory_utilization', 0.9)
            self._tensor_parallel_size = self.llm_config.get('tensor_parallel_size', 1)
            self._max_model_len = self.llm_config.get('max_model_len', 4096)
            
            # 生成参数配置
            self._max_gen_len = self.llm_config.get('max_gen_len', 1024)
            self._temperature = self.llm_config.get('temperature', 0.6)
            self._top_p = self.llm_config.get('top_p', 0.9)
            self._top_k = self.llm_config.get('top_k', 40)
            
            # 引擎类型配置: 'llm' 或 'async'
            # - llm: 使用 LLM 类（同步模式，支持 chunk 流式）
            # - async: 使用 AsyncLLMEngine（异步模式，支持真正的 token 级流式）
            self._engine_type = self.llm_config.get('engine_type', 'llm').lower()
            
            self.log.info(f"LLMService initialized with model: {self._model_path}, engine_type: {self._engine_type}")
            
            # 是否启用模型
            self._enable = self.llm_config.get('enable', True)
            
            # 注册进程退出清理函数
            self._cleanup_registered = False
            self._register_cleanup()
            
            # 根据 enable 配置决定是否加载模型
            if auto_load and self._enable:
                self.load_model()
            elif not self._enable:
                self.log.info(f"LLM model disabled by config (enable=false)")
            
                
        except Exception as e:
            self._status = ModelStatus.ERROR
            self.log.error(f"LLMService initialization failed: {e}")
            raise e
    
    def _register_cleanup(self) -> None:
        """注册进程退出时的清理函数"""
        if not self._cleanup_registered:
            atexit.register(self._cleanup_on_exit)
            self._cleanup_registered = True
            self.log.debug("Cleanup function registered for process exit")
    
    def _cleanup_on_exit(self) -> None:
        """
        进程退出时的清理函数
        由 atexit 自动调用，确保 GPU 资源被释放
        """
        try:
            if self._llm is not None:
                self.log.info("Process exiting, releasing GPU resources...")
                self.unload_model()
        except Exception as e:
            # 在退出时不抛出异常
            print(f"Warning: Error during cleanup on exit: {e}")
    
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
        加载模型
        
        注意: 此方法应在服务启动时调用一次，模型加载后即可支持并发推理
        
        Returns:
            bool: 加载是否成功
        """
        if self._status == ModelStatus.READY:
            self.log.info("Model already loaded")
            return True
        
        # 设置 CUDA_VISIBLE_DEVICES 环境变量来指定 GPU
        if self._device and self._device.startswith("cuda:"):
            gpu_id = self._device.split(":")[1]
            import os
            os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id
            self.log.info(f"Set CUDA_VISIBLE_DEVICES={gpu_id} for device {self._device}")
        
        try:
            self._status = ModelStatus.LOADING
            self.log.info(f"Loading model from: {self._model_path}, engine_type: {self._engine_type}")
            
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
                    dtype="auto"
                )
                self.log.info("Using LLM engine for chunk-level streaming")
            
            self._status = ModelStatus.READY
            self._start_time = time.time()
            self.log.info(f"Model loaded successfully: {self._model_path}")
            return True
            
        except Exception as e:
            self._status = ModelStatus.ERROR
            self.log.error(f"Failed to load model: {e}")
            return False
    
    def _init_async_engine(self) -> None:
        """
        初始化异步引擎（用于 token 级流式输出）
        """
        try:
            engine_args = AsyncEngineArgs(
                model=self._model_path,
                gpu_memory_utilization=self._gpu_memory_utilization,
                tensor_parallel_size=self._tensor_parallel_size,
                max_model_len=self._max_model_len,
                trust_remote_code=True,
                dtype="auto"
            )
            self._async_engine = AsyncLLMEngine.from_engine_args(engine_args)
            self.log.info("AsyncLLMEngine initialized for streaming")
        except Exception as e:
            self.log.error(f"AsyncLLMEngine initialization failed: {e}")
            self._async_engine = None
            raise
    
    def unload_model(self) -> bool:
        """
        卸载模型，释放GPU资源
        
        注意: 此方法应在服务关闭时调用，调用前请确保没有正在进行的推理请求
        
        Returns:
            bool: 卸载是否成功
        """
        try:
            if self._llm is not None:
                # 删除vLLM引擎实例
                del self._llm
                self._llm = None
            
            # 清理异步引擎
            if self._async_engine is not None:
                del self._async_engine
                self._async_engine = None
                
            # 强制释放GPU内存
            self._release_gpu_memory()
                
            self._status = ModelStatus.UNLOADED
            self.log.info("Model unloaded successfully")
            return True
            
        except Exception as e:
            self.log.error(f"Failed to unload model: {e}")
            return False
    
    def _release_gpu_memory(self) -> None:
        """
        释放GPU内存资源
        
        执行以下清理操作:
        1. 触发Python垃圾回收
        2. 清空CUDA缓存
        3. 同步CUDA设备
        4. 重置CUDA内存统计
        """
        try:
            # 1. 强制垃圾回收
            gc.collect()
            
            # 2. 尝试释放PyTorch CUDA资源
            try:
                import torch
                if torch.cuda.is_available():
                    # 同步所有CUDA流，确保所有操作完成
                    torch.cuda.synchronize()
                    
                    # 清空CUDA缓存
                    torch.cuda.empty_cache()
                    
                    # 重置内存统计（用于调试）
                    for i in range(torch.cuda.device_count()):
                        try:
                            torch.cuda.reset_peak_memory_stats(i)
                            torch.cuda.reset_accumulated_memory_stats(i)
                        except Exception:
                            pass
                    
                    self.log.debug("PyTorch CUDA cache cleared")
            except ImportError:
                pass
            except Exception as e:
                self.log.warning(f"Failed to clear PyTorch CUDA cache: {e}")
            
            # 3. 再次垃圾回收
            gc.collect()
            
        except Exception as e:
            self.log.warning(f"Error during GPU memory release: {e}")
    
    def _create_sampling_params(
        self,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> SamplingParams:
        """
        创建采样参数
        
        Args:
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            **kwargs: 其他采样参数
            
        Returns:
            SamplingParams: vLLM采样参数对象
        """
        return SamplingParams(
            max_tokens=max_tokens or self._max_gen_len,
            temperature=temperature if temperature is not None else self._temperature,
            top_p=top_p if top_p is not None else self._top_p,
            top_k=top_k if top_k is not None else self._top_k,
            stop=stop,
            **kwargs
        )
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> InferenceResult:
        """
        单条推理（同步方法，仅支持 llm 引擎）
        
        注意：此方法仅在 engine_type='llm' 时可用。
        如果使用 async 引擎，请使用流式接口 (stream=true)。
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            **kwargs: 其他采样参数
            
        Returns:
            InferenceResult: 推理结果
            
        Raises:
            RuntimeError: 模型未加载或使用 async 引擎时抛出
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("Model is not ready. Please load the model first.")
        
        # async 引擎不支持同步调用
        if self._engine_type == 'async':
            raise RuntimeError(
                "Async engine does not support synchronous requests. "
                "Please use streaming mode (stream=true) for async engine."
            )
        
        # 使用 LLM 引擎同步执行
        if self._llm is None:
            raise RuntimeError("LLM engine is not initialized.")
        return self._generate_sync(prompt, max_tokens, temperature, top_p, top_k, stop, **kwargs)
    
    def _generate_sync(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> InferenceResult:
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
            
            # vLLM内部支持并发，多线程可同时调用generate
            outputs = self._llm.generate([prompt], sampling_params)
            output = outputs[0]
            
            latency_ms = (time.time() - start_time) * 1000
            
            # 计算token统计
            prompt_tokens = len(output.prompt_token_ids)
            completion_tokens = len(output.outputs[0].token_ids)
            total_tokens = prompt_tokens + completion_tokens
            
            # 计算生成速度
            tokens_per_second = (completion_tokens / (latency_ms / 1000)) if latency_ms > 0 else 0
            
            result = InferenceResult(
                request_id=output.request_id,
                prompt=prompt,
                generated_text=output.outputs[0].text,
                finish_reason=output.outputs[0].finish_reason or "unknown",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                tokens_per_second=tokens_per_second
            )
            
            self._increment_success(latency_ms)
            
            self.log.debug(f"Inference (sync) completed: {completion_tokens} tokens in {latency_ms:.2f}ms")
            return result
        
        except Exception as e:
            self._increment_failed()
            self.log.error(f"Inference (sync) failed: {e}")
            raise
    
    async def _generate_async(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> InferenceResult:
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
            
            # 使用异步引擎生成（收集完整结果）
            generated_text = ""
            prompt_tokens = 0
            completion_tokens = 0
            finish_reason = None
            
            async for output in self._async_engine.generate(
                {"prompt": prompt},
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
            
            result = InferenceResult(
                request_id=request_id,
                prompt=prompt,
                generated_text=generated_text,
                finish_reason=finish_reason or "unknown",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                tokens_per_second=tokens_per_second
            )
            
            self._increment_success(latency_ms)
            self.log.debug(f"Inference (async) completed: {completion_tokens} tokens in {latency_ms:.2f}ms")
            return result
            
        except Exception as e:
            self._increment_failed()
            self.log.error(f"Inference (async) failed: {e}")
            raise
    
    def generate_batch(
        self,
        prompts: List[str],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> List[InferenceResult]:
        """
        批量推理
        
        Args:
            prompts: 输入提示词列表
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            **kwargs: 其他采样参数
            
        Returns:
            List[InferenceResult]: 推理结果列表
            
        Raises:
            RuntimeError: 模型未加载时抛出
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("Model is not ready. Please load the model first.")
        
        # generate_batch 只支持 LLM 引擎
        if self._engine_type == 'async':
            raise RuntimeError("Batch generation is not supported with async engine. Use generate() instead.")
        
        if self._llm is None:
            raise RuntimeError("LLM engine is not initialized.")
        
        start_time = time.time()
        batch_size = len(prompts)
        self._increment_total_requests(batch_size)
        
        try:
            sampling_params = self._create_sampling_params(
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
                **kwargs
            )
            
            # vLLM内部会自动优化批量推理，高效处理并发
            outputs = self._llm.generate(prompts, sampling_params)
            
            total_latency_ms = (time.time() - start_time) * 1000
            avg_latency_ms = total_latency_ms / batch_size
            
            results = []
            for i, output in enumerate(outputs):
                prompt_tokens = len(output.prompt_token_ids)
                completion_tokens = len(output.outputs[0].token_ids)
                total_tokens = prompt_tokens + completion_tokens
                tokens_per_second = (completion_tokens / (avg_latency_ms / 1000)) if avg_latency_ms > 0 else 0
                
                result = InferenceResult(
                    request_id=output.request_id,
                    prompt=prompts[i],
                    generated_text=output.outputs[0].text,
                    finish_reason=output.outputs[0].finish_reason or "unknown",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=avg_latency_ms,
                    tokens_per_second=tokens_per_second
                )
                results.append(result)
            
            self._increment_success(total_latency_ms, batch_size)
            
            self.log.debug(f"Batch inference completed: {batch_size} prompts in {total_latency_ms:.2f}ms")
            return results
            
        except Exception as e:
            self._increment_failed(batch_size)
            self.log.error(f"Batch inference failed: {e}")
            raise
    
    def generate_stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        chunk_size: int = 5,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        流式推理 - 模拟逐token生成
        
        由于vLLM的LLM类是批处理模式，这里通过分块方式模拟流式输出。
        如需真正的token级流式，请使用AsyncLLMEngine。
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            chunk_size: 每次yield的字符数（模拟流式）
            **kwargs: 其他采样参数
            
        Yields:
            str: 逐步生成的文本片段
            
        Raises:
            RuntimeError: 模型未加载时抛出
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("Model is not ready. Please load the model first.")
        
        # generate_stream (chunk 模式) 只支持 LLM 引擎
        if self._engine_type == 'async':
            raise RuntimeError("Chunk streaming is not supported with async engine. Use chat_stream() instead.")
        
        if self._llm is None:
            raise RuntimeError("LLM engine is not initialized.")
        
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
            
            # vLLM的LLM.generate()是同步批处理，返回List[RequestOutput]
            outputs = self._llm.generate(
                [prompt], 
                sampling_params,
                use_tqdm=False
            )
            
            if not outputs:
                self._increment_failed()
                return
            
            output = outputs[0]
            generated_text = output.outputs[0].text
            
            # 模拟流式输出：将完整文本分块yield
            # 这样可以让客户端逐步接收数据
            pos = 0
            while pos < len(generated_text):
                chunk = generated_text[pos:pos + chunk_size]
                yield chunk
                pos += chunk_size
            
            latency_ms = (time.time() - start_time) * 1000
            self._increment_success(latency_ms)
            
        except Exception as e:
            self._increment_failed()
            self.log.error(f"Stream inference failed: {e}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> InferenceResult:
        """
        对话式推理 - 支持多轮对话
        
        Args:
            messages: 对话历史，格式: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            system_prompt: 系统提示词
            **kwargs: 其他采样参数
            
        Returns:
            InferenceResult: 推理结果
        """
        # 构建对话格式的prompt
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"<|system|>\n{system_prompt}\n")
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                prompt_parts.append(f"<|user|>\n{content}\n")
            elif role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{content}\n")
            elif role == "system":
                prompt_parts.append(f"<|system|>\n{content}\n")
        
        # 添加assistant角色前缀，引导模型回复
        prompt_parts.append("<|assistant|>\n")
        
        prompt = "".join(prompt_parts)
        
        return self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stop=stop,
            **kwargs
        )
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Token 级流式对话推理（使用 AsyncLLMEngine）
        
        Args:
            messages: 对话历史
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            system_prompt: 系统提示词
            **kwargs: 其他采样参数
            
        Yields:
            StreamChunk: 流式输出块
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("Model is not ready. Please load the model first.")
        
        if self._engine_type != 'async' or self._async_engine is None:
            raise RuntimeError("Token streaming requires AsyncLLMEngine. Set engine_type to 'async'.")
        
        import uuid as uuid_module
        request_id = f"stream-{uuid_module.uuid4().hex[:16]}"
        start_time = time.time()
        self._increment_total_requests()
        
        try:
            # 构建 prompt
            prompt = self._build_chat_prompt(messages, system_prompt)
            
            sampling_params = self._create_sampling_params(
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
                **kwargs
            )
            
            generated_text = ""
            prompt_tokens = 0
            completion_tokens = 0
            finish_reason = None
            
            async for output in self._async_engine.generate(
                {"prompt": prompt},
                sampling_params,
                request_id=request_id
            ):
                if output.outputs:
                    current_text = output.outputs[0].text
                    delta_text = current_text[len(generated_text):]
                    generated_text = current_text
                    
                    if hasattr(output, 'prompt_token_ids'):
                        prompt_tokens = len(output.prompt_token_ids)
                    completion_tokens = len(output.outputs[0].token_ids) if output.outputs else 0
                    
                    is_finished = output.finished
                    if is_finished:
                        finish_reason = output.outputs[0].finish_reason
                    
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
            yield StreamChunk(
                request_id=request_id,
                delta_text="",
                is_finished=True,
                finish_reason="error"
            )
            raise
    
    def chat_stream_chunk(
        self,
        messages: List[Dict[str, str]],
        chunk_size: int = 10,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Generator[StreamChunk, None, None]:
        """
        分块流式对话（伪流式输出，使用 LLM 引擎）
        
        先完整生成内容，再按 chunk_size 分块返回。
        适用于不支持 AsyncLLMEngine 的场景。
        
        Args:
            messages: 对话历史
            chunk_size: 每块字符数
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: Top-p采样参数
            top_k: Top-k采样参数
            stop: 停止词列表
            system_prompt: 系统提示词
            **kwargs: 其他参数
            
        Yields:
            StreamChunk: 流式输出块
        """
        import uuid as uuid_module
        request_id = f"chunk-{uuid_module.uuid4().hex[:16]}"
        
        try:
            if self._engine_type == 'async':
                raise RuntimeError("Chunk streaming is not supported with async engine. Use chat_stream() instead.")
            
            # 使用 LLM 引擎同步生成
            result = self.chat(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop,
                system_prompt=system_prompt,
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
    
    def _build_chat_prompt(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """构建对话格式的 prompt"""
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"<|system|>\n{system_prompt}\n")
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                prompt_parts.append(f"<|user|>\n{content}\n")
            elif role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{content}\n")
            elif role == "system":
                prompt_parts.append(f"<|system|>\n{content}\n")
        
        prompt_parts.append("<|assistant|>\n")
        return "".join(prompt_parts)
    
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
        """
        获取GPU资源使用情况
        
        Returns:
            List[ResourceInfo]: GPU资源信息列表
        """
        resources = []
        
        try:
            # 尝试使用pynvml获取详细GPU信息
            import pynvml
            pynvml.nvmlInit()
            
            device_count = pynvml.nvmlDeviceGetCount()
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # 获取GPU名称
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                
                # 获取内存信息
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_mb = mem_info.total / (1024 * 1024)
                used_mb = mem_info.used / (1024 * 1024)
                free_mb = mem_info.free / (1024 * 1024)
                mem_util = used_mb / total_mb if total_mb > 0 else 0
                
                # 获取GPU利用率
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_util = util.gpu / 100.0
                except:
                    gpu_util = 0.0
                
                # 获取温度
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
            self.log.warning("pynvml not available, falling back to torch")
            # 回退到torch方式获取基本信息
            try:
                import torch
                if torch.cuda.is_available():
                    for i in range(torch.cuda.device_count()):
                        props = torch.cuda.get_device_properties(i)
                        
                        # 获取当前显存使用
                        torch.cuda.set_device(i)
                        total_mb = props.total_memory / (1024 * 1024)
                        allocated_mb = torch.cuda.memory_allocated(i) / (1024 * 1024)
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
        """
        模型健康检测
        
        Returns:
            HealthStatus: 健康状态信息
        """
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
        
        # 执行简单的推理测试来验证模型可用性
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
                        health.error_message = "Model inference test failed"
                else:
                    health.is_healthy = False
                    health.error_message = "No engine initialized"
            except Exception as e:
                health.is_healthy = False
                health.error_message = f"Health check failed: {str(e)}"
        
        return health
    
    def ping(self) -> bool:
        """
        简单的可用性检测
        
        Returns:
            bool: 模型是否可用
        """
        if self._status != ModelStatus.READY:
            return False
        if self._engine_type == 'async':
            return self._async_engine is not None
        else:
            return self._llm is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息（线程安全）
        
        Returns:
            Dict[str, Any]: 模型配置和状态信息
        """
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
        """重置统计信息（线程安全）"""
        with self._stats_lock:
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._total_latency_ms = 0.0
            self._active_requests = 0
        self.log.info("Statistics reset")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，自动卸载模型"""
        self.shutdown()
        return False
    
    def shutdown(self) -> None:
        """
        关闭服务，释放所有资源
        
        建议在程序退出前显式调用此方法，以确保资源被正确释放
        """
        try:
            # 卸载模型
            if self._llm is not None:
                self.unload_model()
            
            # 注销 atexit 回调（避免重复清理）
            if self._cleanup_registered:
                try:
                    atexit.unregister(self._cleanup_on_exit)
                    self._cleanup_registered = False
                except Exception:
                    pass
            
            self.log.info("LLMService shutdown complete")
            
        except Exception as e:
            self.log.error(f"Error during shutdown: {e}")
    
    def __del__(self):
        """
        析构函数 - 确保GPU资源释放
        
        注意: Python的析构函数不保证一定被调用，
        建议在程序退出前显式调用 shutdown() 方法
        """
        try:
            # 避免在析构时使用 logger（可能已被销毁）
            if hasattr(self, '_llm') and self._llm is not None:
                # 直接释放资源，不使用 log
                del self._llm
                self._llm = None
                
                # 释放GPU内存
                try:
                    gc.collect()
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                        torch.cuda.empty_cache()
                except Exception:
                    pass
        except Exception:
            # 析构函数中不抛出异常
            pass
