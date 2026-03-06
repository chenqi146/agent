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
from domain.service.ops_service import OpsService

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
    def __init__(self,config:SysConfig,web_app:FastAPI):
        self.config = config
        self.app = web_app
        self._start_time = time.time()
        self._app_name = "pg-agent-application"
        self._version = self._get_version_from_config()
        # 初始化服务，并将配置和基础信息传入，供健康检查和指标使用
        self.ops_service = OpsService(
            config=self.config,
            app_name=self._app_name,
            version=self._version,
            start_time=self._start_time,
        )
        # 注册路由
        self._register_routes()

    def _get_version_from_config(self) -> str:
        """从配置中获取版本号"""
        try:
            system_config = self.config.get_system_config()
            return system_config.get('version', '1.0.0')
        except Exception:
            return '1.0.0'

    def _register_routes(self):
        """注册所有路由"""

        @self.app.post("/v1/agent/chat/ops/ping", response_model=ApiResponse)
        async def ping(request: EmptyRequest = EmptyRequest()):
            """
            简单探活接口 - 用于负载均衡器健康检查
            """
            revalue,result =  await self.ops_service.handle_ping()
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump())
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/chat/ops/health", response_model=ApiResponse)
        async def health_check(request: EmptyRequest = EmptyRequest()):
            """
            健康检查接口 - 详细的健康状态检查
            """
            revalue,result = await self.ops_service.handle_health_check()
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump())
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/chat/ops/metrics", response_model=ApiResponse)
        async def metrics(request: EmptyRequest = EmptyRequest()):
            """
            服务指标接口 - 获取完整的服务指标
            """
            revalue,result = await self.ops_service.handle_metrics()
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump())
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/chat/ops/version", response_model=ApiResponse)
        async def version(request: EmptyRequest = EmptyRequest()):
            """
            版本信息接口
            """
            revalue,result = await self.ops_service.handle_version()
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump())
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/chat/ops/process", response_model=ApiResponse)
        async def process_info(request: EmptyRequest = EmptyRequest()):
            """
            进程信息接口
            """
            revalue,result = await self.ops_service.handle_process_info()
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump())
            else:
                return fail(revalue, result)

        @self.app.post("/v1/agent/chat/ops/system", response_model=ApiResponse)
        async def system_info(request: EmptyRequest = EmptyRequest()):
            """
            系统信息接口
            """
            revalue,result = await self.ops_service.handle_system_info()
            if revalue == ErrorCode.SUCCESS:
                return ok(result.model_dump())
            else:
                return fail(revalue, result)
