'''
Ops 请求/响应 DTO 定义
系统运维相关接口的数据传输对象
'''
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time


# ==================== 请求 DTO ====================

class EmptyRequest(BaseModel):
    """空请求体"""
    pass


# ==================== 响应 DTO ====================

class VersionInfo(BaseModel):
    """版本信息"""
    version: str = Field(default="1.0.0", description="应用版本号")
    app_name: str = Field(default="qjzh-vllm-application", description="应用名称")
    build_time: Optional[str] = Field(default=None, description="构建时间")
    git_commit: Optional[str] = Field(default=None, description="Git提交哈希")
    python_version: str = Field(default="", description="Python版本")
    vllm_version: Optional[str] = Field(default=None, description="vLLM版本")


class ProcessInfo(BaseModel):
    """进程信息"""
    pid: int = Field(..., description="进程ID")
    ppid: int = Field(default=0, description="父进程ID")
    name: str = Field(default="", description="进程名称")
    status: str = Field(default="running", description="进程状态")
    create_time: float = Field(default=0.0, description="进程创建时间戳")
    uptime_seconds: float = Field(default=0.0, description="运行时间(秒)")
    num_threads: int = Field(default=0, description="线程数")
    cpu_percent: float = Field(default=0.0, description="CPU使用率(%)")
    memory_percent: float = Field(default=0.0, description="内存使用率(%)")
    memory_rss_mb: float = Field(default=0.0, description="物理内存使用(MB)")
    memory_vms_mb: float = Field(default=0.0, description="虚拟内存使用(MB)")


class SystemInfo(BaseModel):
    """系统信息"""
    hostname: str = Field(default="", description="主机名")
    os_name: str = Field(default="", description="操作系统名称")
    os_version: str = Field(default="", description="操作系统版本")
    architecture: str = Field(default="", description="CPU架构")
    cpu_count: int = Field(default=0, description="CPU核心数")
    cpu_percent: float = Field(default=0.0, description="系统CPU使用率(%)")
    memory_total_mb: float = Field(default=0.0, description="总内存(MB)")
    memory_available_mb: float = Field(default=0.0, description="可用内存(MB)")
    memory_percent: float = Field(default=0.0, description="内存使用率(%)")
    disk_total_gb: float = Field(default=0.0, description="磁盘总容量(GB)")
    disk_used_gb: float = Field(default=0.0, description="磁盘已用(GB)")
    disk_free_gb: float = Field(default=0.0, description="磁盘可用(GB)")
    disk_percent: float = Field(default=0.0, description="磁盘使用率(%)")
    boot_time: float = Field(default=0.0, description="系统启动时间戳")
    uptime_seconds: float = Field(default=0.0, description="系统运行时间(秒)")


class HealthCheckResult(BaseModel):
    """健康检查结果"""
    is_healthy: bool = Field(default=True, description="是否健康")
    status: str = Field(default="healthy", description="健康状态: healthy/unhealthy/degraded")
    checks: Dict[str, bool] = Field(default_factory=dict, description="各项检查结果")
    details: Dict[str, str] = Field(default_factory=dict, description="检查详情")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="检查时间戳")


class MetricsResponse(BaseModel):
    """服务指标响应"""
    version: VersionInfo = Field(default_factory=VersionInfo, description="版本信息")
    process: ProcessInfo = Field(default_factory=ProcessInfo, description="进程信息")
    system: SystemInfo = Field(default_factory=SystemInfo, description="系统信息")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="采集时间戳")


class PingResponse(BaseModel):
    """Ping响应"""
    status: str = Field(default="pong", description="响应状态")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="时间戳")

