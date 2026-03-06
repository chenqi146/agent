from typing import Any, Dict, List, Optional, Tuple

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.config.sys_config import SysConfig
from infrastructure.persistences.mysql_persistence import MysqlPersistence


@logger()
class PromptRepository:
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

    def count_templates(
        self,
        creator_id: int,
        keyword: Optional[str],
        status: Optional[int],
    ) -> Tuple[ErrorCode, int]:
        condition_parts: List[str] = ["creator_id = %s"]
        params: List[Any] = [creator_id]
        if keyword:
            condition_parts.append("template_name LIKE %s")
            params.append(f"%{keyword}%")
        if status is not None:
            condition_parts.append("status = %s")
            params.append(status)
        condition = " AND ".join(condition_parts)
        return self.mysql.count("prompt_template", condition=condition, params=tuple(params))

    def list_templates(
        self,
        creator_id: int,
        keyword: Optional[str],
        status: Optional[int],
        limit: int,
        offset: int,
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        condition_parts: List[str] = ["creator_id = %s"]
        params: List[Any] = [creator_id]
        if keyword:
            condition_parts.append("template_name LIKE %s")
            params.append(f"%{keyword}%")
        if status is not None:
            condition_parts.append("status = %s")
            params.append(status)
        condition = " AND ".join(condition_parts)
        return self.mysql.select(
            "prompt_template",
            condition=condition,
            params=tuple(params),
            order_by="created_at DESC",
            limit=limit,
            offset=offset,
        )

    def get_template_by_id(
        self,
        template_id: int,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        condition = "id = %s AND creator_id = %s"
        params = (template_id, creator_id)
        return self.mysql.select_one("prompt_template", condition=condition, params=params)

    def insert_template(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.mysql.insert("prompt_template", data)

    def update_template(self, template_id: int, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        condition = "id = %s"
        params = (template_id,)
        return self.mysql.update("prompt_template", data=data, condition=condition, params=params)

    def delete_template(self, template_id: int, creator_id: int) -> Tuple[ErrorCode, int]:
        condition = "id = %s AND creator_id = %s"
        params = (template_id, creator_id)
        return self.mysql.delete("prompt_template", condition=condition, params=params)

    def insert_variables(self, template_id: int, rows: List[Dict[str, Any]]) -> Tuple[ErrorCode, int]:
        if not rows:
            return ErrorCode.SUCCESS, 0
        for row in rows:
            row.setdefault("template_id", template_id)
        return self.mysql.batch_insert("prompt_variable", rows)

    def get_prompt_constant(
        self,
        user_id: int,
        application_type: str,
        prompt_type: str,
        current_time: Optional[str] = None
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """
        根据用户ID、应用类型、prompt类型获取prompt
        当前表结构不支持时间范围查询，忽略current_time参数
        """
        # 简化查询 - 只根据用户ID、应用类型和prompt类型查询
        condition = "user_id = %s AND application_type = %s AND type = %s"
        params = (user_id, application_type, prompt_type)
        
        err, row = self.mysql.select_one("prompt_constant_tbl", condition=condition, params=params)
        if err != ErrorCode.SUCCESS:
            return err, None
        return ErrorCode.SUCCESS, row

    def get_prompt_constant_at_time(
        self,
        user_id: int,
        application_type: str,
        prompt_type: str,
        at_time: str
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """
        获取在指定时间点有效的prompt
        当前表结构不支持时间范围查询，直接返回最新的匹配记录
        """
        # 表结构简化查询 - 只根据用户ID、应用类型和prompt类型查询
        condition = "user_id = %s AND application_type = %s AND type = %s"
        params = (user_id, application_type, prompt_type)
        
        err, row = self.mysql.select_one("prompt_constant_tbl", condition=condition, params=params)
        if err != ErrorCode.SUCCESS:
            return err, None
        return ErrorCode.SUCCESS, row

    def delete_variables_by_template(self, template_id: int) -> Tuple[ErrorCode, int]:
        condition = "template_id = %s"
        params = (template_id,)
        return self.mysql.delete("prompt_variable", condition=condition, params=params)

    def list_variables_by_template(self, template_id: int) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        condition = "template_id = %s"
        params = (template_id,)
        return self.mysql.select(
            "prompt_variable",
            condition=condition,
            params=params,
            order_by="sort_order ASC, id ASC",
        )

    def insert_test(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.mysql.insert("prompt_test", data)

    def insert_ab_test(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.mysql.insert("prompt_ab_test", data)

    def insert_batch_test(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.mysql.insert("prompt_batch_test", data)

    def batch_insert_test_cases(self, rows: List[Dict[str, Any]]) -> Tuple[ErrorCode, int]:
        if not rows:
            return ErrorCode.SUCCESS, 0
        return self.mysql.batch_insert("prompt_test_case", rows)

    def get_test_by_id(self, test_id: int) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        condition = "id = %s"
        params = (test_id,)
        return self.mysql.select_one("prompt_test", condition=condition, params=params)

    def update_test(self, test_id: int, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        condition = "id = %s"
        params = (test_id,)
        return self.mysql.update("prompt_test", data, condition, params)

