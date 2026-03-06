from typing import List, Tuple, Dict, Any, Optional
import httpx
from infrastructure.repositories.tools_repository import ToolsRepository
from interfaces.dto.tools_dto import *
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger

@logger()
class ToolsService:
    def __init__(self, repository: ToolsRepository):
        self.repo = repository

    # --- Tool Execution (Delegated to MCP Service) ---
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[ErrorCode, Any]:
        err, info = self.repo.get_tool_execution_info(tool_name)
        if err != ErrorCode.SUCCESS:
            return err, "Failed to get tool execution info"
        if not info:
            return ErrorCode.TOOL_NOT_FOUND, f"Tool {tool_name} execution info not found"
            
        base_url = info.get('base_url')
        endpoint_url = info.get('endpoint_url')
        method = info.get('http_method', 'POST')
        timeout_ms = info.get('timeout_ms', 30000)
        api_key = info.get('api_key')
        
        if not endpoint_url:
             return ErrorCode.TOOL_EXECUTION_ERROR, "Tool endpoint not defined"
             
        if endpoint_url.startswith("http"):
            url = endpoint_url
        else:
            if not base_url:
                return ErrorCode.TOOL_EXECUTION_ERROR, "MCP Server base URL not defined"
            url = f"{base_url.rstrip('/')}/{endpoint_url.lstrip('/')}"
            
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            with httpx.Client() as client:
                response = client.request(
                    method=method,
                    url=url,
                    json=arguments,
                    headers=headers,
                    timeout=timeout_ms / 1000.0
                )
                
                if response.status_code >= 400:
                     return ErrorCode.TOOL_EXECUTION_ERROR, f"Tool execution failed: {response.text}"
                     
                return ErrorCode.SUCCESS, response.json()
        except Exception as e:
            self.log.error(f"Tool execution error: {e}")
            return ErrorCode.TOOL_EXECUTION_ERROR, str(e)

    # --- Tool Integration & Management ---
    def list_tools(self, page: int, page_size: int) -> Tuple[ErrorCode, Dict[str, Any]]:
        # Fetch local tools only
        err, local_tools, local_total = self.repo.list_tools(page, page_size)
        if err != ErrorCode.SUCCESS:
            return ErrorCode.DATABASE_QUERY_ERROR, {}
        return ErrorCode.SUCCESS, {"items": local_tools, "total": local_total}

    def create_tool(self, req: ToolCreateRequest) -> Tuple[ErrorCode, Dict[str, Any]]:
        # 1. Create the main tool entry
        # Supports importing tool details via manual entry or discovery service (if configured).
        # Requires server_id if the tool is hosted on a dynamic MCP server.
        err, tool_id = self.repo.create_tool(req.dict())
        if err != ErrorCode.SUCCESS:
            return err, {}
            
        # 2. Create default interface if endpoint is provided
        if req.endpoint_url:
            interface_data = {
                "tool_id": tool_id,
                "interface_type": "full",
                "version": "v1",
                "is_default": 1,
                "endpoint_url": req.endpoint_url,
                "api_key": req.api_key,
                "http_method": "POST", # Default to POST
                "description": req.description_short
            }
            self.repo.create_tool_interface(interface_data)
            
        return ErrorCode.SUCCESS, {"id": tool_id}

    def update_tool(self, req: ToolUpdateRequest) -> Tuple[ErrorCode, None]:
        data = req.dict(exclude_unset=True)
        tool_id = data.get("id")
        if "id" in data:
            del data["id"]
            
        # Check if endpoint_url or api_key needs update
        if "endpoint_url" in data or "api_key" in data:
            endpoint_url = data.pop("endpoint_url", None)
            api_key = data.pop("api_key", None)
            # Update interface
            self.repo.update_tool_default_interface(tool_id, endpoint_url, api_key)

        err, _ = self.repo.update_tool(tool_id, data)
        return err, None

    def delete_tool(self, tool_id: int) -> Tuple[ErrorCode, None]:
        return self.repo.delete_tool(tool_id)

    def discover_tools(self, mcp_server_url: str, api_key: str = None) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """
        Discover tools from an MCP server.
        
        Args:
            mcp_server_url: The base URL of the MCP server
            api_key: Optional API key for authentication
            
        Returns:
            Tuple[ErrorCode, List[Dict]]: Error code and list of tool definitions
        """
        if not mcp_server_url:
            return ErrorCode.PARAM_ERROR, []

        url = f"{mcp_server_url.rstrip('/')}/v1/tools"
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                
            with httpx.Client() as client:
                response = client.get(url, headers=headers, timeout=10.0)
                if response.status_code != 200:
                    self.log.error(f"Discovery failed: {response.status_code} - {response.text}")
                    return ErrorCode.EXTERNAL_SERVICE_ERROR, []
                
                result = response.json()
                # Handle potential wrapper format { code: 0, data: [...] }
                if isinstance(result, dict) and "data" in result:
                     return ErrorCode.SUCCESS, result["data"]
                elif isinstance(result, dict) and "items" in result:
                     return ErrorCode.SUCCESS, result["items"]
                return ErrorCode.SUCCESS, result
        except Exception as e:
            self.log.error(f"Tool discovery error: {e}")
            return ErrorCode.EXTERNAL_SERVICE_ERROR, []

    # --- MCP Server Management ---
    def get_mcp_servers(self, active_only: bool = True) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        return self.repo.get_mcp_servers(active_only)

    def create_mcp_server(self, server_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.repo.create_mcp_server(server_data)

    # --- MCP Tool Logs ---
    def get_tool_logs(self, query: ToolLogQuery) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, logs, total = self.repo.get_tool_logs(query)
        if err != ErrorCode.SUCCESS:
            return err, {}
        return ErrorCode.SUCCESS, {"items": logs, "total": total}

    # --- Tool Rating ---
    def get_tool_rating_list(self, page: int = 1, page_size: int = 20) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, tools, total = self.repo.get_tool_rating_list(page, page_size)
        if err != ErrorCode.SUCCESS:
            return err, {}
        return ErrorCode.SUCCESS, {"items": tools, "total": total}

    def add_tool_rating(self, user_id: str, req: ToolRatingCreateRequest) -> Tuple[ErrorCode, Dict[str, Any]]:
        data = req.dict()
        data['user_id'] = user_id
        err, rating_id = self.repo.add_tool_rating(data)
        return err, {"id": rating_id}

    def get_tool_ratings(self, tool_id: int) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, ratings = self.repo.get_tool_ratings(tool_id)
        return err, {"ratings": ratings}

    # --- Tool Relationships ---
    def create_tool_relationship(self, req: ToolRelationCreateRequest) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, rel_id = self.repo.create_tool_relationship(req.dict())
        return err, {"id": rel_id}

    def get_tool_relationships(self, tool_id: int) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, rels = self.repo.get_tool_relationships(tool_id)
        return err, {"relationships": rels}

    def get_all_tool_relationships(self, page: int = 1, page_size: int = 20) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, rels, total = self.repo.get_all_tool_relationships(page, page_size)
        if err != ErrorCode.SUCCESS:
            return err, {}
        return ErrorCode.SUCCESS, {"items": rels, "total": total}

    # --- Snapshot Version Management ---
    def create_tool_snapshot(self, req: ToolSnapshotCreateRequest) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, snap_id = self.repo.create_tool_snapshot(req.dict())
        return err, {"id": snap_id}

    def list_tool_snapshots(self, tool_id: int) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, snapshots = self.repo.list_tool_snapshots(tool_id)
        return err, {"snapshots": snapshots}

    def get_all_tool_snapshots(self, page: int = 1, page_size: int = 20) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, snaps, total = self.repo.get_all_tool_snapshots(page, page_size)
        if err != ErrorCode.SUCCESS:
            return err, {}
        return ErrorCode.SUCCESS, {"items": snaps, "total": total}

    # --- Tool Discovery Model ---
    def get_tool_discovery_recommendations(self, query: ToolDiscoveryQuery) -> Tuple[ErrorCode, Dict[str, Any]]:
        err, recs = self.repo.get_tool_discovery_recommendations(query)
        return err, {"recommendations": recs}
