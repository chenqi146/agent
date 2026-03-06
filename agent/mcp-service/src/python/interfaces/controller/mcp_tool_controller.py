from fastapi import APIRouter, Depends, Query, Path, Body
from typing import List, Optional, Dict, Any
from interfaces.controller.base_controller import BaseController
from domain.service.mcp_tool_service import McpToolService
from interfaces.dto.mcp_tool_dto import *
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.error.http_errcode import ApiResponse
from infrastructure.common.logging.logging import logger

@logger()
class McpToolController(BaseController):
    def __init__(self, service: McpToolService):
        super().__init__()
        self.service = service
        self.router = APIRouter(prefix="/v1/tools", tags=["MCP Tools"])
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route("", self.list_tools, methods=["GET"], response_model=Dict[str, Any])
        self.router.add_api_route("/execute", self.execute_tool, methods=["POST"], response_model=ToolExecutionResponse)
        self.router.add_api_route("/{tool_name}/execute", self.execute_tool_by_name, methods=["POST"], response_model=ToolExecutionResponse)
        self.router.add_api_route("/{tool_name}", self.get_tool_definition, methods=["GET"], response_model=Dict[str, Any])

    async def list_tools(self, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
        result = self.service.list_tools(page, page_size)
        self.log.debug(f"List tools: {result}")
        return ApiResponse.success(result)

    async def execute_tool(self, request: ToolExecutionRequest = Body(...)):
        try:
            self.log.debug(f"Executing tool: {request.tool_name} with arguments: {request.arguments}")
            result = await self.service.execute_tool(request)
            return result
        except Exception as e:
            self.log.error(f"Execution error: {e}")
            return ToolExecutionResponse(status="error", result=None, error_message=str(e), execution_time_ms=0.0)

    async def execute_tool_by_name(
        self,
        tool_name: str = Path(...),
        arguments: Dict[str, Any] = Body(...),
        interface_type: InterfaceType = Query(InterfaceType.FULL)
    ):
        request = ToolExecutionRequest(
            tool_name=tool_name,
            interface_type=interface_type,
            arguments=arguments
        )
        self.log.debug(f"Executing tool by name: {tool_name} with arguments: {arguments} and interface type: {interface_type}")
        return await self.execute_tool(request)

    async def get_tool_definition(self, tool_name: str = Path(...), interface_type: InterfaceType = Query(InterfaceType.FULL)):
        definition = self.service.get_tool_definition(tool_name, interface_type)
        if not definition:
            return ApiResponse.error_by_enum(ErrorCode.NOT_FOUND, f"Tool {tool_name} not found")
        self.log.debug(f"Get tool definition: {definition}")
        return ApiResponse.success(definition)
