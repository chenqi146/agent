
import platform
import os
import time
from typing import Dict, Any, Optional, Tuple
from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from interfaces.dto.ops_dto import (
    EmptyRequest, VersionInfo, ProcessInfo, SystemInfo,
    HealthCheckResult, MetricsResponse, PingResponse
)

@logger()
class OpsService:
    def __init__(self, config: Optional[SysConfig] = None,
                 app_name: str = "pg-agent-application",
                 version: str = "1.0.0",
                 start_time: Optional[float] = None):
        """
        :param config: 系统配置，用于健康检查等
        :param app_name: 应用名称
        :param version: 应用版本号
        :param start_time: 应用启动时间，用于计算运行时长
        """
        self.config: Optional[SysConfig] = config
        self._app_name: str = app_name
        self._version: str = version
        # 如果上层没有传入，则在此刻记录启动时间
        self._start_time: float = start_time if start_time is not None else time.time()
        self.log.info(
            f"OpsService initialized, app_name={self._app_name}, "
            f"version={self._version}, has_config={self.config is not None}"
        )

    async def handle_ping(self) -> Tuple[ErrorCode,PingResponse]:
        """
        处理 ping 请求

        Returns:
            ApiResponse: 统一响应
        """
        try:
            response = PingResponse(status="pong")
            return ErrorCode.SUCCESS,response
        except Exception as e:
            self.log.error(f"Ping error: {e}")
            return ErrorCode.INTERNAL_ERROR, str(e)

    async def handle_health_check(self) -> Tuple[ErrorCode,HealthCheckResult]:
        """
        处理健康检查请求
        """
        try:
            checks = {}
            details = {}
            is_healthy = True

            # 检查1: 进程是否正常运行
            checks['process'] = True
            details['process'] = "进程运行正常"

            # 检查2: 内存使用是否正常（低于90%）
            try:
                import psutil
                memory = psutil.virtual_memory()
                memory_ok = memory.percent < 90
                checks['memory'] = memory_ok
                details['memory'] = f"内存使用率: {memory.percent:.1f}%"
                if not memory_ok:
                    is_healthy = False
            except ImportError:
                checks['memory'] = True
                details['memory'] = "psutil未安装，跳过检查"

            # 检查3: 磁盘空间是否正常（低于95%）
            try:
                import psutil
                disk = psutil.disk_usage('/')
                disk_ok = disk.percent < 95
                checks['disk'] = disk_ok
                details['disk'] = f"磁盘使用率: {disk.percent:.1f}%"
                if not disk_ok:
                    is_healthy = False
            except ImportError:
                checks['disk'] = True
                details['disk'] = "psutil未安装，跳过检查"
            except Exception as e:
                checks['disk'] = True
                details['disk'] = f"检查跳过: {e}"

            # 检查4: 配置是否加载
            config_ok = self.config is not None
            checks['config'] = config_ok
            details['config'] = "配置已加载" if config_ok else "配置未加载"
            if not config_ok:
                is_healthy = False

            status = "healthy" if is_healthy else "unhealthy"

            response = HealthCheckResult(
                is_healthy=is_healthy,
                status=status,
                checks=checks,
                details=details
            )

            if is_healthy:
                return ErrorCode.SUCCESS, response
            else:
                return ErrorCode.INTERNAL_ERROR, response

        except Exception as e:
            self.log.error(f"Health check error: {e}")
            return ErrorCode.EXCEPTION_ERROR, str(e)

    async def handle_metrics(self) -> Tuple[ErrorCode,MetricsResponse]:
        """
        处理指标请求 - 返回完整的服务指标

        Returns:
            ApiResponse: 统一响应
        """
        try:
            version_info = self._get_version_info()
            process_info = self._get_process_info()
            system_info = self._get_system_info()

            return ErrorCode.SUCCESS, MetricsResponse(
                version=version_info,
                process=process_info,
                system=system_info
            )

        except Exception as e:
            self.log.error(f"Metrics error: {e}")
            return ErrorCode.EXCEPTION_ERROR, str(e)

    async def handle_version(self) -> Tuple[ErrorCode,VersionInfo]:
        """
        处理版本信息请求

        Returns:
            ApiResponse: 统一响应
        """
        try:
            version_info = self._get_version_info()
            return ErrorCode.SUCCESS, version_info
        except Exception as e:
            self.log.error(f"Version error: {e}")
            return ErrorCode.EXCEPTION_ERROR, str(e)

    async def handle_process_info(self) -> Tuple[ErrorCode,ProcessInfo]:
        """
        处理进程信息请求

        Returns:
            ApiResponse: 统一响应
        """
        try:
            process_info = self._get_process_info()
            return ErrorCode.SUCCESS, process_info
        except Exception as e:
            self.log.error(f"Process info error: {e}")
            return ErrorCode.EXCEPTION_ERROR, str(e)

    async def handle_system_info(self) -> Tuple[ErrorCode,SystemInfo]:
        """
        处理系统信息请求

        Returns:
            ApiResponse: 统一响应
        """
        try:
            system_info = self._get_system_info()
            return ErrorCode.SUCCESS, system_info
        except Exception as e:
            self.log.error(f"System info error: {e}")
            return ErrorCode.EXCEPTION_ERROR, str(e)

    # ==================== 信息采集方法 ====================

    def _get_version_info(self) -> VersionInfo:
        """
        获取版本信息

        Returns:
            VersionInfo: 版本信息对象
        """
        vllm_version = None
        try:
            import vllm
            vllm_version = getattr(vllm, '__version__', None)
        except ImportError:
            pass

        return VersionInfo(
            version=self._version,
            app_name=self._app_name,
            build_time=None,
            git_commit=None,
            python_version=platform.python_version(),
            vllm_version=vllm_version
        )

    def _get_process_info(self) -> ProcessInfo:
        """
        获取当前进程信息

        Returns:
            ProcessInfo: 进程信息对象
        """
        pid = os.getpid()
        uptime = time.time() - self._start_time

        # 基础信息
        info = ProcessInfo(
            pid=pid,
            ppid=os.getppid(),
            name="python",
            status="running",
            create_time=self._start_time,
            uptime_seconds=uptime
        )

        # 尝试使用 psutil 获取详细信息
        try:
            import psutil
            process = psutil.Process(pid)

            info.name = process.name()
            info.status = process.status()
            info.create_time = process.create_time()
            info.uptime_seconds = time.time() - process.create_time()
            info.num_threads = process.num_threads()
            info.cpu_percent = process.cpu_percent(interval=0.1)
            info.memory_percent = process.memory_percent()

            mem_info = process.memory_info()
            info.memory_rss_mb = mem_info.rss / (1024 * 1024)
            info.memory_vms_mb = mem_info.vms / (1024 * 1024)

        except ImportError:
            self.log.debug("psutil not available, using basic process info")
        except Exception as e:
            self.log.warning(f"Failed to get detailed process info: {e}")

        return info

    def _get_system_info(self) -> SystemInfo:
        """
        获取系统信息

        Returns:
            SystemInfo: 系统信息对象
        """
        info = SystemInfo(
            hostname=platform.node(),
            os_name=platform.system(),
            os_version=platform.release(),
            architecture=platform.machine(),
            cpu_count=os.cpu_count() or 0
        )

        # 尝试使用 psutil 获取详细信息
        try:
            import psutil

            # CPU
            info.cpu_percent = psutil.cpu_percent(interval=0.1)

            # 内存
            memory = psutil.virtual_memory()
            info.memory_total_mb = memory.total / (1024 * 1024)
            info.memory_available_mb = memory.available / (1024 * 1024)
            info.memory_percent = memory.percent

            # 磁盘
            try:
                disk = psutil.disk_usage('/')
                info.disk_total_gb = disk.total / (1024 * 1024 * 1024)
                info.disk_used_gb = disk.used / (1024 * 1024 * 1024)
                info.disk_free_gb = disk.free / (1024 * 1024 * 1024)
                info.disk_percent = disk.percent
            except Exception:
                pass

            # 启动时间
            info.boot_time = psutil.boot_time()
            info.uptime_seconds = time.time() - psutil.boot_time()

        except ImportError:
            self.log.debug("psutil not available, using basic system info")
        except Exception as e:
            self.log.warning(f"Failed to get detailed system info: {e}")

        return info