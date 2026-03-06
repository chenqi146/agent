import asyncio

from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse

from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger
from infrastructure.config.sys_config import SysConfig
from interfaces.controller.base_controller import BaseController
from interfaces.deps.user_context import UserContext, get_validated_user_context
from interfaces.dto.prompt_dto import (
    PromptTemplateListApiRequest,
    PromptTemplateSaveApiRequest,
    PromptTemplateIdApiRequest,
    PromptTemplateToggleStatusApiRequest,
    PromptAbTestRunApiRequest,
    PromptQuickTestRunApiRequest,
    PromptBatchTestRunApiRequest,
)
from interfaces.dto.response_dto import ApiResponse, ok, fail
from domain.service.prompt_service import PromptService


@logger()
class PromptController(BaseController):
    def __init__(self, config: SysConfig, web_app: FastAPI, mysql_client=None):
        self.config = config
        self.app = web_app
        self.prompt_service = PromptService(config, mysql_client)
        self._register_routes()

    def _register_routes(self):
        @self.app.post("/v1/agent/prompt/template/list", response_model=ApiResponse)
        async def list_templates(
            request: PromptTemplateListApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.prompt_service.list_templates, request.data, creator_id
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

        @self.app.post("/v1/agent/prompt/template/create", response_model=ApiResponse)
        async def create_template(
            request: PromptTemplateSaveApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.prompt_service.create_template, request.data, creator_id
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

        @self.app.post("/v1/agent/prompt/template/get", response_model=ApiResponse)
        async def get_template(
            request: PromptTemplateIdApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.prompt_service.get_template, request.data, creator_id
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

        @self.app.post("/v1/agent/prompt/template/update", response_model=ApiResponse)
        async def update_template(
            request: PromptTemplateSaveApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.prompt_service.update_template, request.data, creator_id
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

        @self.app.post("/v1/agent/prompt/template/delete", response_model=ApiResponse)
        async def delete_template(
            request: PromptTemplateIdApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.prompt_service.delete_template, request.data, creator_id
                )
                if err == ErrorCode.SUCCESS:
                    return ok()
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/prompt/template/toggle_status", response_model=ApiResponse)
        async def toggle_status(
            request: PromptTemplateToggleStatusApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                err, result = await asyncio.to_thread(
                    self.prompt_service.toggle_status, request.data, creator_id
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

        @self.app.post("/v1/agent/prompt/test/ab_run", response_model=ApiResponse)
        async def run_ab_test(
            request: PromptAbTestRunApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                err, result = await self.prompt_service.run_ab_test(request.data, creator_id)
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

        @self.app.post("/v1/agent/prompt/test/ab_run_stream")
        async def run_ab_test_stream(
            request: PromptAbTestRunApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                return StreamingResponse(
                    self.prompt_service.run_ab_test_stream(request.data, creator_id),
                    media_type="text/event-stream"
                )
            except Exception as e:
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/prompt/test/quick_run_stream")
        async def run_quick_test_stream(
            request: PromptQuickTestRunApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                return StreamingResponse(
                    self.prompt_service.run_quick_test_stream(request.data, creator_id),
                    media_type="text/plain"
                )
            except Exception as e:
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/prompt/test/quick_run", response_model=ApiResponse)
        async def run_quick_test(
            request: PromptQuickTestRunApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                err, result = await self.prompt_service.run_quick_test(request.data, creator_id)
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

        @self.app.post("/v1/agent/prompt/test/batch_run", response_model=ApiResponse)
        async def run_batch_test(
            request: PromptBatchTestRunApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                creator_id = int(user_ctx.user_id)
                err, result = await self.prompt_service.run_batch_test(request.data, creator_id)
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
