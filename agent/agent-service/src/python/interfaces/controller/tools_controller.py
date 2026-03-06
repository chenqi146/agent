import asyncio
from typing import List, Dict, Any

from fastapi import FastAPI, Depends, Query, Body

from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger
from infrastructure.config.sys_config import SysConfig
from interfaces.controller.base_controller import BaseController
from interfaces.deps.user_context import UserContext, get_validated_user_context
from interfaces.dto.response_dto import ApiResponse, ok, fail
from domain.service.tools_service import ToolsService
from infrastructure.repositories.tools_repository import ToolsRepository
from interfaces.dto.tools_dto import (
    ToolCreateRequest,
    ToolUpdateRequest,
    ToolLogQuery,
    ToolRatingCreateRequest,
    ToolRelationCreateRequest,
    ToolSnapshotCreateRequest,
    ToolDiscoveryQuery,
)

@logger()
class ToolsController(BaseController):
    def __init__(self, config: SysConfig, web_app: FastAPI, mysql_client=None):
        self.config = config
        self.app = web_app
        self.repo = ToolsRepository(mysql_client)
        self.service = ToolsService(self.repo)
        self._register_routes()

    def _register_routes(self):
        # --- Tool Execution (Delegated to MCP Service) ---
        @self.app.post("/v1/agent/tools/execute", response_model=ApiResponse)
        async def execute_tool(
            request: Dict[str, Any] = Body(...),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                tool_name = request.get("tool_name")
                arguments = request.get("arguments", {})
                if not tool_name:
                    return fail(ErrorCode.PARAM_ERROR, "tool_name is required")
                    
                err, result = await asyncio.to_thread(self.service.execute_tool, tool_name, arguments)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        # --- Tool Integration & Management ---
        @self.app.get("/v1/agent/tools/integrate/list", response_model=ApiResponse)
        async def list_tools(
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.list_tools, page, page_size)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        @self.app.post("/v1/agent/tools/integrate/add", response_model=ApiResponse)
        async def create_tool(
            request: ToolCreateRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.create_tool, request)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        @self.app.post("/v1/agent/tools/integrate/update", response_model=ApiResponse)
        async def update_tool(
            request: ToolUpdateRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.update_tool, request)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        @self.app.post("/v1/agent/tools/integrate/delete", response_model=ApiResponse)
        async def delete_tool(
            request: Dict[str, Any] = Body(...),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                tool_id = request.get("tool_id") or request.get("id")
                if not tool_id:
                    return fail(ErrorCode.PARAM_ERROR, "tool_id is required")
                
                try:
                    tool_id = int(tool_id)
                except ValueError:
                    return fail(ErrorCode.PARAM_ERROR, "tool_id must be an integer")

                err, result = await asyncio.to_thread(self.service.delete_tool, tool_id)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        # --- MCP Server Management ---
        @self.app.get("/v1/agent/tools/server/list", response_model=ApiResponse)
        async def list_mcp_servers(
            active_only: bool = Query(True),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.get_mcp_servers, active_only)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        @self.app.post("/v1/agent/tools/server/add", response_model=ApiResponse)
        async def create_mcp_server(
            request: Dict[str, Any] = Body(...),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                if "server_name" not in request or "base_url" not in request:
                    return fail(ErrorCode.PARAM_ERROR, "server_name and base_url are required")
                    
                err, result = await asyncio.to_thread(self.service.create_mcp_server, request)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        # --- MCP Tool Discovery ---
        @self.app.get("/v1/agent/tools/integrate/discover", response_model=ApiResponse)
        async def discover_tools(
            url: str = Query(..., alias="url"),
            api_key: str = Query(None, alias="api_key"),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.discover_tools, url, api_key)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        # --- MCP Tool Logs ---
        @self.app.post("/v1/agent/tools/log/list", response_model=ApiResponse)
        async def get_tool_logs(
            request: ToolLogQuery,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.get_tool_logs, request)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        # --- Tool Rating ---
        @self.app.get("/v1/agent/tools/rating/summary", response_model=ApiResponse)
        async def get_tool_rating_list(
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.get_tool_rating_list, page, page_size)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        @self.app.post("/v1/agent/tools/rating/add", response_model=ApiResponse)
        async def add_tool_rating(
            request: ToolRatingCreateRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.add_tool_rating, user_ctx.user_id, request)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        @self.app.get("/v1/agent/tools/rating/list", response_model=ApiResponse)
        async def get_tool_ratings(
            tool_id: int = Query(..., alias="toolId"),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.get_tool_ratings, tool_id)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        # --- Tool Relationships ---
        @self.app.post("/v1/agent/tools/relation/add", response_model=ApiResponse)
        async def create_tool_relationship(
            request: ToolRelationCreateRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.create_tool_relationship, request)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        @self.app.get("/v1/agent/tools/relation/list", response_model=ApiResponse)
        async def get_tool_relationships(
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
            tool_id: int = Query(None, alias="toolId"),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                if tool_id:
                    # The current get_tool_relationships returns ALL relationships for a tool.
                    err, result = await asyncio.to_thread(self.service.get_tool_relationships, tool_id)
                    # result is {"relationships": [...]}
                    if err == ErrorCode.SUCCESS:
                        return ok(result)
                    return fail(err, result)
                else:
                    # List all relationships paginated
                    err, result = await asyncio.to_thread(self.service.get_all_tool_relationships, page, page_size)
                    if err == ErrorCode.SUCCESS:
                        return ok(result)
                    return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        # --- Snapshot Version Management ---
        @self.app.post("/v1/agent/tools/version/create", response_model=ApiResponse)
        async def create_tool_snapshot(
            request: ToolSnapshotCreateRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.create_tool_snapshot, request)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        @self.app.get("/v1/agent/tools/version/list", response_model=ApiResponse)
        async def list_tool_snapshots(
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
            tool_id: int = Query(None, alias="toolId"),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                if tool_id:
                    err, result = await asyncio.to_thread(self.service.list_tool_snapshots, tool_id)
                    if err == ErrorCode.SUCCESS:
                        return ok(result)
                    return fail(err, result)
                else:
                    err, result = await asyncio.to_thread(self.service.get_all_tool_snapshots, page, page_size)
                    if err == ErrorCode.SUCCESS:
                        return ok(result)
                    return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        # --- Tool Discovery Model ---
        @self.app.post("/v1/agent/tools/discovery/search", response_model=ApiResponse)
        async def get_tool_discovery_recommendations(
            request: ToolDiscoveryQuery,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            try:
                err, result = await asyncio.to_thread(self.service.get_tool_discovery_recommendations, request)
                if err == ErrorCode.SUCCESS:
                    return ok(result)
                return fail(err, result)
            except Exception as e:
                return fail(ErrorCode.INTERNAL_ERROR, str(e))
