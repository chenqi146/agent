'''
Ops控制器 - 提供系统运维、进程健康检测、服务指标查询接口
负责处理系统管理请求和响应
所有接口统一使用 POST 方法
'''
import os
import sys
import time
import platform
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

from interfaces.dto.ops_dto import (
    EmptyRequest, VersionInfo, ProcessInfo, SystemInfo,
    HealthCheckResult, MetricsResponse, PingResponse
)
from interfaces.dto.response_dto import ApiResponse, ok, fail


@logger()
class OpsController:
    """
    Ops 控制器 - 系统运维接口
    
    所有接口统一使用 POST 方法:
    - POST /ops/ping          - 简单探活
    - POST /ops/health        - 健康检查
    - POST /ops/metrics       - 服务指标
    - POST /ops/version       - 版本信息
    - POST /ops/process       - 进程信息
    - POST /ops/system        - 系统信息
    """
    
    def __init__(self, config: SysConfig, web_app: FastAPI):
        """
        初始化 Ops 控制器
        
        Args:
            config: 系统配置
            web_app: FastAPI 应用实例
        """
        self.config = config
        self.app = web_app
        self._start_time = time.time()
        self._app_name = "qjzh-vllm-application"
        self._version = self._get_version_from_config()
        
        # 注册路由
        self._register_routes()
        
        self.log.info("OpsController initialized")
    
    def _get_version_from_config(self) -> str:
        """从配置中获取版本号"""
        try:
            system_config = self.config.get_system_config()
            return system_config.get('version', '1.0.0')
        except Exception:
            return '1.0.0'
    
    def _register_routes(self):
        """注册所有路由"""
        
        @self.app.post("/ops/ping", response_model=ApiResponse)
        async def ping(request: EmptyRequest = EmptyRequest()):
            """
            简单探活接口 - 用于负载均衡器健康检查
            """
            return await self._handle_ping()
        
        @self.app.post("/ops/health", response_model=ApiResponse)
        async def health_check(request: EmptyRequest = EmptyRequest()):
            """
            健康检查接口 - 详细的健康状态检查
            """
            return await self._handle_health_check()
        
        @self.app.post("/ops/metrics", response_model=ApiResponse)
        async def metrics(request: EmptyRequest = EmptyRequest()):
            """
            服务指标接口 - 获取完整的服务指标
            """
            return await self._handle_metrics()
        
        @self.app.post("/ops/version", response_model=ApiResponse)
        async def version(request: EmptyRequest = EmptyRequest()):
            """
            版本信息接口
            """
            return await self._handle_version()
        
        @self.app.post("/ops/process", response_model=ApiResponse)
        async def process_info(request: EmptyRequest = EmptyRequest()):
            """
            进程信息接口
            """
            return await self._handle_process_info()
        
        @self.app.post("/ops/system", response_model=ApiResponse)
        async def system_info(request: EmptyRequest = EmptyRequest()):
            """
            系统信息接口
            """
            return await self._handle_system_info()
    
    # ==================== 请求处理方法 ====================
    
    async def _handle_ping(self) -> ApiResponse:
        """
        处理 ping 请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            response = PingResponse(status="pong")
            return ok(response.model_dump(), "服务正常")
        except Exception as e:
            self.log.error(f"Ping error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_health_check(self) -> ApiResponse:
        """
        处理健康检查请求
        
        Returns:
            ApiResponse: 统一响应
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
                return ok(response.model_dump(), "服务健康")
            else:
                return fail(ErrorCode.SERVICE_UNAVAILABLE, "服务异常", response.model_dump())
                
        except Exception as e:
            self.log.error(f"Health check error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_metrics(self) -> ApiResponse:
        """
        处理指标请求 - 返回完整的服务指标
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            version_info = self._get_version_info()
            process_info = self._get_process_info()
            system_info = self._get_system_info()
            
            response = MetricsResponse(
                version=version_info,
                process=process_info,
                system=system_info
            )
            
            return ok(response.model_dump())
            
        except Exception as e:
            self.log.error(f"Metrics error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_version(self) -> ApiResponse:
        """
        处理版本信息请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            version_info = self._get_version_info()
            return ok(version_info.model_dump())
        except Exception as e:
            self.log.error(f"Version error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_process_info(self) -> ApiResponse:
        """
        处理进程信息请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            process_info = self._get_process_info()
            return ok(process_info.model_dump())
        except Exception as e:
            self.log.error(f"Process info error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
    async def _handle_system_info(self) -> ApiResponse:
        """
        处理系统信息请求
        
        Returns:
            ApiResponse: 统一响应
        """
        try:
            system_info = self._get_system_info()
            return ok(system_info.model_dump())
        except Exception as e:
            self.log.error(f"System info error: {e}")
            return fail(ErrorCode.INTERNAL_ERROR, str(e))
    
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
