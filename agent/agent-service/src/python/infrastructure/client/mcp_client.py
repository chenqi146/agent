from typing import Dict, Any, Tuple, Optional, List
import requests
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger
from infrastructure.config.sys_config import SysConfig
from infrastructure.persistences.mysql_persistence import MysqlPersistence

@logger()
class McpClient:
    def __init__(self, config: SysConfig, mysql_persistence: MysqlPersistence = None):
        self.config = config
        self.mysql = mysql_persistence
        # Default fallback if DB fails
        mcp_config = config.get_system_config().get("mcp_service", {})
        self.base_url = mcp_config.get("url", "http://localhost:8000").rstrip("/")
        self.api_key = mcp_config.get("api_key", "")
        self.timeout = mcp_config.get("timeout", 30)

    def _get_mcp_servers(self) -> List[Dict[str, str]]:
        """
        Fetch all MCP servers from database.
        Returns a list of dicts with 'url' and 'api_key'.
        """
        servers = []
        # 1. Add default from config (if configured)
        if self.base_url and "localhost:8000" not in self.base_url:
             servers.append({"url": self.base_url, "api_key": self.api_key})

        # 2. Fetch from DB
        if self.mysql:
            sql = "SELECT server_url, api_key, is_active FROM mcp_server_tbl WHERE is_active = 1"
            err, rows = self.mysql.execute_sql(sql)
            if err == ErrorCode.SUCCESS and rows:
                for row in rows:
                    servers.append({
                        "url": row['server_url'].rstrip("/"),
                        "api_key": row.get('api_key', '')
                    })
        
        # If no servers found, fallback to default localhost:8000 to show error
        if not servers:
             servers.append({"url": "http://localhost:8000", "api_key": ""})
             
        return servers

    def _get_headers(self, api_key: str = None) -> Dict[str, str]:
        headers = {}
        key = api_key or self.api_key
        if key:
            headers["X-API-Key"] = key
        return headers

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[ErrorCode, Any]:
        servers = self._get_mcp_servers()
        last_error = None
        
        # Try to execute on first matching server (or all?)
        # Ideally, we should know which server hosts the tool.
        # For now, we iterate until success.
        for server in servers:
            url = f"{server['url']}/v1/tools/execute"
            data = {
                "tool_name": tool_name,
                "arguments": arguments
            }
            try:
                response = requests.post(url, json=data, headers=self._get_headers(server['api_key']), timeout=self.timeout)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        return ErrorCode.SUCCESS, result.get("result")
                    elif result.get("code") == 0:
                         return ErrorCode.SUCCESS, result.get("data")
                    else:
                        last_error = result.get("error_message") or result.get("message")
                        continue # Try next server?
                else:
                    self.log.warning(f"MCP execute failed on {server['url']}: {response.status_code}")
                    last_error = f"HTTP {response.status_code}"
            except Exception as e:
                self.log.error(f"MCP execute exception on {server['url']}: {e}")
                last_error = str(e)
                
        return ErrorCode.EXTERNAL_SERVICE_ERROR, last_error or "No available MCP server found"

    def list_tools(self, page: int = 1, page_size: int = 20) -> Tuple[ErrorCode, Any]:
        servers = self._get_mcp_servers()
        all_tools = []
        
        for server in servers:
            url = f"{server['url']}/v1/tools"
            params = {"page": page, "page_size": page_size}
            try:
                response = requests.get(url, params=params, headers=self._get_headers(server['api_key']), timeout=self.timeout)
                if response.status_code == 200:
                    result = response.json()
                    tools = []
                    if result.get("code") == 0:
                         tools = result.get("data", {}).get("items", [])
                    elif isinstance(result, list):
                        tools = result
                    elif isinstance(result, dict) and "items" in result:
                        tools = result["items"]
                        
                    all_tools.extend(tools)
                else:
                    self.log.warning(f"MCP list failed on {server['url']}: {response.status_code}")
            except Exception as e:
                self.log.error(f"MCP list exception on {server['url']}: {e}")
        
        # Aggregate results
        return ErrorCode.SUCCESS, all_tools

    def get_tool_definition(self, tool_name: str) -> Tuple[ErrorCode, Any]:
        servers = self._get_mcp_servers()
        last_error = None
        
        for server in servers:
            url = f"{server['url']}/v1/tools/{tool_name}"
            try:
                response = requests.get(url, headers=self._get_headers(server['api_key']), timeout=self.timeout)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        return ErrorCode.SUCCESS, result.get("data")
                    return ErrorCode.SUCCESS, result
                else:
                    last_error = f"HTTP {response.status_code}"
            except Exception as e:
                last_error = str(e)
                
        return ErrorCode.EXTERNAL_SERVICE_ERROR, last_error or "Tool definition not found on any server"
