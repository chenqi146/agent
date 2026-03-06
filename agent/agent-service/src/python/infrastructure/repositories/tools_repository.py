from typing import List, Tuple, Optional, Dict, Any
import json
from interfaces.dto.tools_dto import *
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger

@logger()
class ToolsRepository:
    def __init__(self, mysql_client):
        self.mysql = mysql_client

    # --- Tool Integration & Management ---
    def list_tools(self, page: int = 1, page_size: int = 20) -> Tuple[ErrorCode, List[Dict[str, Any]], int]:
        offset = (page - 1) * page_size
        sql = """
            SELECT t.*, i.endpoint_url
            FROM mcp_tools_tbl t
            LEFT JOIN tool_interfaces_tbl i ON t.id = i.tool_id AND i.is_default = 1
            LIMIT %s OFFSET %s
        """
        count_sql = "SELECT COUNT(*) as total FROM mcp_tools_tbl"
        
        err, rows = self.mysql.execute_sql(sql, params=(page_size, offset))
        if err != ErrorCode.SUCCESS:
            return err, [], 0
            
        err, count_rows = self.mysql.execute_sql(count_sql)
        total = count_rows[0]['total'] if count_rows else 0
        
        return ErrorCode.SUCCESS, rows, total

    def create_tool(self, tool_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        # Check if tool exists by name and server_id
        check_sql = "SELECT id FROM mcp_tools_tbl WHERE name = %s"
        params_check = [tool_data['name']]
        
        if tool_data.get('server_id'):
            check_sql += " AND server_id = %s"
            params_check.append(tool_data['server_id'])
        else:
            check_sql += " AND server_id IS NULL"
            
        check_sql += " LIMIT 1"
        
        try:
            err, rows = self.mysql.execute_sql(check_sql, params=tuple(params_check))
            if err == ErrorCode.SUCCESS and rows:
                existing_id = rows[0]['id']
                # Update existing tool
                update_sql = """
                    UPDATE mcp_tools_tbl
                    SET display_name=%s, description_short=%s, description_full=%s, 
                        tool_type=%s, category=%s, tags=%s, primary_skill_id=%s
                    WHERE id=%s
                """
                params_update = (
                    tool_data.get('display_name'),
                    tool_data.get('description_short'),
                    tool_data.get('description_full'),
                    tool_data['tool_type'],
                    tool_data.get('category'),
                    tool_data.get('tags'),
                    tool_data.get('primary_skill_id'),
                    existing_id
                )
                self.mysql.execute_sql(update_sql, params=params_update)
                return ErrorCode.SUCCESS, existing_id
            else:
                # Create new tool
                insert_sql = """
                    INSERT INTO mcp_tools_tbl 
                    (name, display_name, description_short, description_full, tool_type, category, tags, primary_skill_id, server_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params_insert = (
                    tool_data['name'],
                    tool_data.get('display_name'),
                    tool_data.get('description_short'),
                    tool_data.get('description_full'),
                    tool_data['tool_type'],
                    tool_data.get('category'),
                    tool_data.get('tags'),
                    tool_data.get('primary_skill_id'),
                    tool_data.get('server_id')
                )
                err, last_row_id = self.mysql.execute_sql(insert_sql, params=params_insert)
                return err, last_row_id
        except Exception as e:
            self.log.error(f"Error creating tool: {e}")
            return ErrorCode.DB_ERROR, 0

    def find_tool_by_intent(self, intent: str) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """
        Find a tool by intent (name, display_name, or tags).
        """
        sql = """
            SELECT * FROM mcp_tools_tbl 
            WHERE name = %s 
            OR display_name = %s 
            OR JSON_CONTAINS(tags, JSON_QUOTE(%s))
            LIMIT 1
        """
        try:
            err, rows = self.mysql.execute_sql(sql, params=(intent, intent, intent))
            if err == ErrorCode.SUCCESS and rows:
                return ErrorCode.SUCCESS, rows[0]
            return ErrorCode.TOOL_NOT_FOUND, None
        except Exception as e:
            self.log.error(f"Error finding tool by intent: {e}")
            return ErrorCode.DB_ERROR, None


    def get_tool_execution_info(self, tool_name: str) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """
        Get execution info for a tool: server URL, endpoint, method, timeout.
        """
        sql = """
            SELECT 
                t.name,
                s.server_url as base_url,
                s.api_key as api_key,
                i.endpoint_url,
                i.http_method,
                i.timeout_ms
            FROM mcp_tools_tbl t
            LEFT JOIN mcp_server_tbl s ON t.server_id = s.id
            LEFT JOIN tool_interfaces_tbl i ON t.id = i.tool_id
            WHERE t.name = %s AND i.is_default = 1
            LIMIT 1
        """
        try:
            err, rows = self.mysql.execute_sql(sql, params=(tool_name,))
            if err != ErrorCode.SUCCESS:
                return err, None
            if not rows:
                return ErrorCode.NOT_FOUND, None
            return ErrorCode.SUCCESS, rows[0]
        except Exception as e:
            self.log.error(f"Failed to get tool execution info: {e}")
            return ErrorCode.DATABASE_QUERY_ERROR, None

    def create_tool_interface(self, interface_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        input_schema = interface_data.get('input_schema')
        if isinstance(input_schema, (dict, list)):
            input_schema = json.dumps(input_schema)
            
        output_schema = interface_data.get('output_schema')
        if isinstance(output_schema, (dict, list)):
            output_schema = json.dumps(output_schema)
            
        examples = interface_data.get('examples')
        if isinstance(examples, (dict, list)):
            examples = json.dumps(examples)

        interface_type = interface_data.get('interface_type', 'full')
        version = interface_data.get('version', 'v1')
        
        # Check if interface exists
        check_sql = "SELECT id FROM tool_interfaces_tbl WHERE tool_id=%s AND interface_type=%s AND version=%s"
        params_check = (interface_data['tool_id'], interface_type, version)
        
        try:
            err, rows = self.mysql.execute_sql(check_sql, params=params_check)
            if err == ErrorCode.SUCCESS and rows:
                existing_id = rows[0]['id']
                # Update existing interface
                update_sql = """
                    UPDATE tool_interfaces_tbl
                    SET is_default=%s, endpoint_url=%s, http_method=%s,
                        timeout_ms=%s, description=%s, input_schema=%s, output_schema=%s, examples=%s
                    WHERE id=%s
                """
                params_update = (
                    interface_data.get('is_default', 1),
                    interface_data.get('endpoint_url', ''),
                    interface_data.get('http_method', 'POST'),
                    interface_data.get('timeout_ms', 30000),
                    interface_data.get('description'),
                    input_schema,
                    output_schema,
                    examples,
                    existing_id
                )
                err, _ = self.mysql.execute_sql(update_sql, params=params_update, commit=True)
                if err == ErrorCode.SUCCESS:
                    return ErrorCode.SUCCESS, existing_id
                return err, 0
        except Exception as e:
            self.log.error(f"Failed to check/update tool interface: {e}")
            return ErrorCode.DATABASE_QUERY_ERROR, 0

        sql = """
            INSERT INTO tool_interfaces_tbl (
                tool_id, interface_type, version, is_default, endpoint_url, http_method,
                timeout_ms, description, input_schema, output_schema, examples
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            interface_data['tool_id'],
            interface_type,
            version,
            interface_data.get('is_default', 1),
            interface_data.get('endpoint_url', ''),
            interface_data.get('http_method', 'POST'),
            interface_data.get('timeout_ms', 30000),
            interface_data.get('description'),
            input_schema,
            output_schema,
            examples
        )
        try:
            with self.mysql.get_cursor() as cursor:
                cursor.execute(sql, params)
                last_id = cursor.lastrowid
                return ErrorCode.SUCCESS, last_id
        except Exception as e:
            self.log.error(f"Failed to create tool interface: {e}")
            return ErrorCode.DATABASE_INSERT_ERROR, 0

    def create_tool_parameter(self, param_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        sql = """
            INSERT INTO tool_parameters_tbl (
                interface_id, param_name, display_name, description_full, description_short,
                data_type, required, default_value, example_value, complexity_level,
                learning_importance
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            param_data['interface_id'],
            param_data['param_name'],
            param_data.get('display_name'),
            param_data.get('description_full'),
            param_data.get('description_short'),
            param_data.get('data_type', 'string'),
            param_data.get('required', 0),
            param_data.get('default_value'),
            param_data.get('example_value'),
            param_data.get('complexity_level', 'medium'),
            param_data.get('learning_importance', 3)
        )
        try:
            with self.mysql.get_cursor() as cursor:
                cursor.execute(sql, params)
                last_id = cursor.lastrowid
                return ErrorCode.SUCCESS, last_id
        except Exception as e:
            self.log.error(f"Failed to create tool parameter: {e}")
            return ErrorCode.DATABASE_INSERT_ERROR, 0

    def create_tool_capability(self, cap_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        sql = """
            INSERT INTO tool_capabilities_tbl (
                tool_id, capability_name, display_name, description_full, description_short,
                available_in_full, available_in_compact
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            cap_data['tool_id'],
            cap_data['capability_name'],
            cap_data.get('display_name'),
            cap_data.get('description_full'),
            cap_data.get('description_short'),
            cap_data.get('available_in_full', 1),
            cap_data.get('available_in_compact', 1)
        )
        try:
            with self.mysql.get_cursor() as cursor:
                cursor.execute(sql, params)
                last_id = cursor.lastrowid
                return ErrorCode.SUCCESS, last_id
        except Exception as e:
            self.log.error(f"Failed to create tool capability: {e}")
            return ErrorCode.DATABASE_INSERT_ERROR, 0


    def update_tool(self, tool_id: int, tool_data: Dict[str, Any]) -> Tuple[ErrorCode, None]:
        if not tool_data:
            return ErrorCode.SUCCESS, None
            
        set_clauses = []
        params = []
        for key, value in tool_data.items():
            set_clauses.append(f"{key} = %s")
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            params.append(value)
            
        params.append(tool_id)
        sql = f"UPDATE mcp_tools_tbl SET {', '.join(set_clauses)} WHERE id = %s"
        
        err, _ = self.mysql.execute_sql(sql, params=tuple(params))
        return err, None

    def update_tool_default_interface(self, tool_id: int, endpoint_url: str = None, api_key: str = None) -> Tuple[ErrorCode, None]:
        set_clauses = []
        params = []
        if endpoint_url is not None:
            set_clauses.append("endpoint_url = %s")
            params.append(endpoint_url)
        
        # api_key is not supported in tool_interfaces_tbl
        # if api_key is not None:
        #     set_clauses.append("api_key = %s")
        #     params.append(api_key)
            
        if not set_clauses:
            return ErrorCode.SUCCESS, None
            
        params.append(tool_id)
        sql = f"UPDATE tool_interfaces_tbl SET {', '.join(set_clauses)} WHERE tool_id = %s AND is_default = 1"
        err, _ = self.mysql.execute_sql(sql, params=tuple(params))
        if err == ErrorCode.SUCCESS:
             # Check if updated, if not create one?
             # For now assume it exists if it was created properly.
             pass
        return err, None

    def delete_tool(self, tool_id: int) -> Tuple[ErrorCode, None]:
        sql = "DELETE FROM mcp_tools_tbl WHERE id = %s"
        err, _ = self.mysql.execute_sql(sql, params=(tool_id,))
        return err, None

    def create_tool_permission(self, perm_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        sql = """
            INSERT INTO tool_permissions_tbl (
                tool_id, user_type, user_id, permission_level, rate_limit,
                required_skill_level
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            perm_data['tool_id'],
            perm_data.get('user_type', 'all'),
            perm_data.get('user_id'),
            perm_data.get('permission_level', 'execute'),
            perm_data.get('rate_limit', 0),
            perm_data.get('required_skill_level', 'novice')
        )
        try:
            with self.mysql.get_cursor() as cursor:
                cursor.execute(sql, params)
                last_id = cursor.lastrowid
                return ErrorCode.SUCCESS, last_id
        except Exception as e:
            self.log.error(f"Failed to create tool permission: {e}")
            return ErrorCode.DATABASE_INSERT_ERROR, 0

    # --- MCP Tool Logs ---
    def get_tool_logs(self, query: ToolLogQuery) -> Tuple[ErrorCode, List[Dict[str, Any]], int]:
        offset = (query.page - 1) * query.page_size
        where_clauses = ["1=1"]
        params = []
        
        if query.tool_id:
            where_clauses.append("tool_id = %s")
            params.append(query.tool_id)
        if query.start_time:
            where_clauses.append("called_at >= %s")
            params.append(query.start_time)
        if query.end_time:
            where_clauses.append("called_at <= %s")
            params.append(query.end_time)
            
        where_str = " AND ".join(where_clauses)
        
        sql = f"""
            SELECT s.*, t.name as tool_name, t.tool_type 
            FROM tool_usage_stats_tbl s
            LEFT JOIN mcp_tools_tbl t ON s.tool_id = t.id
            WHERE {where_str} 
            ORDER BY s.called_at DESC 
            LIMIT %s OFFSET %s
        """
        count_sql = f"SELECT COUNT(*) as total FROM tool_usage_stats_tbl WHERE {where_str}"
        
        err, rows = self.mysql.execute_sql(sql, params=tuple(params + [query.page_size, offset]))
        if err != ErrorCode.SUCCESS:
            return err, [], 0
            
        err, count_rows = self.mysql.execute_sql(count_sql, params=tuple(params))
        total = count_rows[0]['total'] if count_rows else 0
        
        return ErrorCode.SUCCESS, rows, total

    # --- Tool Rating ---
    def get_tool_rating_list(self, page: int = 1, page_size: int = 20) -> Tuple[ErrorCode, List[Dict[str, Any]], int]:
        offset = (page - 1) * page_size
        
        # Calculate total count first
        count_sql = "SELECT COUNT(*) as total FROM mcp_tools_tbl"
        err, count_rows = self.mysql.execute_sql(count_sql)
        total = count_rows[0]['total'] if count_rows else 0
        
        if total == 0:
            return ErrorCode.SUCCESS, [], 0
            
        # Main query
        sql = """
            SELECT 
                t.id, 
                t.name, 
                t.display_name,
                t.tool_type,
                (SELECT endpoint_url FROM tool_interfaces_tbl WHERE tool_id = t.id AND is_default = 1 LIMIT 1) as endpoint_url,
                (SELECT AVG(rating) FROM user_skill_mastery_tbl WHERE primary_tool_id = t.id) as avg_rating,
                (IFNULL(t.call_count_full, 0) + IFNULL(t.call_count_compact, 0)) as call_count
            FROM mcp_tools_tbl t
            LIMIT %s OFFSET %s
        """
        
        err, rows = self.mysql.execute_sql(sql, params=(page_size, offset))
        return err, rows, total

    def add_tool_rating(self, rating_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        sql = """
            INSERT INTO user_skill_mastery_tbl (user_id, skill_id, primary_tool_id, rating)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            rating = VALUES(rating),
            primary_tool_id = VALUES(primary_tool_id)
        """
        params = (
            rating_data['user_id'],
            rating_data['skill_id'],
            rating_data['tool_id'],
            rating_data['rating']
        )
        err, last_id = self.mysql.execute_sql(sql, params=params, commit=True)
        return err, last_id

    def get_tool_ratings(self, tool_id: int) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        # This would require aggregation from user_skill_mastery_tbl or usage stats.
        sql = """
            SELECT AVG(rating) as avg_rating, COUNT(*) as count 
            FROM user_skill_mastery_tbl 
            WHERE primary_tool_id = %s AND rating IS NOT NULL
        """
        err, rows = self.mysql.execute_sql(sql, params=(tool_id,))
        return err, rows

    # --- Tool Relationships ---
    def create_tool_relationship(self, rel_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        sql = """
            INSERT INTO tool_relationships_tbl (source_tool_id, target_tool_id, relationship_type, weight)
            VALUES (%s, %s, %s, %s)
        """
        params = (
            rel_data['source_tool_id'],
            rel_data['target_tool_id'],
            rel_data['relationship_type'],
            rel_data.get('weight', 1.0)
        )
        err, last_id = self.mysql.execute_sql(sql, params=params, commit=True)
        return err, last_id

    def get_tool_relationships(self, tool_id: int) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        sql = "SELECT * FROM tool_relationships_tbl WHERE source_tool_id = %s OR target_tool_id = %s"
        err, rows = self.mysql.execute_sql(sql, params=(tool_id, tool_id))
        return err, rows

    def get_all_tool_relationships(self, page: int = 1, page_size: int = 20) -> Tuple[ErrorCode, List[Dict[str, Any]], int]:
        offset = (page - 1) * page_size
        
        count_sql = "SELECT COUNT(*) as total FROM tool_relationships_tbl"
        err, count_rows = self.mysql.execute_sql(count_sql)
        total = count_rows[0]['total'] if count_rows else 0
        
        if total == 0:
            return ErrorCode.SUCCESS, [], 0
            
        sql = """
            SELECT 
                r.id,
                r.source_tool_id,
                s.name as source_tool_name,
                r.target_tool_id,
                t.name as target_tool_name,
                r.relationship_type,
                r.weight
            FROM tool_relationships_tbl r
            LEFT JOIN mcp_tools_tbl s ON r.source_tool_id = s.id
            LEFT JOIN mcp_tools_tbl t ON r.target_tool_id = t.id
            ORDER BY r.id DESC
            LIMIT %s OFFSET %s
        """
        err, rows = self.mysql.execute_sql(sql, params=(page_size, offset))
        return err, rows, total

    # --- Snapshot Version Management ---
    def create_tool_snapshot(self, snapshot_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        sql = """
            INSERT INTO tool_interfaces_tbl (tool_id, interface_type, version, description, input_schema, output_schema)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            snapshot_data['tool_id'],
            snapshot_data.get('interface_type', 'full'),
            snapshot_data['version'],
            snapshot_data.get('description'),
            snapshot_data.get('input_schema'),
            snapshot_data.get('output_schema')
        )
        err, last_id = self.mysql.execute_sql(sql, params=params, commit=True)
        return err, last_id

    def list_tool_snapshots(self, tool_id: int) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        sql = "SELECT * FROM tool_interfaces_tbl WHERE tool_id = %s ORDER BY version DESC"
        err, rows = self.mysql.execute_sql(sql, params=(tool_id,))
        return err, rows

    def get_all_tool_snapshots(self, page: int = 1, page_size: int = 20) -> Tuple[ErrorCode, List[Dict[str, Any]], int]:
        offset = (page - 1) * page_size
        
        count_sql = "SELECT COUNT(*) as total FROM tool_interfaces_tbl"
        err, count_rows = self.mysql.execute_sql(count_sql)
        total = count_rows[0]['total'] if count_rows else 0
        
        if total == 0:
            return ErrorCode.SUCCESS, [], 0
            
        sql = """
            SELECT 
                s.id,
                s.tool_id,
                t.name as tool_name,
                s.interface_type,
                s.version,
                s.description,
                s.created_at
            FROM tool_interfaces_tbl s
            LEFT JOIN mcp_tools_tbl t ON s.tool_id = t.id
            ORDER BY s.version DESC, s.created_at DESC
            LIMIT %s OFFSET %s
        """
        err, rows = self.mysql.execute_sql(sql, params=(page_size, offset))
        return err, rows, total

    # --- Tool Discovery Model ---
    def get_tool_discovery_recommendations(self, query: ToolDiscoveryQuery) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        # This is a complex query, simplified for now.
        sql = """
            SELECT t.*, s.skill_name 
            FROM mcp_tools_tbl t
            LEFT JOIN skill_definitions_tbl s ON t.primary_skill_id = s.id
            WHERE 1=1
        """
        params = []
        if query.skill_id:
            sql += " AND t.primary_skill_id = %s"
            params.append(query.skill_id)
        if query.category:
            sql += " AND t.category = %s"
            params.append(query.category)
            
        err, rows = self.mysql.execute_sql(sql, params=tuple(params))
        return err, rows

    # --- MCP Server Management ---
    def get_mcp_servers(self, active_only: bool = True) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        sql = "SELECT id, server_name, server_url as base_url, api_key, is_active, created_at, updated_at FROM mcp_server_tbl"
        if active_only:
            sql += " WHERE is_active = 1"
        try:
            err, rows = self.mysql.execute_sql(sql)
            return err, rows
        except Exception as e:
            self.log.error(f"Failed to get MCP servers: {e}")
            return ErrorCode.DATABASE_QUERY_ERROR, []

    def create_mcp_server(self, server_data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        # Check if server exists by URL or Name
        check_sql = "SELECT id FROM mcp_server_tbl WHERE server_url = %s OR server_name = %s LIMIT 1"
        try:
            err, rows = self.mysql.execute_sql(check_sql, params=(server_data['base_url'], server_data['server_name']))
            if err == ErrorCode.SUCCESS and rows:
                existing_id = rows[0]['id']
                # Update existing server
                update_sql = """
                    UPDATE mcp_server_tbl 
                    SET server_name = %s, server_url = %s, api_key = %s, is_active = %s
                    WHERE id = %s
                """
                params = (
                    server_data['server_name'],
                    server_data['base_url'],
                    server_data.get('api_key'),
                    server_data.get('is_active', 1),
                    existing_id
                )
                err, _ = self.mysql.execute_sql(update_sql, params=params, commit=True)
                if err == ErrorCode.SUCCESS:
                    return ErrorCode.SUCCESS, existing_id
                return err, 0
        except Exception as e:
            self.log.error(f"Failed to check/update MCP server: {e}")
            return ErrorCode.DATABASE_QUERY_ERROR, 0

        sql = """
            INSERT INTO mcp_server_tbl (server_name, server_url, api_key, is_active)
            VALUES (%s, %s, %s, %s)
        """
        params = (
            server_data['server_name'],
            server_data['base_url'],
            server_data.get('api_key'),
            server_data.get('is_active', 1)
        )
        try:
            with self.mysql.get_cursor() as cursor:
                cursor.execute(sql, params)
                last_id = cursor.lastrowid
                return ErrorCode.SUCCESS, last_id
        except Exception as e:
            self.log.error(f"Failed to create MCP server: {e}")
            return ErrorCode.DATABASE_INSERT_ERROR, 0
