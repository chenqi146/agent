from typing import Any, Dict, List, Optional, Tuple

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.config.sys_config import SysConfig
from infrastructure.persistences.mysql_persistence import MysqlPersistence


@logger()
class ApplicationRoleRepository:
    def __init__(self, config: SysConfig, mysql_client: Optional[MysqlPersistence] = None):
        if mysql_client:
            self.mysql = mysql_client
        else:
            system_cfg = config.get_system_config() or {}
            mysql_cfg = system_cfg.get("persistence", {}).get("mysql", {}) or {}
            self.mysql = MysqlPersistence(
                host=mysql_cfg.get("host", "127.0.0.1"),
                port=mysql_cfg.get("port", 3306),
                username=mysql_cfg.get("username", "root"),
                password=mysql_cfg.get("password", ""),
                database=mysql_cfg.get("database", "pg-platform-db"),
                charset=mysql_cfg.get("charset", "utf8mb4"),
            )

    def count_roles(
        self,
        binding_user_id: int,
        keyword: Optional[str],
        status: Optional[int],
    ) -> Tuple[ErrorCode, int]:
        condition_parts: List[str] = []
        params: List[Any] = []
        condition_parts.append("binding_user_id = %s")
        params.append(int(binding_user_id))
        if keyword:
            condition_parts.append("name LIKE %s")
            params.append(f"%{keyword}%")
        if status is not None:
            condition_parts.append("status = %s")
            params.append(status)
        condition = " AND ".join(condition_parts) if condition_parts else None
        return self.mysql.count("application_role_tbl", condition=condition, params=tuple(params) if params else None)

    def list_roles(
        self,
        binding_user_id: int,
        keyword: Optional[str],
        status: Optional[int],
        limit: int,
        offset: int,
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        condition_parts: List[str] = []
        params: List[Any] = []
        condition_parts.append("binding_user_id = %s")
        params.append(int(binding_user_id))
        if keyword:
            condition_parts.append("name LIKE %s")
            params.append(f"%{keyword}%")
        if status is not None:
            condition_parts.append("status = %s")
            params.append(status)
        condition = " AND ".join(condition_parts) if condition_parts else None
        return self.mysql.select(
            "application_role_tbl",
            condition=condition,
            params=tuple(params) if params else None,
            order_by="upload_time DESC",
            limit=limit,
            offset=offset,
        )

    def get_role_by_id(self, role_id: int, binding_user_id: int) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        condition = "id = %s AND binding_user_id = %s"
        params = (role_id, int(binding_user_id))
        return self.mysql.select_one("application_role_tbl", condition=condition, params=params)

    def insert_role(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.mysql.insert("application_role_tbl", data)

    def update_role(self, role_id: int, binding_user_id: int, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        condition = "id = %s AND binding_user_id = %s"
        params = (role_id, int(binding_user_id))
        return self.mysql.update("application_role_tbl", data=data, condition=condition, params=params)

    def delete_role(self, role_id: int, binding_user_id: int) -> Tuple[ErrorCode, int]:
        condition = "id = %s AND binding_user_id = %s"
        params = (role_id, int(binding_user_id))
        return self.mysql.delete("application_role_tbl", condition=condition, params=params)

    def insert_role_relations(self, relations: List[Dict[str, Any]]) -> Tuple[ErrorCode, int]:
        if not relations:
            return ErrorCode.SUCCESS, 0
        return self.mysql.batch_insert("application_role_prompt_relation_tbl", relations)

    def delete_role_relations(self, role_id: int) -> Tuple[ErrorCode, int]:
        condition = "role_id = %s"
        params = (role_id,)
        return self.mysql.delete("application_role_prompt_relation_tbl", condition=condition, params=params)

    def get_role_relations(self, role_id: int) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        condition = "role_id = %s"
        params = (role_id,)
        return self.mysql.select("application_role_prompt_relation_tbl", condition=condition, params=params)
