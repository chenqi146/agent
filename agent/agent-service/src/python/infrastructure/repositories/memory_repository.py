from typing import Any, Dict, Optional, Tuple, List

from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.persistences.mysql_persistence import MysqlPersistence
from infrastructure.persistences.elasticsearch_persistence import ElasticsearchPersistence
from infrastructure.client.redis_client import RedisTemplete


@logger()
class MemoryRepository:
    """
    记忆配置仓储层，负责与 memory_config 表交互。
    """

    def __init__(
        self,
        config: SysConfig,
        mysql_client: Optional[MysqlPersistence] = None,
        es_client: Optional[ElasticsearchPersistence] = None,
    ):
        self.config = config
        self.mysql = mysql_client or self._create_mysql_client()
        self.es = es_client

    def _create_mysql_client(self) -> MysqlPersistence:
        """
        当未注入 mysql_client 时，根据配置创建一个新的 MysqlPersistence 实例。
        """
        system_cfg = self.config.get_system_config() or {}
        mysql_cfg = (system_cfg.get("persistence") or {}).get("mysql") or {}
        return MysqlPersistence(
            host=mysql_cfg.get("host", "127.0.0.1"),
            port=mysql_cfg.get("port", 3306),
            username=mysql_cfg.get("username", "root"),
            password=mysql_cfg.get("password", ""),
            database=mysql_cfg.get("database", "pg-platform-db"),
            charset=mysql_cfg.get("charset", "utf8mb4"),
        )

    def search_memory_docs(self, body: Dict[str, Any]) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        if self.es is None:
            return ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, None
        return self.es.search(body)

    def save_memory_doc(self, doc_id: str, document: Dict[str, Any]) -> Tuple[ErrorCode, Optional[object]]:
        if self.es is None:
            return ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, None
        return self.es.save_document(doc_id, document)

    def delete_memory_docs(self, ids: List[str]) -> Tuple[ErrorCode, Optional[object]]:
        if self.es is None:
            return ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, None
        return self.es.bulk_delete_by_ids(ids)

    def clear_memory_docs_by_agent(self, agent_id: int) -> Tuple[ErrorCode, Optional[object]]:
        if self.es is None:
            return ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, None
        query = {"query": {"term": {"agent_id": str(agent_id)}}}
        return self.es.delete_by_query(query)

    def get_active_config(
        self, agent_id: str, config_name: str = "default"
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """
        查询指定智能体的激活记忆配置。
        """
        try:
            binding_user_id = int(agent_id) if str(agent_id).isdigit() else 0
            condition = "binding_user_id = %s AND agent_id = %s AND config_name = %s AND is_active = 1"
            params = (binding_user_id, agent_id, config_name)
            return self.mysql.select_one("memory_config", condition=condition, params=params)
        except Exception:
            try:
                condition = "agent_id = %s AND config_name = %s AND is_active = 1"
                params = (agent_id, config_name)
                return self.mysql.select_one("memory_config", condition=condition, params=params)
            except Exception:
                return ErrorCode.SQL_SELECT_FAILED, None

    def insert_config(self, data: Dict[str, Any]) -> Tuple[ErrorCode, Optional[int]]:
        """
        插入一条新的记忆配置记录。
        """
        try:
            return self.mysql.insert("memory_config", data)
        except Exception:
            if "binding_user_id" in data:
                try:
                    data2 = dict(data)
                    data2.pop("binding_user_id", None)
                    return self.mysql.insert("memory_config", data2)
                except Exception:
                    return ErrorCode.SQL_INSERT_FAILED, None
            return ErrorCode.SQL_INSERT_FAILED, None

    def update_config_by_id(self, config_id: int, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        """
        根据主键 ID 更新记忆配置。
        """
        condition = "id = %s"
        params = (config_id,)
        try:
            return self.mysql.update("memory_config", data, condition=condition, params=params)
        except Exception:
            return ErrorCode.SQL_UPDATE_FAILED, 0

    def upsert_config(
        self, agent_id: str, config_name: str, data: Dict[str, Any]
    ) -> Tuple[ErrorCode, Optional[int]]:
        """
        按 (agent_id, config_name) 进行 upsert：
        - 若存在记录则更新；
        - 若不存在则插入。
        返回 (错误码, 记录ID)。
        """
        err, row = self.get_active_config(agent_id, config_name)
        if err != ErrorCode.SUCCESS and err != ErrorCode.SQL_SELECT_FAILED:
            return err, None

        # 记录不存在：插入
        if not row:
            insert_data = dict(data)
            insert_data.setdefault("agent_id", agent_id)
            insert_data.setdefault("config_name", config_name)
            insert_data.setdefault("is_active", 1)
            if "binding_user_id" not in insert_data:
                insert_data["binding_user_id"] = int(agent_id) if str(agent_id).isdigit() else 0
            return self.insert_config(insert_data)

        # 记录存在：更新
        config_id = row.get("id")
        if not config_id:
            return ErrorCode.DATA_INVALID, None
        update_data = dict(data)
        # agent_id、config_name 不允许被修改
        update_data.pop("agent_id", None)
        update_data.pop("config_name", None)
        err_u, _ = self.update_config_by_id(config_id, update_data)
        if err_u != ErrorCode.SUCCESS:
            return err_u, None
        return ErrorCode.SUCCESS, config_id

    def save_short_memory(self, key: str, value: Any, expire_seconds: int) -> Tuple[ErrorCode, Optional[object]]:
        try:
            if not RedisTemplete.is_init:
                return ErrorCode.REDIS_CLIENT_NOT_INIT, None
            RedisTemplete.set(key, value, expire_seconds)
            return ErrorCode.SUCCESS, None
        except Exception:
            return ErrorCode.EXTERNAL_SERVICE_ERROR, None

    def load_short_memory(self, key: str) -> Tuple[ErrorCode, Optional[Any]]:
        try:
            if not RedisTemplete.is_init:
                return ErrorCode.REDIS_CLIENT_NOT_INIT, None
            data = RedisTemplete.get(key)
            return ErrorCode.SUCCESS, data
        except Exception:
            return ErrorCode.EXTERNAL_SERVICE_ERROR, None

    def clear_short_memory(self, key: str) -> Tuple[ErrorCode, Optional[object]]:
        try:
            if not RedisTemplete.is_init:
                return ErrorCode.REDIS_CLIENT_NOT_INIT, None
            RedisTemplete.delete(key)
            return ErrorCode.SUCCESS, None
        except Exception:
            return ErrorCode.EXTERNAL_SERVICE_ERROR, None
