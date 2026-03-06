'''
Embedding服务,基于vLLM框架实现
提供文本向量化功能

并发支持说明:
- vLLM内部使用异步调度器，天然支持并发推理请求
- encode() 方法可被多线程同时调用
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
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from vllm import LLM

from infrastructure.common.logging.logging import logger, init_logging
from infrastructure.common.error.errcode import (
    ErrorCode, create_error, success, is_success,
    ErrorCode as EC
)
from infrastructure.config.sys_config import SysConfig
from infrastructure.llm.llm_model_status import ModelStatus
from infrastructure.llm.llm_work_info import ResourceInfo, HealthStatus


@dataclass
class EmbeddingResult:
    """Embedding 结果数据类"""
    request_id: str
    embeddings: List[List[float]]  # 向量列表
    model: str = ""
    usage: Dict[str, int] = field(default_factory=lambda: {"prompt_tokens": 0, "total_tokens": 0})
    latency_ms: float = 0.0


@logger()
class EmbeddingService:
    """
    Embedding服务类 - 基于vLLM框架
    
    提供以下功能:
    - 模型加载与初始化
    - 单条/批量文本向量化
    - 模型健康检测
    - GPU资源查询
    
    线程安全说明:
    - vLLM内部使用异步调度器，encode()方法天然支持多线程并发调用
    - 统计信息使用锁保护，确保计数准确
    """
    
    def __init__(self, config: SysConfig, auto_load: bool = True):
        """
        初始化Embedding服务
        
        Args:
            config: 系统配置对象
            auto_load: 是否自动加载模型，默认True
        """
        try:
            self.embedding_config = config.get_embedding_config()
            # 后端：vLLM (GPU) 或 HF sentence-transformers (CPU)
            self._backend: str = "vllm"
            self._llm: Optional[LLM] = None
            self._hf_model = None
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
            self._model_path = self.embedding_config.get('model', '')
            self._device = self.embedding_config.get('device', 'cuda:0')
            self._gpu_memory_utilization = self.embedding_config.get('gpu_memory_utilization', 0.5)
            self._tensor_parallel_size = self.embedding_config.get('tensor_parallel_size', 1)
            self._max_model_len = self.embedding_config.get('max_model_len', 8192)
            
            # 是否启用模型
            self._enable = self.embedding_config.get('enable', True)

            # 根据 device 选择后端
            device_lower = str(self._device).lower() if self._device else ""
            if device_lower == "cpu":
                self._backend = "hf"
                self.log.info(f"EmbeddingService initialized with HF backend (CPU), model: {self._model_path}")
            else:
                self._backend = "vllm"
                self.log.info(f"EmbeddingService initialized with vLLM backend, device={self._device}, model: {self._model_path}")
            
            # 注册进程退出清理函数
            self._cleanup_registered = False
            self._register_cleanup()
            
            # 根据 enable 配置决定是否加载模型
            if auto_load and self._enable:
                self.log.info(f"Embedding model loading started")
                if not self.load_model():
                    self.log.error(f"Embedding model loading failed")
                    raise RuntimeError(f"Embedding model loading failed")
            elif not self._enable:
                self.log.info(f"Embedding model disabled by config (enable=false)")
            
        except Exception as e:
            self._status = ModelStatus.ERROR
            self.log.error(f"EmbeddingService initialization failed: {e}")
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
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.unload_model()
        return False
    
    def load_model(self) -> bool:
        """
        加载Embedding模型
        
        Returns:
            bool: 加载成功返回True，失败返回False
        """
        self.log.debug("load embedding model")
        if not self._enable:
            self.log.info("Embedding model loading skipped (enable=false)")
            return False
            
        if self._status == ModelStatus.READY:
            self.log.info("Embedding model already loaded")
            return True
        
        self._status = ModelStatus.LOADING

        # ===== HF CPU 后端（sentence-transformers）=====
        if self._backend == "hf":
            self.log.info(f"Loading HF (sentence-transformers) embedding model from: {self._model_path}")
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                self._status = ModelStatus.ERROR
                self.log.error("sentence-transformers not installed; please `pip install sentence-transformers`")
                raise

            try:
                self._hf_model = SentenceTransformer(self._model_path)
                self._status = ModelStatus.READY
                self._start_time = time.time()
                self.log.info(f"HF embedding model loaded successfully (CPU): {self._model_path}")
                return True
            except Exception as e:
                self._status = ModelStatus.ERROR
                self.log.error(f"Failed to load HF embedding model: {e}")
                raise

        # ===== vLLM 后端（GPU）=====
        self.log.info(f"Loading embedding model from: {self._model_path}")
        
        # 设置 CUDA_VISIBLE_DEVICES 环境变量来指定 GPU
        if self._device and self._device.startswith("cuda:"):
            gpu_id = self._device.split(":")[1]
            import os
            os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id
            self.log.info(f"Set CUDA_VISIBLE_DEVICES={gpu_id} for device {self._device}")
        
        try:
            # 初始化 LLM（用于 embedding）
            # 注意：不同版本的 vLLM 参数不同，这里使用兼容性写法
            llm_kwargs = {
                "model": self._model_path,
                "gpu_memory_utilization": self._gpu_memory_utilization,
                "tensor_parallel_size": self._tensor_parallel_size,
                "max_model_len": self._max_model_len,
                "trust_remote_code": True,
                "dtype": "auto",
            }
            
            # 尝试使用 task 参数（vLLM >= 0.6.0）
            try:
                self._llm = LLM(task="embed", **llm_kwargs)
                self.log.info("Loaded embedding model with task='embed'")
            except TypeError as te:
                if "task" in str(te):
                    # 旧版本 vLLM 不支持 task 参数
                    self.log.info("vLLM version does not support 'task' parameter, loading without it")
                    self._llm = LLM(**llm_kwargs)
                else:
                    raise
            
            self._status = ModelStatus.READY
            self._start_time = time.time()
            self.log.info(f"Embedding model loaded successfully: {self._model_path}")
            return True
            
        except Exception as e:
            self._status = ModelStatus.ERROR
            self.log.error(f"Failed to load embedding model: {e}")
            raise
    
    def unload_model(self) -> bool:
        """
        卸载模型，释放GPU资源
        
        Returns:
            bool: 卸载成功返回True
        """
        # HF 后端
        if self._backend == "hf":
            if self._hf_model is None:
                self.log.info("No HF model to unload")
                return True
            try:
                self.log.info("Unloading HF embedding model...")
                del self._hf_model
                self._hf_model = None
                gc.collect()
                self._status = ModelStatus.UNINITIALIZED
                self.log.info("HF embedding model unloaded successfully")
                return True
            except Exception as e:
                self.log.error(f"Error unloading HF embedding model: {e}")
                return False

        # vLLM 后端
        if self._llm is None:
            self.log.info("No model to unload")
            return True
        
        try:
            self.log.info("Unloading embedding model...")
            
            # 删除模型对象
            del self._llm
            self._llm = None
            
            # 强制垃圾回收
            gc.collect()
            
            # 尝试清理CUDA缓存
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            except ImportError:
                pass
            
            self._status = ModelStatus.UNINITIALIZED
            self.log.info("Embedding model unloaded successfully")
            return True
            
        except Exception as e:
            self.log.error(f"Error unloading embedding model: {e}")
            return False
    
    # ==================== 统计相关方法 ====================
    
    def _increment_total_requests(self, count: int = 1) -> None:
        """增加总请求计数"""
        with self._stats_lock:
            self._total_requests += count
            self._active_requests += count
    
    def _increment_success(self, latency_ms: float, count: int = 1) -> None:
        """增加成功计数和延迟统计"""
        with self._stats_lock:
            self._successful_requests += count
            self._total_latency_ms += latency_ms
            self._active_requests -= count
    
    def _increment_failed(self, count: int = 1) -> None:
        """增加失败计数"""
        with self._stats_lock:
            self._failed_requests += count
            self._active_requests -= count
    
    def get_active_requests(self) -> int:
        """获取当前活跃请求数"""
        with self._stats_lock:
            return self._active_requests
    
    # ==================== 核心功能方法 ====================
    
    def encode(
        self,
        texts: Union[str, List[str]],
        dimensions: Optional[int] = None,
    ) -> EmbeddingResult:
        """
        文本向量化
        
        Args:
            texts: 单条文本或文本列表
            dimensions: 输出向量维度（可选，支持 Matryoshka Embeddings 的模型可用）
                        如 512, 768, 1024, 2048, 4096 等
            
        Returns:
            EmbeddingResult: 向量化结果
            
        Raises:
            RuntimeError: 模型未加载时抛出
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("Embedding model is not ready. Please load the model first.")
        
        # 确保输入是列表格式
        if isinstance(texts, str):
            texts = [texts]
        
        start_time = time.time()
        batch_size = len(texts)
        self._increment_total_requests(batch_size)

        # ===== HF CPU 后端 =====
        if self._backend == "hf":
            if self._hf_model is None:
                raise RuntimeError("HF embedding model is not initialized.")
            try:
                import uuid
                request_id = f"emb-{uuid.uuid4().hex[:16]}"

                # sentence-transformers encode
                embeddings_np = self._hf_model.encode(texts, convert_to_numpy=True)
                embeddings = [vec.tolist() for vec in embeddings_np]

                # 手动截断 / 保持维度
                if dimensions is not None and embeddings:
                    original_dim = len(embeddings[0])
                    if original_dim > dimensions:
                        self.log.debug(f"Truncating embeddings from {original_dim} to {dimensions} dimensions (HF)")
                        embeddings = [emb[:dimensions] for emb in embeddings]
                    elif original_dim < dimensions:
                        self.log.info(
                            f"Requested dimensions ({dimensions}) > model output ({original_dim}) (HF), using original"
                        )

                latency_ms = (time.time() - start_time) * 1000
                result = EmbeddingResult(
                    request_id=request_id,
                    embeddings=embeddings,
                    model=self._model_path.split("/")[-1],
                    usage={"prompt_tokens": 0, "total_tokens": 0},
                    latency_ms=latency_ms,
                )
                self._increment_success(latency_ms, batch_size)
                actual_dim = len(embeddings[0]) if embeddings else 0
                self.log.debug(f"HF Embedding completed: {batch_size} texts in {latency_ms:.2f}ms, dim={actual_dim}")
                return result
            except Exception as e:
                self._increment_failed(batch_size)
                self.log.error(f"HF Embedding failed: {e}")
                raise

        # ===== vLLM 后端 =====
        if self._llm is None:
            raise RuntimeError("Embedding model is not initialized.")
        
        try:
            import uuid
            request_id = f"emb-{uuid.uuid4().hex[:16]}"
            
            # 使用 vLLM 获取 embeddings（兼容不同版本）
            # 新版本使用 encode()，旧版本可能使用 embed()
            outputs = None
            
            # 构建 pooling_params（如果支持 dimensions）
            pooling_params = None
            if dimensions is not None:
                try:
                    from vllm import PoolingParams
                    pooling_params = PoolingParams(dimensions=dimensions)
                    self.log.debug(f"Using PoolingParams with dimensions={dimensions}")
                except ImportError:
                    self.log.debug("PoolingParams not available, dimensions will be truncated manually")
                except Exception as e:
                    self.log.debug(f"Failed to create PoolingParams: {e}")
            
            if hasattr(self._llm, 'encode'):
                try:
                    if pooling_params is not None:
                        outputs = self._llm.encode(texts, pooling_params=pooling_params)
                    else:
                        outputs = self._llm.encode(texts)
                except TypeError as te:
                    # 旧版本可能不支持 pooling_params
                    if "pooling_params" in str(te):
                        self.log.debug("encode() does not support pooling_params, calling without it")
                        outputs = self._llm.encode(texts)
                    else:
                        raise
                except Exception as e:
                    self.log.debug(f"encode() failed: {e}, trying embed()")
                    if hasattr(self._llm, 'embed'):
                        outputs = self._llm.embed(texts)
                    else:
                        raise
            elif hasattr(self._llm, 'embed'):
                outputs = self._llm.embed(texts)
            else:
                raise RuntimeError("LLM object has neither 'encode' nor 'embed' method")
            
            latency_ms = (time.time() - start_time) * 1000
            
            # 提取 embeddings（兼容不同版本的输出格式）
            embeddings = []
            total_tokens = 0
            
            for output in outputs:
                embedding_data = None
                
                # 方式1: PoolingRequestOutput 格式 (vLLM >= 0.6.0)
                if hasattr(output, 'outputs') and output.outputs is not None:
                    pooling_output = output.outputs
                    if hasattr(pooling_output, 'data'):
                        embedding_data = pooling_output.data
                    elif hasattr(pooling_output, 'embedding'):
                        embedding_data = pooling_output.embedding
                
                # 方式2: EmbeddingRequestOutput 格式
                elif hasattr(output, 'embedding'):
                    embedding_data = output.embedding
                
                # 方式3: 直接是 embedding 数据
                elif hasattr(output, 'tolist') or isinstance(output, (list, tuple)):
                    embedding_data = output
                
                # 转换为 list
                if embedding_data is not None:
                    if hasattr(embedding_data, 'tolist'):
                        embeddings.append(embedding_data.tolist())
                    elif hasattr(embedding_data, '__iter__') and not isinstance(embedding_data, str):
                        embeddings.append(list(embedding_data))
                    else:
                        embeddings.append(embedding_data)
                
                # 统计 token 数
                if hasattr(output, 'prompt_token_ids'):
                    total_tokens += len(output.prompt_token_ids)
            
            # 如果指定了 dimensions，且 PoolingParams 不可用或没生效，手动截断
            if dimensions is not None and embeddings:
                original_dim = len(embeddings[0])
                if original_dim > dimensions:
                    self.log.debug(f"Truncating embeddings from {original_dim} to {dimensions} dimensions")
                    embeddings = [emb[:dimensions] for emb in embeddings]
                elif original_dim < dimensions:
                    self.log.info(f"Requested dimensions ({dimensions}) > model output ({original_dim}), using original")
            
            result = EmbeddingResult(
                request_id=request_id,
                embeddings=embeddings,
                model=self._model_path.split("/")[-1],
                usage={
                    "prompt_tokens": total_tokens,
                    "total_tokens": total_tokens
                },
                latency_ms=latency_ms
            )
            
            actual_dim = len(embeddings[0]) if embeddings else 0
            self._increment_success(latency_ms, batch_size)
            self.log.debug(f"Embedding completed: {batch_size} texts in {latency_ms:.2f}ms, dim={actual_dim}")
            return result
            
        except Exception as e:
            self._increment_failed(batch_size)
            self.log.error(f"Embedding failed: {e}")
            raise
    
    def encode_single(self, text: str) -> List[float]:
        """
        单条文本向量化（简化接口）
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 向量
        """
        result = self.encode(text)
        if result.embeddings:
            return result.embeddings[0]
        return []
    
    def encode_batch(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        批量文本向量化（简化接口）
        
        Args:
            texts: 文本列表
            
        Returns:
            List[List[float]]: 向量列表
        """
        result = self.encode(texts)
        return result.embeddings
    
    # ==================== 健康检查与资源查询 ====================
    
    def ping(self) -> bool:
        """
        快速检查模型是否可用
        
        Returns:
            bool: 模型可用返回True
        """
        if not self._enable or self._status != ModelStatus.READY:
            return False
        if self._backend == "hf":
            return self._hf_model is not None
        return self._llm is not None
    
    def health_check(self) -> HealthStatus:
        """
        详细健康检查
        
        Returns:
            HealthStatus: 健康状态信息
        """
        is_healthy = self.ping()
        uptime = time.time() - self._start_time if self._start_time else 0
        
        with self._stats_lock:
            total = self._total_requests
            success = self._successful_requests
            failed = self._failed_requests
            avg_latency = self._total_latency_ms / success if success > 0 else 0
        
        return HealthStatus(
            is_healthy=is_healthy,
            model_status=self._status.value,
            model_name=self._model_path,
            uptime_seconds=uptime,
            total_requests=total,
            successful_requests=success,
            failed_requests=failed,
            avg_latency_ms=avg_latency
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict: 模型详细信息
        """
        return {
            "model_name": self._model_path.split("/")[-1] if self._model_path else "",
            "model_path": self._model_path,
            "device": self._device,
            "status": self._status.value,
            "enable": self._enable,
            "gpu_memory_utilization": self._gpu_memory_utilization,
            "tensor_parallel_size": self._tensor_parallel_size,
            "max_model_len": self._max_model_len,
            "uptime_seconds": time.time() - self._start_time if self._start_time else 0,
        }
    
    def get_gpu_resources(self) -> List[ResourceInfo]:
        """
        获取GPU资源信息
        
        Returns:
            List[ResourceInfo]: GPU资源列表
        """
        resources = []
        
        try:
            import torch
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                for i in range(device_count):
                    props = torch.cuda.get_device_properties(i)
                    
                    # 获取显存信息（单位：MB）
                    total_memory = props.total_memory / (1024 * 1024)
                    allocated = torch.cuda.memory_allocated(i) / (1024 * 1024)
                    reserved = torch.cuda.memory_reserved(i) / (1024 * 1024)
                    free = total_memory - reserved
                    
                    resources.append(ResourceInfo(
                        gpu_id=i,
                        gpu_name=props.name,
                        total_memory_mb=total_memory,
                        used_memory_mb=reserved,
                        free_memory_mb=free,
                        memory_utilization=reserved / total_memory if total_memory > 0 else 0,
                        gpu_utilization=0.0,  # 需要额外工具获取
                        temperature=0.0  # 需要额外工具获取
                    ))
        except ImportError:
            self.log.debug("PyTorch not available for GPU resource query")
        except Exception as e:
            self.log.error(f"Error getting GPU resources: {e}")
        
        return resources
    
    def is_enabled(self) -> bool:
        """检查模型是否启用"""
        return self._enable
    
    def get_embedding_dimension(self) -> int:
        """
        获取 embedding 维度
        
        Returns:
            int: embedding 向量维度
        """
        if self._llm is None:
            return 0
        
        try:
            # 通过一个简单的测试获取维度
            test_result = self.encode("test")
            if test_result.embeddings:
                return len(test_result.embeddings[0])
        except Exception:
            pass
        
        return 0
