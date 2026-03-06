import uuid
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.client.redis_client import RedisTemplete
from interfaces.dto.coordinator_dto import TaskInfo, TaskStatus, TaskResult


@logger()
class TaskManager:
    """
    任务管理服务
    负责任务创建、状态管理、分配给规划智能体、结果汇总
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._task_ttl = config.get("task", {}).get("ttl", 3600)  # 1小时
        self._task_prefix = "coordinator:task:"
        self._session_tasks_prefix = "coordinator:session_tasks:"
        
        # 规划智能体注册表（从配置或数据库加载）
        self._planner_agents: Dict[str, Dict[str, Any]] = {}
        self._load_planner_agents()
        
        self.log.info(f"TaskManager initialized with {len(self._planner_agents)} planner agents")
    
    def _load_planner_agents(self):
        """加载规划智能体配置"""
        # 内置规划智能体配置
        self._planner_agents = {
            "city_parking": {
                "agent_id": "city_parking_agent",
                "agent_name": "城市停车管理智能体",
                "agent_type": "planning",
                "capabilities": ["parking_analysis", "task_guidance", "decision_support"],
                "supported_intents": ["city_parking", "parking_query", "vehicle_query"],
                "endpoint": None,  # 本地调用
                "timeout": 30000
            },
            "steward": {
                "agent_id": "steward_agent",
                "agent_name": "管家功能模块智能体",
                "agent_type": "planning",
                "capabilities": ["monitoring", "alerting", "patrol", "license_plate_recognition"],
                "supported_intents": ["steward", "monitor", "alert", "patrol"],
                "endpoint": None,
                "timeout": 30000
            }
        }
    
    def _task_key(self, task_id: str) -> str:
        """生成任务Redis key"""
        return f"{self._task_prefix}{task_id}"
    
    def _session_tasks_key(self, session_id: str) -> str:
        """生成会话任务列表Redis key"""
        return f"{self._session_tasks_prefix}{session_id}"
    
    async def create_task(
        self, 
        session_id: str,
        intent: str,
        task_type: str,
        parameters: Dict[str, Any],
        user_id: int
    ) -> Tuple[ErrorCode, Optional[TaskInfo]]:
        """创建新任务"""
        try:
            task_id = f"task_{uuid.uuid4().hex[:16]}"
            
            # 匹配规划智能体
            assigned_agent = self._match_planner_agent(intent)
            
            task = TaskInfo(
                task_id=task_id,
                session_id=session_id,
                task_type=task_type,
                intent=intent,
                parameters=parameters,
                assigned_agent=assigned_agent.get("agent_id") if assigned_agent else None,
                status=TaskStatus.PENDING
            )
            
            # 保存任务
            err = await self._save_task(task)
            if err != ErrorCode.SUCCESS:
                return err, None
            
            # 添加到会话任务列表
            err = await self._add_task_to_session(session_id, task_id)
            if err != ErrorCode.SUCCESS:
                self.log.warning(f"Failed to add task {task_id} to session {session_id}")
            
            self.log.info(f"Task created: {task_id} (intent={intent}, agent={task.assigned_agent})")
            return ErrorCode.SUCCESS, task
            
        except Exception as e:
            self.log.error(f"create_task failed: {e}")
            return ErrorCode.SYSTEM_ERROR, None
    
    def _match_planner_agent(self, intent: str) -> Optional[Dict[str, Any]]:
        """根据意图匹配规划智能体"""
        for agent_key, agent_config in self._planner_agents.items():
            if intent in agent_config.get("supported_intents", []):
                return agent_config
        
        # 默认返回城市停车智能体
        return self._planner_agents.get("city_parking")
    
    async def _save_task(self, task: TaskInfo) -> ErrorCode:
        """保存任务到Redis"""
        try:
            if not RedisTemplete.is_init:
                return ErrorCode.SUCCESS  # 静默失败，任务在内存中处理
            
            key = self._task_key(task.task_id)
            data = task.model_dump()
            RedisTemplete.set(key, json.dumps(data), self._task_ttl)
            
            return ErrorCode.SUCCESS
            
        except Exception as e:
            self.log.error(f"_save_task failed: {e}")
            return ErrorCode.SYSTEM_ERROR
    
    async def _add_task_to_session(self, session_id: str, task_id: str) -> ErrorCode:
        """将任务添加到会话任务列表"""
        try:
            if not RedisTemplete.is_init:
                return ErrorCode.SUCCESS
            
            key = self._session_tasks_key(session_id)
            # 使用Redis Set存储任务ID列表
            existing = RedisTemplete.get(key)
            
            if existing:
                if isinstance(existing, bytes):
                    existing = existing.decode('utf-8')
                task_list = json.loads(existing)
            else:
                task_list = []
            
            if task_id not in task_list:
                task_list.append(task_id)
                RedisTemplete.set(key, json.dumps(task_list), self._task_ttl)
            
            return ErrorCode.SUCCESS
            
        except Exception as e:
            self.log.error(f"_add_task_to_session failed: {e}")
            return ErrorCode.SYSTEM_ERROR
    
    async def get_task(self, task_id: str) -> Tuple[ErrorCode, Optional[TaskInfo]]:
        """获取任务信息"""
        try:
            if not RedisTemplete.is_init:
                return ErrorCode.DATA_NOT_FOUND, None
            
            key = self._task_key(task_id)
            data = RedisTemplete.get(key)
            
            if not data:
                return ErrorCode.DATA_NOT_FOUND, None
            
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            task_dict = json.loads(data)
            task = TaskInfo(**task_dict)
            
            return ErrorCode.SUCCESS, task
            
        except Exception as e:
            self.log.error(f"get_task failed: {e}")
            return ErrorCode.SYSTEM_ERROR, None
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus,
        result: Any = None,
        error_message: str = None,
        execution_time_ms: int = None
    ) -> ErrorCode:
        """更新任务状态"""
        try:
            err, task = await self.get_task(task_id)
            if err != ErrorCode.SUCCESS:
                return err
            
            task.status = status
            
            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.now().isoformat()
            
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now().isoformat()
            
            if result is not None:
                task.result = result
            
            if error_message:
                task.error_message = error_message
            
            if execution_time_ms:
                task.execution_time_ms = execution_time_ms
            
            return await self._save_task(task)
            
        except Exception as e:
            self.log.error(f"update_task_status failed: {e}")
            return ErrorCode.SYSTEM_ERROR
    
    async def get_session_tasks(
        self, 
        session_id: str,
        status: Optional[TaskStatus] = None
    ) -> Tuple[ErrorCode, List[TaskInfo]]:
        """获取会话的所有任务"""
        try:
            if not RedisTemplete.is_init:
                return ErrorCode.SUCCESS, []
            
            key = self._session_tasks_key(session_id)
            data = RedisTemplete.get(key)
            
            if not data:
                return ErrorCode.SUCCESS, []
            
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            task_ids = json.loads(data)
            tasks = []
            
            for task_id in task_ids:
                err, task = await self.get_task(task_id)
                if err == ErrorCode.SUCCESS and task:
                    if status is None or task.status == status:
                        tasks.append(task)
            
            # 按创建时间排序
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            
            return ErrorCode.SUCCESS, tasks
            
        except Exception as e:
            self.log.error(f"get_session_tasks failed: {e}")
            return ErrorCode.SYSTEM_ERROR, []
    
    async def cancel_task(self, task_id: str) -> ErrorCode:
        """取消任务"""
        return await self.update_task_status(task_id, TaskStatus.CANCELLED)
    
    async def aggregate_results(
        self, 
        session_id: str,
        task_ids: Optional[List[str]] = None
    ) -> Tuple[ErrorCode, Dict[str, Any]]:
        """汇总多个任务的结果"""
        try:
            if task_ids is None:
                # 获取会话所有已完成任务
                err, tasks = await self.get_session_tasks(session_id, TaskStatus.COMPLETED)
                if err != ErrorCode.SUCCESS:
                    return err, {}
                task_ids = [t.task_id for t in tasks]
            
            aggregated = {
                "session_id": session_id,
                "total_tasks": len(task_ids),
                "successful_tasks": 0,
                "failed_tasks": 0,
                "results": [],
                "summary": {}
            }
            
            for task_id in task_ids:
                err, task = await self.get_task(task_id)
                if err != ErrorCode.SUCCESS:
                    continue
                
                if task.status == TaskStatus.COMPLETED:
                    aggregated["successful_tasks"] += 1
                    aggregated["results"].append({
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                        "intent": task.intent,
                        "result": task.result,
                        "execution_time_ms": task.execution_time_ms
                    })
                elif task.status == TaskStatus.FAILED:
                    aggregated["failed_tasks"] += 1
                    aggregated["results"].append({
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                        "error": task.error_message
                    })
            
            # 生成汇总摘要
            aggregated["summary"] = self._generate_summary(aggregated["results"])
            
            return ErrorCode.SUCCESS, aggregated
            
        except Exception as e:
            self.log.error(f"aggregate_results failed: {e}")
            return ErrorCode.SYSTEM_ERROR, {}
    
    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成结果摘要"""
        summary = {
            "success_rate": 0.0,
            "avg_execution_time_ms": 0,
            "intent_distribution": {},
            "key_findings": []
        }
        
        if not results:
            return summary
        
        # 成功率
        successful = [r for r in results if "error" not in r]
        summary["success_rate"] = len(successful) / len(results)
        
        # 平均执行时间
        exec_times = [r.get("execution_time_ms", 0) for r in successful if r.get("execution_time_ms")]
        if exec_times:
            summary["avg_execution_time_ms"] = sum(exec_times) / len(exec_times)
        
        # 意图分布
        intent_counts = {}
        for r in results:
            intent = r.get("intent", "unknown")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        summary["intent_distribution"] = intent_counts
        
        return summary
    
    async def cleanup_session_tasks(self, session_id: str) -> ErrorCode:
        """清理会话的所有任务"""
        try:
            err, tasks = await self.get_session_tasks(session_id)
            if err != ErrorCode.SUCCESS:
                return err
            
            # 删除所有任务
            for task in tasks:
                key = self._task_key(task.task_id)
                if RedisTemplete.is_init:
                    RedisTemplete.delete(key)
            
            # 删除任务列表
            if RedisTemplete.is_init:
                key = self._session_tasks_key(session_id)
                RedisTemplete.delete(key)
            
            return ErrorCode.SUCCESS
            
        except Exception as e:
            self.log.error(f"cleanup_session_tasks failed: {e}")
            return ErrorCode.SYSTEM_ERROR
    
    def get_available_agents(self) -> List[Dict[str, Any]]:
        """获取可用的规划智能体列表"""
        return [
            {
                "agent_id": agent["agent_id"],
                "agent_name": agent["agent_name"],
                "agent_type": agent["agent_type"],
                "capabilities": agent["capabilities"],
                "supported_intents": agent["supported_intents"]
            }
            for agent in self._planner_agents.values()
        ]
