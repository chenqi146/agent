from typing import List, Tuple, Optional, Dict, Any
from interfaces.dto.mcp_tool_dto import *
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger

@logger()
class McpToolRepository:
    def __init__(self, mysql_client):
        self.mysql = mysql_client

    # --- Tool Integration & Management ---
    def list_tools(self, page: int = 1, page_size: int = 20) -> Tuple[ErrorCode, List[Dict[str, Any]], int]:
        import json
        offset = (page - 1) * page_size
        # Join with interface table to get input_schema for the default interface
        sql = """
            SELECT t.*, i.input_schema, i.endpoint_url 
            FROM ms_tools_tbl t
            LEFT JOIN ms_tool_interfaces_tbl i ON t.id = i.tool_id AND i.is_default = 1
            LIMIT %s OFFSET %s
        """
        count_sql = "SELECT COUNT(*) as total FROM ms_tools_tbl"
        
        err, rows = self.mysql.execute_sql(sql, params=(page_size, offset))
        if err != ErrorCode.SUCCESS:
            return err, [], 0
            
        # Transform snake_case to camelCase for API consistency
        for row in rows:
            if 'input_schema' in row:
                val = row.pop('input_schema')
                if isinstance(val, str):
                    try:
                        row['inputSchema'] = json.loads(val)
                    except json.JSONDecodeError:
                        row['inputSchema'] = {} # Fallback or keep as string? 
                        # Ideally log warning but for now empty dict is safer than broken JSON
                else:
                    row['inputSchema'] = val

            if 'endpoint_url' in row:
                row['endpointUrl'] = row.pop('endpoint_url')
            
        err, count_rows = self.mysql.execute_sql(count_sql)
        total = count_rows[0]['total'] if count_rows else 0
        
        return ErrorCode.SUCCESS, rows, total

    def create_tool(self, tool_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        import json
        from enum import Enum
        
        # Prepare data for insertion
        params = tool_data.copy()
        
        # Serialize tags
        if isinstance(params.get('tags'), list):
            params['tags'] = json.dumps(params['tags'], ensure_ascii=False)
            
        # Serialize tool_type
        if isinstance(params.get('tool_type'), Enum):
            params['tool_type'] = params['tool_type'].value
            
        # Use insert method to get the ID
        return self.mysql.insert('ms_tools_tbl', params)

    def create_tool_interface(self, interface_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        sql = """
            INSERT INTO ms_tool_interfaces_tbl (
                tool_id, interface_type, version, is_default, endpoint_url, 
                description, input_schema, estimated_token_length
            ) VALUES (
                %(tool_id)s, %(interface_type)s, %(version)s, %(is_default)s, %(endpoint_url)s,
                %(description)s, %(input_schema)s, %(estimated_token_length)s
            ) ON DUPLICATE KEY UPDATE
                description = VALUES(description),
                input_schema = VALUES(input_schema),
                estimated_token_length = VALUES(estimated_token_length),
                updated_at = NOW()
        """
        err, result = self.mysql.execute_sql(sql, params=interface_data)
        if err != ErrorCode.SUCCESS:
            return err, 0
        return ErrorCode.SUCCESS, result

    def get_tool_by_name(self, name: str) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        sql = "SELECT * FROM ms_tools_tbl WHERE name = %s"
        err, rows = self.mysql.execute_sql(sql, params=(name,))
        if err != ErrorCode.SUCCESS:
            return err, None
        if not rows:
            return ErrorCode.SUCCESS, None
        return ErrorCode.SUCCESS, rows[0]
    
    def get_tool_interface(self, tool_id: int, interface_type: str, version: str = 'v1') -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        sql = """
            SELECT * FROM ms_tool_interfaces_tbl 
            WHERE tool_id = %s AND interface_type = %s AND version = %s
        """
        err, rows = self.mysql.execute_sql(sql, params=(tool_id, interface_type, version))
        if err != ErrorCode.SUCCESS:
            return err, None
        if not rows:
            # Try default version if specific version not found?
            # For now, just return None
            return ErrorCode.SUCCESS, None
        return ErrorCode.SUCCESS, rows[0]

    def update_tool(self, tool_id: int, tool_data: Dict[str, Any]) -> Tuple[ErrorCode, None]:
        if not tool_data:
            return ErrorCode.SUCCESS, None
            
        import json
        from enum import Enum
        
        set_clauses = []
        params = []
        for key, value in tool_data.items():
            set_clauses.append(f"{key} = %s")
            
            # Serialize special types
            if key == 'tags' and isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False)
            elif key == 'tool_type' and isinstance(value, Enum):
                value = value.value
                
            params.append(value)
            
        sql = f"UPDATE ms_tools_tbl SET {', '.join(set_clauses)} WHERE id = %s"
        params.append(tool_id)
        
        err, _ = self.mysql.execute_sql(sql, params=tuple(params))
        return err, None

    def delete_tool(self, tool_id: int) -> Tuple[ErrorCode, None]:
        sql = "DELETE FROM mcp_tools_tbl WHERE id = %s"
        err, _ = self.mysql.execute_sql(sql, params=(tool_id,))
        return err, None

