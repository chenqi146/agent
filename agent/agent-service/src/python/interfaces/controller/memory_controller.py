import time
import asyncio

from fastapi import FastAPI, Depends

from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

from interfaces.controller.base_controller import BaseController
from interfaces.deps.user_context import UserContext, get_validated_user_context
from interfaces.dto.response_dto import ApiResponse, ok, fail
from interfaces.dto.memory_dto import (
    MemoryConfigApiRequest,
    MemoryContentSearchApiRequest,
    MemoryContentDeleteApiRequest,
    MemoryContentClearApiRequest,
)
from domain.service.memory_service import MemoryService


@logger()
class MemoryController(BaseController):
    """
    记忆控制器：
    - 获取 / 保存记忆配置
    - 管理记忆内容列表（基于 Elasticsearch）
    """

    def __init__(self, config: SysConfig, web_app: FastAPI, memory_service: MemoryService):
        self.config = config
        self.app = web_app
        self._start_time = time.time()
        self._app_name = "pg-agent-application"
        self._version = self._get_version_from_config()

        self.memory_service = memory_service

        self._register_routes()

    def _get_version_from_config(self) -> str:
        try:
            system_config = self.config.get_system_config()
            return system_config.get("version", "1.0.0")
        except Exception:
            return "1.0.0"

    def _register_routes(self):
        @self.app.get("/v1/agent/memory", response_model=ApiResponse)
        async def get_memory_config(
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """
            获取当前智能体（用户）对应的记忆配置。
            """
            try:
                agent_id = int(user_ctx.user_id)
                err, cfg = await asyncio.to_thread(
                    self.memory_service.get_memory_config, agent_id
                )
                if err == ErrorCode.SUCCESS:
                    data = cfg.model_dump(by_alias=True) if cfg is not None else None
                    return ok(data)
                return fail(err, None)
            except Exception as e:
                self.log.error("get_memory_config error: %s", e, exc_info=True)
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/memory", response_model=ApiResponse)
        async def save_memory_config(
            request: MemoryConfigApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """
            保存记忆配置。
            """
            try:
                agent_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.memory_service.save_memory_config, agent_id, request.data
                )
                if err == ErrorCode.SUCCESS:
                    cfg = result
                    data = cfg.model_dump(by_alias=True) if cfg is not None else None
                    return ok(data)
                msg = result if isinstance(result, str) else None
                return fail(err, msg)
            except Exception as e:
                self.log.error("save_memory_config error: %s", e, exc_info=True)
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/memory/content/search", response_model=ApiResponse)
        async def search_memory_content(
            request: MemoryContentSearchApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                agent_id = int(user_ctx.user_id)
                err, data = await asyncio.to_thread(
                    self.memory_service.search_memory_content, agent_id, request.data
                )
                if err == ErrorCode.SUCCESS:
                    return ok(data)
                return fail(err)
            except Exception as e:
                self.log.error("search_memory_content error: %s", e, exc_info=True)
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/memory/content/delete", response_model=ApiResponse)
        async def delete_memory_content(
            request: MemoryContentDeleteApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                agent_id = int(user_ctx.user_id)
                err, _ = await asyncio.to_thread(
                    self.memory_service.delete_memory_content, agent_id, request.data.ids
                )
                if err == ErrorCode.SUCCESS:
                    return ok()
                return fail(err)
            except Exception as e:
                self.log.error("delete_memory_content error: %s", e, exc_info=True)
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/memory/content/clear", response_model=ApiResponse)
        async def clear_memory_content(
            request: MemoryContentClearApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                agent_id = int(user_ctx.user_id)
                err, _ = await asyncio.to_thread(
                    self.memory_service.clear_memory_content, agent_id
                )
                if err == ErrorCode.SUCCESS:
                    return ok()
                return fail(err)
            except Exception as e:
                self.log.error("clear_memory_content error: %s", e, exc_info=True)
                return fail(ErrorCode.SYSTEM_ERROR, str(e))
