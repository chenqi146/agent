from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta
import json
import uuid

from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.repositories.memory_repository import MemoryRepository
from infrastructure.client.redis_client import RedisTemplete
from interfaces.dto.memory_dto import (
    MemoryConfig,
    MemoryContentItem,
    MemoryContentSearchRequest,
)


@logger()
class MemoryService:
    """
    记忆配置领域服务：
    - 负责从仓储中读取 / 保存 memory_config
    - 承担必要的业务校验（例如评分权重之和为 1）
    """

    def __init__(self, config: SysConfig, mysql_client=None, es_client=None):
        self.config = config
        self.repo = MemoryRepository(config, mysql_client, es_client)

    def _short_context_key(self, agent_id: int) -> str:
        return f"agent:{agent_id}:short_context"

    def _parse_time(self, value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.utcfromtimestamp(value)
            except Exception:
                return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return None
        return None

    def _build_default_config(self) -> MemoryConfig:
        """
        构造一份默认配置（与 SQL 中的默认值保持一致）。
        """
        return MemoryConfig(
            memory_half_life=24,
            auto_forget_enabled=True,
            importance_weight=0.4,
            freshness_weight=0.3,
            frequency_weight=0.3,
            compress_trigger_count=200,
            summary_style="compact_technical",
            context_max_count=20,
            context_retention_minutes=60,
            single_item_max_chars=500,
            important_context_to_long_term=True,
            description="默认记忆配置",
        )

    def get_memory_config(self, agent_id: int) -> Tuple[ErrorCode, Optional[MemoryConfig]]:
        """
        获取指定智能体的记忆配置。
        若无记录，返回默认配置（错误码为 SUCCESS）。
        """
        agent_key = str(agent_id)
        err, row = self.repo.get_active_config(agent_key, "default")
        if err != ErrorCode.SUCCESS and err != ErrorCode.SQL_SELECT_FAILED:
            return err, None

        if not row:
            return ErrorCode.SUCCESS, self._build_default_config()

        try:
            cfg = MemoryConfig(
                memory_half_life=int(row.get("memory_half_life", 24)),
                auto_forget_enabled=bool(row.get("auto_forget_enabled", 1)),
                importance_weight=float(row.get("importance_weight", 0.4)),
                freshness_weight=float(row.get("freshness_weight", 0.3)),
                frequency_weight=float(row.get("frequency_weight", 0.3)),
                compress_trigger_count=int(row.get("compress_trigger_count", 200)),
                summary_style=row.get("summary_style") or "compact_technical",
                context_max_count=int(row.get("context_max_count", 20)),
                context_retention_minutes=int(row.get("context_retention_minutes", 60)),
                single_item_max_chars=int(row.get("single_item_max_chars", 500)),
                important_context_to_long_term=bool(
                    row.get("important_context_to_long_term", 1)
                ),
                description=row.get("description"),
            )
            return ErrorCode.SUCCESS, cfg
        except Exception:
            return ErrorCode.DATA_INVALID, None

    def _validate_weights(self, cfg: MemoryConfig) -> Tuple[ErrorCode, Optional[str]]:
        """
        校验评分权重之和是否为 1。
        """
        total = (
            float(cfg.importance_weight)
            + float(cfg.freshness_weight)
            + float(cfg.frequency_weight)
        )
        if abs(total - 1.0) > 1e-3:
            return (
                ErrorCode.INVALID_PARAMETER,
                "重要性、新鲜度、出现频次三项权重之和必须为 1",
            )
        return ErrorCode.SUCCESS, None

    def save_memory_config(
        self, agent_id: int, cfg: MemoryConfig
    ) -> Tuple[ErrorCode, Optional[object]]:
        """
        保存记忆配置：
        - 校验权重
        - 将配置写入 memory_config（upsert）
        """
        err, msg = self._validate_weights(cfg)
        if err != ErrorCode.SUCCESS:
            return err, msg

        agent_key = str(agent_id)
        data = {
            "agent_id": agent_key,
            "config_name": "default",
            "memory_half_life": int(cfg.memory_half_life),
            "auto_forget_enabled": 1 if cfg.auto_forget_enabled else 0,
            "importance_weight": float(cfg.importance_weight),
            "freshness_weight": float(cfg.freshness_weight),
            "frequency_weight": float(cfg.frequency_weight),
            "compress_trigger_count": int(cfg.compress_trigger_count),
            "summary_style": cfg.summary_style,
            "context_max_count": int(cfg.context_max_count),
            "context_retention_minutes": int(cfg.context_retention_minutes),
            "single_item_max_chars": int(cfg.single_item_max_chars),
            "important_context_to_long_term": 1
            if cfg.important_context_to_long_term
            else 0,
            "is_active": 1,
            "description": cfg.description or "",
        }

        err_u, _ = self.repo.upsert_config(agent_key, "default", data)
        if err_u != ErrorCode.SUCCESS:
            return err_u, None
        return ErrorCode.SUCCESS, cfg

    def _build_time_range(self, time_range: str) -> Optional[str]:
        if time_range == "all":
            return None
        now = datetime.utcnow()
        if time_range == "last1d":
            delta = timedelta(days=1)
        elif time_range == "last7d":
            delta = timedelta(days=7)
        elif time_range == "last30d":
            delta = timedelta(days=30)
        elif time_range == "last90d":
            delta = timedelta(days=90)
        else:
            return None
        start = now - delta
        # Ensure time format is consistent with ES index mapping (yyyy-MM-dd HH:mm:ss)
        return start.strftime("%Y-%m-%d %H:%M:%S")

    def search_memory_content(
        self, agent_id: int, cond: MemoryContentSearchRequest
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        must: List[Dict[str, Any]] = [
            {"term": {"agent_id": str(agent_id)}},
        ]

        from_time = self._build_time_range(cond.time_range)
        if from_time is not None:
            must.append({"range": {"time": {"gte": from_time}}})

        if cond.category and cond.category != "all":
            must.append({"term": {"category": cond.category}})

        if cond.role_type and cond.role_type != "all":
            must.append({"term": {"role_type": cond.role_type}})

        if cond.keyword:
            must.append(
                {
                    "multi_match": {
                        "query": cond.keyword,
                        "fields": ["fact^2", "detail"],
                    }
                }
            )

        body: Dict[str, Any] = {
            "query": {"bool": {"must": must}},
            "sort": [{"time": {"order": "desc"}}],
            "from": (cond.page - 1) * cond.page_size,
            "size": cond.page_size,
        }
        err, resp = self.repo.search_memory_docs(body)
        if err != ErrorCode.SUCCESS or not resp:
            return err, None
        hits = resp.get("hits", {}) or {}
        total_val = hits.get("total", 0)
        if isinstance(total_val, dict):
            total = int(total_val.get("value", 0) or 0)
        else:
            total = int(total_val or 0)

        items: List[MemoryContentItem] = []
        for hit in hits.get("hits", []):
            src = hit.get("_source") or {}
            doc_id = hit.get("_id")
            t = src.get("time") or src.get("created_at")
            if isinstance(t, (int, float)):
                dt = datetime.utcfromtimestamp(t)
                t_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(t, str):
                t_str = t
            else:
                t_str = ""

            item = MemoryContentItem(
                id=str(doc_id),
                time=t_str,
                category=src.get("category") or "system",
                role_type=src.get("role_type") or "all",
                fact=src.get("fact") or "",
                detail=src.get("detail") or "",
            )
            items.append(item)

        data = {
            "total": total,
            "items": [i.model_dump(by_alias=True) for i in items],
        }
        return ErrorCode.SUCCESS, data

    def add_memory(
        self,
        agent_id: int,
        query: str,
        response: str
    ) -> Tuple[ErrorCode, Optional[str]]:
        """
        保存一次对话记忆
        """
        if not query and not response:
            return ErrorCode.INVALID_PARAMETER, None
            
        doc_id = str(uuid.uuid4())
        now = datetime.utcnow()
        # Ensure time format is consistent with ES index mapping (yyyy-MM-dd HH:mm:ss)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        doc = {
            "agent_id": str(agent_id),
            "time": now_str,
            "category": "conversation",
            "role_type": "all",
            "fact": query,
            "detail": response,
            "created_at": now_str
        }
        
        err, _ = self.repo.save_memory_doc(doc_id, doc)
        if err != ErrorCode.SUCCESS:
            return err, None
            
        return ErrorCode.SUCCESS, doc_id

    def delete_memory_content(
        self, agent_id: int, ids: List[str]
    ) -> Tuple[ErrorCode, Optional[object]]:
        if not ids:
            return ErrorCode.SUCCESS, None
        err, _ = self.repo.delete_memory_docs(ids)
        return err, None

    def clear_memory_content(self, agent_id: int) -> Tuple[ErrorCode, Optional[object]]:
        err, _ = self.repo.clear_memory_docs_by_agent(agent_id)
        return err, None

    def build_short_context(
        self,
        agent_id: int,
        messages: List[Dict[str, Any]],
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """
        根据 memory_config 中的上下文短记忆配置，从完整对话消息列表中
        计算出当前轮需要携带的短期上下文窗口。

        约定每条 message 至少包含字段：
        - role: "user" / "assistant" / "system" 等
        - content: 文本内容
        - time: 可选，datetime / 时间戳 / ISO 字符串，用于按保留时长过滤

        返回按时间升序排列的短期上下文列表。
        """
        if not messages:
            return ErrorCode.SUCCESS, []

        err, cfg = self.get_memory_config(agent_id)
        if err != ErrorCode.SUCCESS or cfg is None:
            return err, []

        now = datetime.utcnow()
        retention_delta = timedelta(minutes=int(cfg.context_retention_minutes))

        filtered: List[Dict[str, Any]] = []
        for msg in messages:
            t_raw = msg.get("time")
            dt = self._parse_time(t_raw) if t_raw is not None else None
            if dt is not None:
                if now - dt > retention_delta:
                    continue
            filtered.append(msg)

        filtered.sort(key=lambda m: self._parse_time(m.get("time")) or now)

        if len(filtered) > cfg.context_max_count:
            filtered = filtered[-cfg.context_max_count :]

        result: List[Dict[str, Any]] = []
        max_chars = int(cfg.single_item_max_chars)
        for msg in filtered:
            content = msg.get("content")
            if isinstance(content, str) and len(content) > max_chars:
                truncated = content[:max_chars]
            else:
                truncated = content
            copy_msg = dict(msg)
            copy_msg["content"] = truncated
            result.append(copy_msg)

        try:
            key = self._short_context_key(agent_id)
            ttl = int(cfg.context_retention_minutes) * 60
            RedisTemplete.set(key, json.dumps(result, ensure_ascii=False), ttl)
        except Exception as e:
            self.log.warning("save short context to redis failed: %s", e)

        return ErrorCode.SUCCESS, result

    def load_short_context(self, agent_id: int) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        try:
            key = self._short_context_key(agent_id)
            raw = RedisTemplete.get(key)
            if not raw:
                return ErrorCode.SUCCESS, []
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return ErrorCode.SUCCESS, data
            return ErrorCode.SUCCESS, []
        except Exception as e:
            self.log.error("load_short_context error: %s", e, exc_info=True)
            return ErrorCode.EXTERNAL_SERVICE_ERROR, []
