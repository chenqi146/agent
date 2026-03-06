import json
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import hashlib

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.client.redis_client import RedisTemplete
from infrastructure.client.neo4j_client import Neo4jClient
from interfaces.dto.coordinator_dto import (
    SessionContext, BusinessContext, DomainKnowledgeContext, FullContext
)


@logger()
class ContextManager:
    """
    上下文管理服务
    管理三级上下文：会话级（Redis）、业务级（MySQL/Neo4j按需查询）、领域知识级（Neo4j实时查询）
    """
    
    def __init__(
        self, 
        config: Dict[str, Any],
        neo4j_client: Optional[Neo4jClient] = None,
        mysql_client = None
    ):
        self.config = config
        self._neo4j = neo4j_client
        self._mysql = mysql_client
        
        # 会话上下文配置
        self._session_ttl = config.get("context", {}).get("session_ttl", 1800)  # 30分钟
        self._max_history_turns = config.get("context", {}).get("max_history_turns", 5)
        self._context_prefix = "coordinator:session:"
        
        # 上下文配置缓存（从MySQL加载）
        self._config_cache = {}
        self._config_cache_ttl = 300  # 5分钟
        self._last_config_load = None
        
        self.log.info(f"ContextManager initialized: session_ttl={self._session_ttl}s, max_history={self._max_history_turns}")
    
    def _session_key(self, session_id: str) -> str:
        """生成Redis key"""
        return f"{self._context_prefix}{session_id}"
    
    async def load_session_context(self, session_id: str, user_id: int) -> Tuple[ErrorCode, Optional[SessionContext]]:
        """加载会话级上下文"""
        try:
            if not RedisTemplete.is_init:
                # Redis未初始化，返回空上下文
                self.log.warning("Redis not initialized, returning empty session context")
                return ErrorCode.SUCCESS, SessionContext(
                    session_id=session_id,
                    user_id=user_id,
                    ttl=self._session_ttl
                )
            
            key = self._session_key(session_id)
            data = RedisTemplete.get(key)
            
            if data:
                # 解析并刷新TTL
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                context_dict = json.loads(data)
                context_dict["updated_at"] = datetime.now().isoformat()
                
                # 刷新Redis TTL
                RedisTemplete.expire(key, self._session_ttl)
                
                return ErrorCode.SUCCESS, SessionContext(**context_dict)
            else:
                # 创建新会话上下文
                context = SessionContext(
                    session_id=session_id,
                    user_id=user_id,
                    ttl=self._session_ttl
                )
                return ErrorCode.SUCCESS, context
                
        except Exception as e:
            self.log.error(f"load_session_context failed: {e}")
            # 返回空上下文作为兜底
            return ErrorCode.SUCCESS, SessionContext(
                session_id=session_id,
                user_id=user_id,
                ttl=self._session_ttl
            )
    
    async def save_session_context(self, context: SessionContext) -> ErrorCode:
        """保存会话级上下文到Redis"""
        try:
            if not RedisTemplete.is_init:
                self.log.warning("Redis not initialized, cannot save session context")
                return ErrorCode.SUCCESS  # 静默失败
            
            key = self._session_key(context.session_id)
            context.updated_at = datetime.now().isoformat()
            
            # 限制历史对话长度
            if len(context.dialogue_history) > self._max_history_turns:
                context.dialogue_history = context.dialogue_history[-self._max_history_turns:]
            
            # 序列化并保存
            data = context.model_dump()
            RedisTemplete.set(key, json.dumps(data), self._session_ttl)
            
            return ErrorCode.SUCCESS
            
        except Exception as e:
            self.log.error(f"save_session_context failed: {e}")
            return ErrorCode.SYSTEM_ERROR
    
    async def update_dialogue_history(
        self, 
        session_id: str, 
        user_id: int,
        user_query: str, 
        system_response: str,
        intent: str = ""
    ) -> ErrorCode:
        """更新对话历史"""
        try:
            err, context = await self.load_session_context(session_id, user_id)
            if err != ErrorCode.SUCCESS:
                return err
            
            # 添加新对话轮次
            turn = {
                "timestamp": datetime.now().isoformat(),
                "user": user_query,
                "system": system_response,
                "intent": intent
            }
            context.dialogue_history.append(turn)
            
            # 维护意图栈
            if intent and intent not in context.intent_stack:
                context.intent_stack.append(intent)
                # 限制栈深度
                if len(context.intent_stack) > 10:
                    context.intent_stack = context.intent_stack[-10:]
            
            # 保存
            return await self.save_session_context(context)
            
        except Exception as e:
            self.log.error(f"update_dialogue_history failed: {e}")
            return ErrorCode.SYSTEM_ERROR
    
    async def get_business_context(
        self, 
        user_id: int, 
        intent: str, 
        entities: Dict[str, Any]
    ) -> Tuple[ErrorCode, BusinessContext]:
        """
        获取业务级上下文（按需从MySQL/Neo4j查询）
        """
        try:
            business_ctx = BusinessContext()
            
            # 获取用户上下文（从MySQL）
            if self._mysql:
                user_ctx = await self._load_user_context(user_id)
                business_ctx.user_context = user_ctx
            
            # 获取实体状态（从Neo4j）
            if self._neo4j and entities:
                entity_states = await self._load_entity_states(entities)
                business_ctx.entity_states = entity_states
            
            # 获取业务流程进度
            process_progress = await self._load_process_progress(user_id, intent)
            business_ctx.process_progress = process_progress
            
            # 系统上下文
            business_ctx.system_context = {
                "timestamp": datetime.now().isoformat(),
                "timezone": "Asia/Shanghai"
            }
            
            return ErrorCode.SUCCESS, business_ctx
            
        except Exception as e:
            self.log.error(f"get_business_context failed: {e}")
            return ErrorCode.SUCCESS, BusinessContext()  # 返回空上下文
    
    async def _load_user_context(self, user_id: int) -> Dict[str, Any]:
        """从MySQL加载用户上下文"""
        try:
            # TODO: 实现具体查询逻辑
            # 这里返回模拟数据
            return {
                "user_id": user_id,
                "role": "operator",
                "permissions": ["read", "write"],
                "department": "parking_management"
            }
        except Exception as e:
            self.log.warning(f"load_user_context failed: {e}")
            return {}
    
    async def _load_entity_states(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """从Neo4j加载实体状态"""
        try:
            if not self._neo4j:
                return {}
            
            states = {}
            
            # 检查车辆实体
            if "vehicle" in entities or "plate_number" in entities:
                plate = entities.get("vehicle", {}).get("plate_number") or entities.get("plate_number")
                if plate:
                    cypher = """
                    MATCH (v:Vehicle {plate_number: $plate})
                    OPTIONAL MATCH (v)-[:PARKED_AT]->(p:ParkingSpot)
                    RETURN v.status as status, p.location as location, 
                           v.entry_time as entry_time, v.parking_duration as duration
                    """
                    err, result = await asyncio.to_thread(
                        self._neo4j.execute_query, cypher, {"plate": plate}
                    )
                    if err == ErrorCode.SUCCESS and result:
                        states["vehicle"] = result[0]
            
            # 检查停车位实体
            if "parking_spot" in entities:
                spot_id = entities.get("parking_spot")
                cypher = """
                MATCH (p:ParkingSpot {id: $spot_id})
                RETURN p.status as status, p.type as type, 
                       p.hourly_rate as rate, p.occupied_by as occupied_by
                """
                err, result = await asyncio.to_thread(
                    self._neo4j.execute_query, cypher, {"spot_id": spot_id}
                )
                if err == ErrorCode.SUCCESS and result:
                    states["parking_spot"] = result[0]
            
            return states
            
        except Exception as e:
            self.log.warning(f"load_entity_states failed: {e}")
            return {}
    
    async def _load_process_progress(self, user_id: int, intent: str) -> Dict[str, Any]:
        """加载业务流程进度"""
        try:
            # TODO: 实现具体查询逻辑
            return {
                "current_step": "init",
                "completed_steps": [],
                "pending_steps": ["verify", "process", "confirm"]
            }
        except Exception as e:
            self.log.warning(f"load_process_progress failed: {e}")
            return {}
    
    async def get_domain_knowledge_context(
        self, 
        intent: str, 
        entities: Dict[str, Any],
        query: str
    ) -> Tuple[ErrorCode, DomainKnowledgeContext]:
        """
        获取领域知识上下文（从Neo4j实时查询）
        """
        try:
            domain_ctx = DomainKnowledgeContext()
            
            if not self._neo4j:
                return ErrorCode.SUCCESS, domain_ctx
            
            # 1. 查询本体关系图谱
            ontology_ctx = await self._query_ontology_context(intent, entities)
            domain_ctx.ontology_context = ontology_ctx
            
            # 2. 查询业务约束
            constraints = await self._query_constraints(intent)
            domain_ctx.constraint_context = constraints
            
            # 3. 查询历史案例
            historical = await self._query_historical_cases(intent, query)
            domain_ctx.historical_context = historical
            
            return ErrorCode.SUCCESS, domain_ctx
            
        except Exception as e:
            self.log.error(f"get_domain_knowledge_context failed: {e}")
            return ErrorCode.SUCCESS, DomainKnowledgeContext()
    
    async def _query_ontology_context(
        self, 
        intent: str, 
        entities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """查询本体关系图谱"""
        try:
            results = []
            
            # 根据意图查询相关本体
            if intent in ["city_parking", "vehicle_query"]:
                # 查询停车相关本体关系
                cypher = """
                MATCH (p:ParkingSpot)-[:LOCATED_IN]->(a:Area)
                OPTIONAL MATCH (p)-[:HAS_TYPE]->(t:SpotType)
                RETURN p.id as spot_id, a.name as area, t.name as type
                LIMIT 10
                """
                err, result = await asyncio.to_thread(
                    self._neo4j.execute_query, cypher
                )
                if err == ErrorCode.SUCCESS and result:
                    results.extend([{"type": "parking_ontology", "data": r} for r in result])
            
            elif intent == "steward":
                # 查询管家相关本体
                cypher = """
                MATCH (s:StewardFunction)-[:REQUIRES]->(d:Device)
                RETURN s.name as function, d.name as device, d.status as status
                LIMIT 10
                """
                err, result = await asyncio.to_thread(
                    self._neo4j.execute_query, cypher
                )
                if err == ErrorCode.SUCCESS and result:
                    results.extend([{"type": "steward_ontology", "data": r} for r in result])
            
            return results
            
        except Exception as e:
            self.log.warning(f"query_ontology_context failed: {e}")
            return []
    
    async def _query_constraints(self, intent: str) -> List[str]:
        """查询业务约束"""
        try:
            # 从Neo4j查询约束规则
            cypher = """
            MATCH (c:Constraint)-[:APPLIES_TO]->(i:Intent {name: $intent})
            RETURN c.description as description, c.severity as severity
            """
            err, result = await asyncio.to_thread(
                self._neo4j.execute_query, cypher, {"intent": intent}
            )
            
            if err == ErrorCode.SUCCESS and result:
                return [f"[{r.get('severity', 'info')}] {r.get('description', '')}" for r in result]
            
            # 返回默认约束
            default_constraints = {
                "city_parking": ["[warn] 需确认用户权限", "[info] 高峰时段可能需排队"],
                "steward": ["[warn] 需验证设备在线状态"],
                "vehicle_query": ["[info] 仅可查询授权车辆"]
            }
            return default_constraints.get(intent, [])
            
        except Exception as e:
            self.log.warning(f"query_constraints failed: {e}")
            return []
    
    async def _query_historical_cases(
        self, 
        intent: str, 
        query: str
    ) -> List[Dict[str, Any]]:
        """查询历史案例"""
        try:
            # 使用相似意图匹配历史案例
            cypher = """
            MATCH (case:Case)-[:SOLVED_BY]->(solution:Solution)
            WHERE case.intent = $intent
            RETURN case.query as query, case.outcome as outcome, 
                   solution.description as solution, case.created_at as time
            ORDER BY case.created_at DESC
            LIMIT 3
            """
            err, result = await asyncio.to_thread(
                self._neo4j.execute_query, cypher, {"intent": intent}
            )
            
            if err == ErrorCode.SUCCESS and result:
                return result
            
            return []
            
        except Exception as e:
            self.log.warning(f"query_historical_cases failed: {e}")
            return []
    
    async def confirm_slot(
        self, 
        session_id: str, 
        user_id: int,
        slot_name: str, 
        slot_value: Any
    ) -> ErrorCode:
        """确认槽位值"""
        try:
            err, context = await self.load_session_context(session_id, user_id)
            if err != ErrorCode.SUCCESS:
                return err
            
            context.confirmed_slots[slot_name] = slot_value
            return await self.save_session_context(context)
            
        except Exception as e:
            self.log.error(f"confirm_slot failed: {e}")
            return ErrorCode.SYSTEM_ERROR
    
    async def set_temp_variable(
        self, 
        session_id: str, 
        user_id: int,
        var_name: str, 
        var_value: Any
    ) -> ErrorCode:
        """设置临时变量"""
        try:
            err, context = await self.load_session_context(session_id, user_id)
            if err != ErrorCode.SUCCESS:
                return err
            
            context.temp_variables[var_name] = var_value
            return await self.save_session_context(context)
            
        except Exception as e:
            self.log.error(f"set_temp_variable failed: {e}")
            return ErrorCode.SYSTEM_ERROR
