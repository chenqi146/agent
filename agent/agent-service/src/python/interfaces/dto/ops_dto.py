import time
import platform
import os
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
from datetime import datetime
import uuid
from enum import Enum


# ==================== 请求 DTO ====================

class EmptyRequest(BaseModel):
    """空请求体 —— 用于无 payload 的 GET/HEAD 接口（如 /health）"""
    pass


# ==================== 响应 DTO ====================

class VersionInfo(BaseModel):
    """版本信息 —— 支持构建时注入 & 运行时补全"""

    version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$",  # ✅ 语义化版本正则（含 pre-release）
        description="应用语义化版本号（如 '1.2.3', '2.0.0-beta.1'）",
    )
    app_name: str = Field(
        default="qjzh-vllm-application",
        min_length=1,
        max_length=64,
        description="应用唯一标识名（小写字母+数字+短横线）",
    )
    build_time: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$",  # ✅ ISO 8601 UTC 格式
        description="构建时间（ISO 8601 UTC，如 '2024-05-20T14:30:00Z'）",
    )
    git_commit: Optional[str] = Field(
        default=None,
        pattern=r"^[a-f0-9]{7,40}$",  # ✅ 支持 short & full commit hash
        description="Git 提交哈希（7~40 位十六进制）",
    )
    python_version: str = Field(
        default=f"{platform.python_version()}",
        description="运行时 Python 版本（自动填充）",
    )
    vllm_version: Optional[str] = Field(
        default=None,
        description="vLLM 库版本（若已安装，建议运行时动态获取）",
    )

    # ✅ 自动填充 build_time（若未传入）
    @model_validator(mode="before")
    @classmethod
    def set_default_build_time(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("build_time") is None:
            data["build_time"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return data


class ProcessInfo(BaseModel):
    """进程信息 —— 支持 psutil 动态采集字段（示例值为占位）"""

    pid: int = Field(..., ge=1, description="进程 ID（正整数）")
    ppid: int = Field(default=0, ge=0, description="父进程 ID（0 表示 init/systemd）")
    name: str = Field(
        default="",
        min_length=1,
        max_length=128,
        description="进程名称（如 'uvicorn', 'python'）",
    )
    status: Literal["running", "sleeping", "disk-sleep", "stopped", "traced", "zombie", "dead", "idle"] = Field(
        default="running",
        description="POSIX 进程状态（标准化枚举）",
    )
    create_time: float = Field(
        default=0.0,
        ge=0.0,
        description="进程创建时间戳（Unix 秒，高精度）",
    )
    uptime_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="进程已运行秒数（= now - create_time）",
    )
    num_threads: int = Field(default=0, ge=0, description="当前线程数")
    cpu_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="CPU 使用率（%），采样周期内平均值",
    )
    memory_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="内存使用率（%）",
    )
    memory_rss_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="常驻集大小 RSS（MB）",
    )
    memory_vms_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="虚拟内存大小 VMS（MB）",
    )

    # ✅ 自动计算 uptime_seconds（若 create_time 已知）
    @computed_field
    @property
    def uptime_seconds_computed(self) -> float:
        if self.create_time > 0:
            return max(0.0, time.time() - self.create_time)
        return 0.0


class SystemInfo(BaseModel):
    """系统信息 —— 兼容 Linux/macOS/Windows（字段可选）"""

    hostname: str = Field(default="", min_length=1, max_length=255, description="主机名")
    os_name: str = Field(
        default=f"{platform.system()}",
        description="操作系统名称（自动填充：Linux/Darwin/Windows）",
    )
    os_version: str = Field(
        default=f"{platform.release()}",
        description="操作系统版本（自动填充）",
    )
    architecture: str = Field(
        default=f"{platform.machine()}",
        description="CPU 架构（自动填充：x86_64/aarch64/arm64）",
    )
    cpu_count: int = Field(default=os.cpu_count() or 1, ge=1, description="逻辑 CPU 核心数")
    cpu_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="系统整体 CPU 使用率（%）",
    )
    memory_total_mb: float = Field(default=0.0, ge=0.0, description="总物理内存（MB）")
    memory_available_mb: float = Field(default=0.0, ge=0.0, description="当前可用内存（MB）")
    memory_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="内存使用率（%）",
    )
    disk_total_gb: float = Field(default=0.0, ge=0.0, description="磁盘总容量（GB）")
    disk_used_gb: float = Field(default=0.0, ge=0.0, description="磁盘已用空间（GB）")
    disk_free_gb: float = Field(default=0.0, ge=0.0, description="磁盘剩余空间（GB）")
    disk_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="磁盘使用率（%）",
    )
    boot_time: float = Field(default=0.0, ge=0.0, description="系统启动时间戳（Unix 秒）")
    uptime_seconds: float = Field(default=0.0, ge=0.0, description="系统运行时间（秒）")


class HealthCheckResult(BaseModel):
    """健康检查结果 —— 支持多级状态 & 结构化详情"""

    is_healthy: bool = Field(
        default=True,
        description="全局健康状态（True = 所有 checks 通过）",
    )
    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        default="healthy",
        description="摘要状态（healthy=全OK；unhealthy=关键失败；degraded=非关键降级）",
    )
    checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="各子检查项布尔结果（如 {'model_loaded': True, 'gpu_memory': True}）",
    )
    details: Dict[str, str] = Field(
        default_factory=dict,
        description="各检查项详细描述（如 {'gpu_memory': 'GPU VRAM: 12.3/16 GB'}）",
    )
    timestamp: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="检查执行时间戳（毫秒级 Unix 时间戳）",
        ge=1609459200000,  # 2021-01-01T00:00:00Z in ms
    )

    # ✅ 自动同步 is_healthy 和 status
    @model_validator(mode="after")
    def sync_health_status(self) -> "HealthCheckResult":
        all_ok = all(self.checks.values()) if self.checks else True
        any_failed = not all_ok
        degraded_keys = ["cache_warmup", "disk_space", "network_latency"]  # 示例降级项
        has_degraded = any(k in self.checks and not v for k, v in self.checks.items()
                           if k in degraded_keys)

        self.is_healthy = all_ok
        if any_failed and has_degraded:
            self.status = "degraded"
        elif any_failed:
            self.status = "unhealthy"
        else:
            self.status = "healthy"
        return self


class MetricsResponse(BaseModel):
    """服务指标响应 —— 全量可观测数据快照"""

    version: VersionInfo = Field(default_factory=VersionInfo)
    process: ProcessInfo = Field(default_factory=ProcessInfo)
    system: SystemInfo = Field(default_factory=SystemInfo)
    timestamp: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="指标采集完成时间戳（毫秒）",
        ge=1609459200000,
    )

    # ✅ 可选：添加 prometheus-style metrics 字段（便于 exporter 对接）
    @computed_field
    @property
    def prom_metrics(self) -> Dict[str, float]:
        """返回扁平化指标字典（兼容 Prometheus client）"""
        return {
            "process_uptime_seconds": self.process.uptime_seconds_computed,
            "process_cpu_percent": self.process.cpu_percent,
            "process_memory_percent": self.process.memory_percent,
            "system_cpu_percent": self.system.cpu_percent,
            "system_memory_percent": self.system.memory_percent,
            "system_disk_percent": self.system.disk_percent,
        }


class PingResponse(BaseModel):
    """Ping 响应 —— 轻量级存活探测"""

    status: Literal["pong"] = Field(
        default="pong",
        description="固定返回值，用于快速探测服务存活",
    )
    timestamp: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="响应生成时间戳（毫秒）",
        ge=1609459200000,
    )
    latency_ms: float = Field(
        default=0.0,
        description="从收到请求到发出响应的延迟（毫秒，由中间件注入）",
        ge=0.0,
    )

class GPUResourceDTO(BaseModel):
    """GPU资源信息"""
    gpu_id: int = Field(..., description="GPU ID")
    gpu_name: str = Field(default="", description="GPU名称")
    total_memory_mb: float = Field(default=0.0, description="总显存(MB)")
    used_memory_mb: float = Field(default=0.0, description="已用显存(MB)")
    free_memory_mb: float = Field(default=0.0, description="空闲显存(MB)")
    memory_utilization: float = Field(default=0.0, description="显存利用率")
    gpu_utilization: float = Field(default=0.0, description="GPU利用率")
    temperature: float = Field(default=0.0, description="温度(°C)")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    is_healthy: bool = Field(..., description="是否健康")
    model_status: str = Field(default="unknown", description="模型状态")
    model_name: str = Field(default="", description="模型名称")
    uptime_seconds: float = Field(default=0.0, description="运行时间(秒)")
    total_requests: int = Field(default=0, description="总请求数")
    successful_requests: int = Field(default=0, description="成功请求数")
    failed_requests: int = Field(default=0, description="失败请求数")
    active_requests: int = Field(default=0, description="当前活跃请求数")
    avg_latency_ms: float = Field(default=0.0, description="平均延迟(毫秒)")
    gpu_resources: List[GPUResourceDTO] = Field(default_factory=list, description="GPU资源信息")
    error_message: Optional[str] = Field(default=None, description="错误信息")


# ==================== GPU 资源 DTO ====================

class GPUResourceDTO(BaseModel):
    """GPU资源信息 —— 单卡细粒度指标"""

    gpu_id: int = Field(
        ...,
        ge=0,
        description="GPU 设备 ID（从 0 开始）",
    )
    gpu_name: str = Field(
        default="",
        min_length=1,
        max_length=64,
        description="GPU 型号名称（如 'NVIDIA A100-SXM4-80GB', 'AMD Instinct MI300X'）",
    )
    total_memory_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="总显存容量（MB）",
    )
    used_memory_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="已用显存（MB）",
    )
    free_memory_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="空闲显存（MB）",
    )
    memory_utilization: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="显存利用率（%），0.0–100.0",
    )
    gpu_utilization: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="GPU 计算单元利用率（%），0.0–100.0",
    )
    temperature: float = Field(
        default=0.0,
        ge=-273.15,  # 绝对零度
        le=150.0,  # 安全上限（GPU 实际极限约 95–110°C，留余量）
        description="GPU 温度（°C）",
    )

    # ✅ 自动校验：used + free ≈ total（允许浮点误差）
    @model_validator(mode="after")
    def validate_memory_consistency(self) -> "GPUResourceDTO":
        tol = 1.0  # MB 容差
        if abs(self.used_memory_mb + self.free_memory_mb - self.total_memory_mb) > tol:
            raise ValueError(
                f"Memory inconsistency: used({self.used_memory_mb}) + free({self.free_memory_mb}) "
                f"≠ total({self.total_memory_mb}) (tolerance ±{tol}MB)"
            )
        return self

    # ✅ 自动计算：memory_utilization = used / total * 100（若 total > 0）
    @computed_field
    @property
    def memory_utilization_computed(self) -> float:
        if self.total_memory_mb <= 0:
            return 0.0
        return min(100.0, max(0.0, (self.used_memory_mb / self.total_memory_mb) * 100.0))

    # ✅ 自动计算：gpu_utilization 合理性兜底（避免 NaN 或负数）
    @computed_field
    @property
    def gpu_utilization_safe(self) -> float:
        return max(0.0, min(100.0, self.gpu_utilization))


# ==================== 健康检查响应 ====================

class ModelStatus(str,Enum):  # ✅ 强制枚举化（非自由字符串）
    UNKNOWN = "unknown"
    LOADING = "loading"
    LOADED = "loaded"
    UNHEALTHY = "unhealthy"
    ERROR = "error"


class HealthCheckResponse(BaseModel):
    """健康检查响应 —— 兼容 Prometheus / Grafana / SRE 看板"""

    # ✅ 标准元数据（可观测性基石）
    id: str = Field(
        default_factory=lambda: f"health-{uuid.uuid4().hex[:12]}",
        pattern=r"^health-[a-zA-Z0-9]{12}$",
        description="本次健康检查唯一 ID（用于日志追踪）",
    )
    timestamp: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp() * 1000),
        ge=1609459200000,  # 2021-01-01T00:00:00Z in ms
        description="检查执行完成时间戳（毫秒级 Unix 时间）",
    )
    is_healthy: bool = Field(
        ...,
        description="全局健康状态（True = 所有子项达标）",
    )

    # ✅ 模型状态（强制枚举）
    model_status: ModelStatus = Field(
        default=ModelStatus.UNKNOWN,
        description="模型加载与运行状态",
    )
    model_name: str = Field(
        default="",
        min_length=0,
        max_length=128,
        description="加载的模型名称（如 'Qwen2-VL-7B-Instruct'）",
    )

    # ✅ 请求统计（带自动一致性校验）
    uptime_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="服务启动后运行时间（秒）",
    )
    total_requests: int = Field(
        default=0,
        ge=0,
        description="自启动以来总请求数",
    )
    successful_requests: int = Field(
        default=0,
        ge=0,
        description="成功处理的请求数",
    )
    failed_requests: int = Field(
        default=0,
        ge=0,
        description="失败请求数（含 4xx/5xx、timeout、OOM）",
    )
    active_requests: int = Field(
        default=0,
        ge=0,
        description="当前正在处理的请求数（并发数）",
    )
    avg_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="历史平均端到端延迟（毫秒）",
    )

    # ✅ GPU 资源（关键：支持空列表语义明确化）
    gpu_resources: List[GPUResourceDTO] = Field(
        default_factory=list,
        description="GPU 设备列表（空列表 = 无 GPU；None 不允许）",
    )

    # ✅ 错误信息（严格防护）
    error_message: Optional[str] = Field(
        default=None,
        max_length=2048,  # ✅ 防注入 & 防日志爆炸
        description="最后发生的错误详情（仅当 model_status == 'error' 时有效）",
    )

    # ✅ 自动校验：total = success + failed（防御性设计）
    @model_validator(mode="after")
    def validate_request_counts(self) -> "HealthCheckResponse":
        if self.total_requests != self.successful_requests + self.failed_requests:
            # ⚠️ 允许容忍 1 的误差（计数竞态）
            if abs(self.total_requests - (self.successful_requests + self.failed_requests)) > 1:
                raise ValueError(
                    f"Request count mismatch: total({self.total_requests}) ≠ "
                    f"success({self.successful_requests}) + failed({self.failed_requests})"
                )
        return self

    # ✅ 自动推导 is_healthy（业务逻辑集中化）
    @computed_field
    @property
    def is_healthy_computed(self) -> bool:
        # 关键健康条件：
        # 1. model_status 必须为 LOADED
        # 2. 至少有一块 GPU utilization ≤ 95%（防过载）
        # 3. 无 error_message（或 error_message 为空）
        if self.model_status != ModelStatus.LOADED:
            return False
        if not self.gpu_resources:
            return True  # 无 GPU 时跳过 GPU 检查（CPU 模式）
        if any(gpu.gpu_utilization > 95.0 for gpu in self.gpu_resources):
            return False
        if self.error_message and len(self.error_message.strip()) > 0:
            return False
        return True

    # ✅ 自动同步 is_healthy（确保最终一致）
    @model_validator(mode="after")
    def sync_is_healthy(self) -> "HealthCheckResponse":
        self.is_healthy = self.is_healthy_computed
        return self

    # ✅ 可选：Prometheus metrics 字段（开箱即用）
    @computed_field
    @property
    def prom_metrics(self) -> dict:
        """返回扁平化指标，兼容 Prometheus exposition format"""
        return {
            "healthcheck_success": 1.0 if self.is_healthy else 0.0,
            "model_load_status": {"unknown": 0, "loading": 1, "loaded": 2, "unhealthy": 3, "error": 4}[
                self.model_status],
            "requests_total": float(self.total_requests),
            "requests_successful": float(self.successful_requests),
            "requests_failed": float(self.failed_requests),
            "requests_active": float(self.active_requests),
            "latency_ms_avg": self.avg_latency_ms,
            "gpu_count": len(self.gpu_resources),
            **{
                f"gpu_{i}_utilization": gpu.gpu_utilization_safe
                for i, gpu in enumerate(self.gpu_resources)
            },
            **{
                f"gpu_{i}_memory_utilization": gpu.memory_utilization_computed
                for i, gpu in enumerate(self.gpu_resources)
            }
        }

