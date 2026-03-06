from dataclasses import dataclass, field
from typing import List, Optional

from infrastructure.llm.llm_model_status import ModelStatus


@dataclass
class InferenceResult:
    """推理结果数据类"""
    request_id: str                          # 请求ID
    prompt: str                              # 输入提示词
    generated_text: str                      # 生成的文本
    finish_reason: str                       # 完成原因
    prompt_tokens: int = 0                   # 输入token数
    completion_tokens: int = 0               # 输出token数
    total_tokens: int = 0                    # 总token数
    latency_ms: float = 0.0                  # 推理延迟(毫秒)
    tokens_per_second: float = 0.0           # 每秒生成token数


@dataclass
class ResourceInfo:
    """资源信息数据类"""
    gpu_id: int                              # GPU ID
    gpu_name: str                            # GPU名称
    total_memory_mb: float                   # 总显存(MB)
    used_memory_mb: float                    # 已用显存(MB)
    free_memory_mb: float                    # 空闲显存(MB)
    memory_utilization: float                # 显存利用率(0-1)
    gpu_utilization: float = 0.0             # GPU计算利用率(0-1)
    temperature: float = 0.0                 # GPU温度(摄氏度)


@dataclass
class HealthStatus:
    """健康状态数据类"""
    is_healthy: bool                         # 是否健康
    model_status: ModelStatus                # 模型状态
    model_name: str                          # 模型名称
    uptime_seconds: float                    # 运行时间(秒)
    total_requests: int                      # 总请求数
    successful_requests: int                 # 成功请求数
    failed_requests: int                     # 失败请求数
    avg_latency_ms: float                    # 平均延迟(毫秒)
    error_message: Optional[str] = None      # 错误信息
    gpu_resources: List[ResourceInfo] = field(default_factory=list)  # GPU资源信息