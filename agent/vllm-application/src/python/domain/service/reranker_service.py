'''
Reranker服务,基于vLLM框架实现
提供文档重排序功能，常用于RAG场景

功能说明:
- 对 query-document 对进行相关性评分
- 批量重排序
- 支持 cross-encoder 模型（使用 score API）
- 支持基于 embedding 相似度的降级方案

并发支持说明:
- vLLM内部使用异步调度器，天然支持并发推理请求
- score() 方法可被多线程同时调用
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
import math
from typing import Dict, Any, List, Optional, Union, Tuple
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
class RerankResult:
    """重排序结果数据类"""
    request_id: str
    results: List[Dict[str, Any]]  # [{index, document, score}, ...]
    model: str = ""
    usage: Dict[str, int] = field(default_factory=lambda: {"prompt_tokens": 0, "total_tokens": 0})
    latency_ms: float = 0.0


@dataclass
class ScoreResult:
    """评分结果数据类"""
    request_id: str
    scores: List[float]  # 评分列表
    model: str = ""
    latency_ms: float = 0.0


@logger()
class RerankerService:
    """
    Reranker服务类 - 基于vLLM框架
    
    提供以下功能:
    - 模型加载与初始化
    - query-document 对评分
    - 批量文档重排序
    - 模型健康检测
    - GPU资源查询
    
    支持两种模式:
    - score: 使用 cross-encoder 模型（如 bge-reranker）
    - embed: 使用 embedding 模型计算相似度（降级方案）
    
    线程安全说明:
    - vLLM内部使用异步调度器，score()方法天然支持多线程并发调用
    - 统计信息使用锁保护，确保计数准确
    """
    
    def __init__(self, config: SysConfig, auto_load: bool = True):
        """
        初始化Reranker服务
        
        Args:
            config: 系统配置对象
            auto_load: 是否自动加载模型，默认True
        """
        try:
            self.reranker_config = config.get_reranker_config()
            self._llm: Optional[LLM] = None
            self._status = ModelStatus.UNINITIALIZED
            self._start_time: Optional[float] = None
            self._mode: str = "score"  # 'score' 或 'embed'
            
            # 统计信息（使用锁保护以确保并发安全）
            self._stats_lock = threading.Lock()
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._total_latency_ms = 0.0
            
            # 当前并发请求数（用于监控）
            self._active_requests = 0
            
            # 模型配置
            self._model_path = self.reranker_config.get('model', '')
            self._device = self.reranker_config.get('device', 'cuda:0')
            self._gpu_memory_utilization = self.reranker_config.get('gpu_memory_utilization', 0.5)
            self._tensor_parallel_size = self.reranker_config.get('tensor_parallel_size', 1)
            self._max_model_len = self.reranker_config.get('max_model_len', 8192)
            
            # 是否启用模型
            self._enable = self.reranker_config.get('enable', True)
            
            self.log.info(f"RerankerService initialized with model: {self._model_path}")
            
            # 注册进程退出清理函数
            self._cleanup_registered = False
            self._register_cleanup()
            
            # 根据 enable 配置决定是否加载模型
            if auto_load and self._enable:
                try:
                    self.load_model()
                except Exception as e:
                    self.log.error(f"Failed to load reranker model: {e}")
                    self._status = ModelStatus.ERROR
                    # 不抛出异常，允许服务继续运行，只是 reranker 功能不可用
            elif not self._enable:
                self.log.info(f"Reranker model disabled by config (enable=false)")
            
        except Exception as e:
            self._status = ModelStatus.ERROR
            self.log.error(f"RerankerService initialization failed: {e}")
            # 不抛出异常，允许服务继续运行
    
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
        加载Reranker模型
        
        Returns:
            bool: 加载成功返回True，失败返回False
        """
        if not self._enable:
            self.log.info("Reranker model loading skipped (enable=false)")
            return False
            
        if self._status == ModelStatus.READY:
            self.log.info("Reranker model already loaded")
            return True
        
        # 验证模型路径
        import os
        if self._model_path and not self._model_path.startswith(("http://", "https://")):
            if not os.path.exists(self._model_path):
                self.log.error(f"Model path does not exist: {self._model_path}")
                self._status = ModelStatus.ERROR
                return False
            config_file = os.path.join(self._model_path, "config.json")
            if not os.path.exists(config_file):
                self.log.error(f"config.json not found in model path: {self._model_path}")
                self._status = ModelStatus.ERROR
                return False
        
        self._status = ModelStatus.LOADING
        self.log.info(f"Loading reranker model from: {self._model_path}")
        
        # 设置 CUDA_VISIBLE_DEVICES 环境变量来指定 GPU
        if self._device and self._device.startswith("cuda:"):
            gpu_id = self._device.split(":")[1]
            import os
            os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id
            self.log.info(f"Set CUDA_VISIBLE_DEVICES={gpu_id} for device {self._device}")
        
        try:
            llm_kwargs = {
                "model": self._model_path,
                "gpu_memory_utilization": self._gpu_memory_utilization,
                "tensor_parallel_size": self._tensor_parallel_size,
                "max_model_len": self._max_model_len,
                "trust_remote_code": True,
                "dtype": "auto",
            }
            
            # 尝试不同的加载方式
            loaded = False
            
            # 方式1: 尝试使用 task="score"（cross-encoder 模式）
            try:
                self._llm = LLM(task="score", **llm_kwargs)
                self._mode = "score"
                loaded = True
                self.log.info("Loaded reranker model with task='score' (cross-encoder mode)")
            except TypeError as e:
                if "task" in str(e):
                    self.log.debug(f"task parameter not supported: {e}")
                else:
                    raise
            except Exception as e:
                self.log.debug(f"Failed to load with task='score': {e}")
            
            # 方式2: 尝试使用 task="embed"（embedding 模式）
            if not loaded:
                try:
                    self._llm = LLM(task="embed", **llm_kwargs)
                    self._mode = "embed"
                    loaded = True
                    self.log.info("Loaded reranker model with task='embed' (embedding mode)")
                except TypeError as e:
                    if "task" in str(e):
                        self.log.debug(f"task parameter not supported: {e}")
                    else:
                        raise
                except Exception as e:
                    self.log.debug(f"Failed to load with task='embed': {e}")
            
            # 方式3: 不使用 task 参数（兼容旧版本 vLLM）
            if not loaded:
                self._llm = LLM(**llm_kwargs)
                self._mode = "fallback"
                loaded = True
                self.log.info("Loaded reranker model without task parameter (fallback mode)")
            
            # 打印可用的方法（调试用）
            available_methods = [m for m in dir(self._llm) if not m.startswith('_') and callable(getattr(self._llm, m, None))]
            self.log.info(f"LLM available methods: {available_methods}")
            
            # 检测实际可用的评分方式
            if hasattr(self._llm, 'score'):
                self.log.info("score() method available - will use cross-encoder mode")
            if hasattr(self._llm, 'embed'):
                self.log.info("embed() method available - can use embedding mode")
            if hasattr(self._llm, 'encode'):
                self.log.info("encode() method available - can use encode mode")
            
            self._status = ModelStatus.READY
            self._start_time = time.time()
            self.log.info(f"Reranker model loaded successfully: {self._model_path}, mode={self._mode}")
            return True
            
        except Exception as e:
            self._status = ModelStatus.ERROR
            self.log.error(f"Failed to load reranker model: {e}")
            raise
    
    def unload_model(self) -> bool:
        """
        卸载模型，释放GPU资源
        
        Returns:
            bool: 卸载成功返回True
        """
        if self._llm is None:
            self.log.info("No model to unload")
            return True
        
        try:
            self.log.info("Unloading reranker model...")
            
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
            self.log.info("Reranker model unloaded successfully")
            return True
            
        except Exception as e:
            self.log.error(f"Error unloading reranker model: {e}")
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
    
    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec_a) != len(vec_b):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def score(
        self,
        query: str,
        documents: List[str],
    ) -> ScoreResult:
        """
        对 query-document 对进行评分
        
        Args:
            query: 查询文本
            documents: 文档列表
            
        Returns:
            ScoreResult: 评分结果
            
        Raises:
            RuntimeError: 模型未加载时抛出
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("Reranker model is not ready. Please load the model first.")
        
        if self._llm is None:
            raise RuntimeError("Reranker model is not initialized.")
        
        start_time = time.time()
        batch_size = len(documents)
        self._increment_total_requests(batch_size)
        
        try:
            import uuid
            request_id = f"rerank-{uuid.uuid4().hex[:16]}"
            
            scores = []
            
            # 总是先尝试 score API（不管 mode 设置如何）
            # 因为即使没有使用 task 参数加载，模型可能仍然支持 score()
            try:
                scores = self._score_with_cross_encoder(query, documents)
            except Exception as e:
                self.log.debug(f"Cross-encoder scoring failed: {e}, trying embedding mode")
                # 降级到 embedding 模式
                scores = self._score_with_embedding(query, documents)
            
            latency_ms = (time.time() - start_time) * 1000
            
            result = ScoreResult(
                request_id=request_id,
                scores=scores,
                model=self._model_path.split("/")[-1],
                latency_ms=latency_ms
            )
            
            self._increment_success(latency_ms, batch_size)
            self.log.debug(f"Scoring completed: {batch_size} documents in {latency_ms:.2f}ms")
            return result
            
        except Exception as e:
            self._increment_failed(batch_size)
            self.log.error(f"Scoring failed: {e}")
            raise
    
    def _score_with_cross_encoder(self, query: str, documents: List[str]) -> List[float]:
        """使用 cross-encoder 模式评分"""
        scores = []
        
        # 构建 text pairs
        text_pairs = [(query, doc) for doc in documents]
        
        # 尝试使用 score API
        if hasattr(self._llm, 'score'):
            outputs = self._llm.score(text_pairs)
            for output in outputs:
                if hasattr(output, 'outputs') and output.outputs is not None:
                    score_output = output.outputs
                    if hasattr(score_output, 'score'):
                        scores.append(float(score_output.score))
                    elif hasattr(score_output, 'data'):
                        scores.append(float(score_output.data))
                    else:
                        scores.append(0.0)
                elif hasattr(output, 'score'):
                    scores.append(float(output.score))
                else:
                    scores.append(0.0)
            
            if scores:
                return scores
        
        # 如果没有 score 方法，抛出异常让调用者处理
        raise RuntimeError("LLM object does not have 'score' method or score() returned empty results")
    
    def _score_with_embedding(self, query: str, documents: List[str]) -> List[float]:
        """使用 embedding 相似度评分"""
        scores = []
        
        # 获取 query 和 documents 的 embeddings
        all_texts = [query] + documents
        
        # 打印 LLM 对象可用的方法（调试用）
        available_methods = [m for m in dir(self._llm) if not m.startswith('_') and callable(getattr(self._llm, m, None))]
        self.log.debug(f"LLM available methods: {available_methods}")
        
        # 使用 embed 方法获取 embeddings（优先使用更具体的方法）
        embeddings = []
        outputs = None
        
        # 方法1: 优先使用 embed() 方法
        if hasattr(self._llm, 'embed'):
            try:
                outputs = self._llm.embed(all_texts)
                self.log.debug("Using LLM.embed() for embeddings")
            except Exception as e:
                self.log.debug(f"LLM.embed() failed: {e}")
                outputs = None
        
        # 方法2: 使用 encode() 方法，带 pooling_task 参数
        if outputs is None and hasattr(self._llm, 'encode'):
            try:
                outputs = self._llm.encode(all_texts, pooling_task="embed")
                self.log.debug("Using LLM.encode(pooling_task='embed') for embeddings")
            except TypeError as te:
                self.log.debug(f"LLM.encode(pooling_task='embed') TypeError: {te}")
                # 旧版本可能不支持 pooling_task 参数
                try:
                    outputs = self._llm.encode(all_texts)
                    self.log.debug("Using LLM.encode() without pooling_task for embeddings")
                except Exception as e:
                    self.log.debug(f"LLM.encode() failed: {e}")
                    outputs = None
            except Exception as e:
                self.log.debug(f"LLM.encode(pooling_task='embed') failed: {e}")
                outputs = None
        
        # 方法3: 最后尝试直接使用 score 方法（即使之前可能失败）
        if outputs is None and hasattr(self._llm, 'score'):
            self.log.debug("Trying direct score() as last resort")
            text_pairs = [(query, doc) for doc in documents]
            try:
                score_outputs = self._llm.score(text_pairs)
                for output in score_outputs:
                    if hasattr(output, 'outputs') and output.outputs is not None:
                        score_output = output.outputs
                        if hasattr(score_output, 'score'):
                            scores.append(float(score_output.score))
                        elif hasattr(score_output, 'data'):
                            scores.append(float(score_output.data))
                        else:
                            scores.append(0.0)
                    elif hasattr(output, 'score'):
                        scores.append(float(output.score))
                    else:
                        scores.append(0.0)
                if scores:
                    return scores
            except Exception as e:
                self.log.debug(f"Direct score() failed: {e}")
        
        if outputs is None:
            raise RuntimeError("Failed to get embeddings: LLM object has no working 'encode', 'embed', or 'score' method")
        
        for output in outputs:
            embedding_data = None
            
            if hasattr(output, 'outputs') and output.outputs is not None:
                pooling_output = output.outputs
                if hasattr(pooling_output, 'data'):
                    embedding_data = pooling_output.data
                elif hasattr(pooling_output, 'embedding'):
                    embedding_data = pooling_output.embedding
            elif hasattr(output, 'embedding'):
                embedding_data = output.embedding
            elif hasattr(output, 'tolist') or isinstance(output, (list, tuple)):
                embedding_data = output
            
            if embedding_data is not None:
                if hasattr(embedding_data, 'tolist'):
                    embeddings.append(embedding_data.tolist())
                elif hasattr(embedding_data, '__iter__') and not isinstance(embedding_data, str):
                    embeddings.append(list(embedding_data))
                else:
                    embeddings.append(embedding_data)
        
        if len(embeddings) < 2:
            return [0.0] * len(documents)
        
        # 计算 query 与每个 document 的余弦相似度
        query_embedding = embeddings[0]
        for i, doc_embedding in enumerate(embeddings[1:]):
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            scores.append(similarity)
        
        return scores
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None,
        return_documents: bool = True,
    ) -> RerankResult:
        """
        对文档进行重排序
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_n: 返回前N个结果（默认返回全部）
            return_documents: 是否返回文档内容
            
        Returns:
            RerankResult: 重排序结果
        """
        if self._status != ModelStatus.READY:
            raise RuntimeError("Reranker model is not ready. Please load the model first.")
        
        start_time = time.time()
        
        try:
            import uuid
            request_id = f"rerank-{uuid.uuid4().hex[:16]}"
            
            # 获取评分
            score_result = self.score(query, documents)
            
            # 构建结果列表
            results = []
            for i, (doc, score) in enumerate(zip(documents, score_result.scores)):
                result_item = {
                    "index": i,
                    "relevance_score": score,
                }
                if return_documents:
                    result_item["document"] = {"text": doc}
                results.append(result_item)
            
            # 按分数降序排序
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # 取前N个
            if top_n is not None and top_n > 0:
                results = results[:top_n]
            
            latency_ms = (time.time() - start_time) * 1000
            
            return RerankResult(
                request_id=request_id,
                results=results,
                model=self._model_path.split("/")[-1],
                latency_ms=latency_ms
            )
            
        except Exception as e:
            self.log.error(f"Rerank failed: {e}")
            raise
    
    # ==================== 健康检查与资源查询 ====================
    
    def ping(self) -> bool:
        """
        快速检查模型是否可用
        
        Returns:
            bool: 模型可用返回True
        """
        return self._status == ModelStatus.READY and self._llm is not None and self._enable
    
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
            "mode": self._mode,
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
                        gpu_utilization=0.0,
                        temperature=0.0
                    ))
        except ImportError:
            self.log.debug("PyTorch not available for GPU resource query")
        except Exception as e:
            self.log.error(f"Error getting GPU resources: {e}")
        
        return resources
    
    def is_enabled(self) -> bool:
        """检查模型是否启用"""
        return self._enable
    
    def get_mode(self) -> str:
        """获取当前模式（score 或 embed）"""
        return self._mode
