import asyncio

from fastapi import FastAPI, Depends

from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger
from infrastructure.config.sys_config import SysConfig
from interfaces.controller.base_controller import BaseController
from interfaces.deps.user_context import UserContext, get_validated_user_context
from interfaces.dto.role_dto import (
    ApplicationRoleListApiRequest,
    ApplicationRoleSaveApiRequest,
    ApplicationRoleIdApiRequest,
    ApplicationRoleToggleStatusApiRequest,
    ApplicationRoleActiveApiRequest,
)
from interfaces.dto.response_dto import ApiResponse, ok, fail
from domain.service.application_role_service import ApplicationRoleService


@logger()
class ApplicationRoleController(BaseController):
    def __init__(self, config: SysConfig, web_app: FastAPI, mysql_client=None):
        self.config = config
        self.app = web_app
        self.role_service = ApplicationRoleService(config, mysql_client)
        self._register_routes()

    def _register_routes(self):
        @self.app.post("/v1/agent/role/list", response_model=ApiResponse)
        async def list_roles(
            request: ApplicationRoleListApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                user_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.role_service.list_roles, user_id, request.data
                )
                if err == ErrorCode.SUCCESS:
                    data = (
                        result.model_dump()
                        if hasattr(result, "model_dump")
                        else result
                    )
                    return ok(data)
                return fail(err, result)
            except Exception as e:
                import traceback
                self.log.error(f"list_roles failed: {e}")
                self.log.error(traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/role/create", response_model=ApiResponse)
        async def create_role(
            request: ApplicationRoleSaveApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                user_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.role_service.create_role, user_id, request.data
                )
                if err == ErrorCode.SUCCESS:
                    data = (
                        result.model_dump()
                        if hasattr(result, "model_dump")
                        else result
                    )
                    return ok(data)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/role/get", response_model=ApiResponse)
        async def get_role(
            request: ApplicationRoleIdApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                user_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.role_service.get_role, user_id, request.data
                )
                if err == ErrorCode.SUCCESS:
                    data = (
                        result.model_dump()
                        if hasattr(result, "model_dump")
                        else result
                    )
                    return ok(data)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/role/update", response_model=ApiResponse)
        async def update_role(
            request: ApplicationRoleSaveApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                user_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.role_service.update_role, user_id, request.data
                )
                if err == ErrorCode.SUCCESS:
                    data = (
                        result.model_dump()
                        if hasattr(result, "model_dump")
                        else result
                    )
                    return ok(data)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/role/delete", response_model=ApiResponse)
        async def delete_role(
            request: ApplicationRoleIdApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                user_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.role_service.delete_role, user_id, request.data
                )
                if err == ErrorCode.SUCCESS:
                    return ok()
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/role/active_at_time", response_model=ApiResponse)
        async def get_active_roles_at_time(
            request: ApplicationRoleActiveApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """
            获取当前时间有效的角色列表
            如果有多个角色同时有效，需要用户选择
            """
            try:
                user_id = int(user_ctx.user_id)
                self.log.info(f"【角色选择】查询用户 {user_id} 当前有效的角色")
                
                err, result = await asyncio.to_thread(
                    self.role_service.get_active_roles_at_time, user_id, request.data
                )
                
                if err == ErrorCode.SUCCESS:
                    data = (
                        result.model_dump()
                        if hasattr(result, "model_dump")
                        else result
                    )
                    
                    # 根据结果添加提示信息
                    if result and result.has_multiple:
                        self.log.info(f"【角色选择】发现 {len(result.roles)} 个角色同时有效，需要用户选择")
                        for role in result.roles:
                            self.log.info(f"  - {role.name} (ID: {role.id})")
                    elif result and result.roles:
                        self.log.info(f"【角色选择】仅 1 个角色有效: {result.roles[0].name}")
                    else:
                        self.log.info("【角色选择】当前时间无有效角色")
                    
                    return ok(data)
                    
                return fail(err, result)
                
            except Exception as e:
                import traceback
                self.log.error(f"【角色选择】获取有效角色失败: {e}")
                self.log.error(traceback.format_exc())
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/role/toggle_status", response_model=ApiResponse)
        async def toggle_status(
            request: ApplicationRoleToggleStatusApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                user_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.role_service.toggle_status, user_id, request.data
                )
                if err == ErrorCode.SUCCESS:
                    data = (
                        result.model_dump()
                        if hasattr(result, "model_dump")
                        else result
                    )
                    return ok(data)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.SYSTEM_ERROR, str(e))
