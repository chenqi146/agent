"""
Planning Agent Controller
规划智能体控制器
提供RESTful API接口
"""
from typing import Any, Dict
from fastapi import Depends, FastAPI
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.config.sys_config import SysConfig
from infrastructure.persistences.mysql_persistence import MysqlPersistence

from interfaces.dto.planning_agent_dto import (
    ApiResponse,
    CreatePlanningSessionApiRequest,
    ExecutePlanningApiRequest,
    GetPlanningStatusApiRequest,
    UpdateTaskStatusApiRequest,
    CreatePlanningSessionRequest,
    ExecutePlanningRequest,
    GetPlanningStatusRequest,
    UpdateTaskStatusRequest
)

from domain.service.planning_agent_service import PlanningAgentService


@logger()
class PlanningAgentController:
    """规划智能体控制器"""
    
    def __init__(
        self,
        app: FastAPI,
        config: SysConfig,
        mysql_client: MysqlPersistence,
        planning_service: PlanningAgentService = None
    ):
        self.app = app
        self.config = config
        self.mysql = mysql_client
        self.planning_service = planning_service or PlanningAgentService(config, mysql_client)
        self._register_routes()
    
    def _ok(self, data: Any = None) -> Dict:
        """成功响应"""
        return ApiResponse(code=0, message="success", data=data).model_dump()
    
    def _fail(self, code: ErrorCode, message: str = "", data: Any = None) -> Dict:
        """失败响应"""
        return ApiResponse(
            code=code.value if isinstance(code, ErrorCode) else code,
            message=message or "error",
            data=data
        ).model_dump()
    
    def _register_routes(self):
        """注册路由"""
        
        # 1. 创建规划会话
        @self.app.post("/api/v1/planning/session/create", response_model=ApiResponse)
        async def create_session(request: CreatePlanningSessionApiRequest):
            """
            创建规划会话
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "user_id": 1,
                    "agent_type": "parking_billing",
                    "goal": "处理停车场A今天的所有停车计费事件",
                    "initial_context": {
                        "parking_lot_id": "A001",
                        "date": "2026-03-04"
                    }
                }
            }
            """
            try:
                self.log.info(f"【创建规划会话】用户 {request.data.user_id} 请求创建 {request.data.agent_type.value} 会话")
                
                err, result = await self.planning_service.create_session(request.data)
                
                if err == ErrorCode.SUCCESS:
                    self.log.info(f"【创建规划会话】成功，会话ID: {result.session_id}")
                    return self._ok(result.model_dump())
                else:
                    self.log.error(f"【创建规划会话】失败: {err}")
                    return self._fail(err, "创建规划会话失败")
                    
            except Exception as e:
                self.log.error(f"【创建规划会话】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
        
        # 2. 执行规划
        @self.app.post("/api/v1/planning/execute", response_model=ApiResponse)
        async def execute_planning(request: ExecutePlanningApiRequest):
            """
            执行规划
            
            触发完整的规划流程：
            1. 目标拆解
            2. 依赖分析
            3. 工具匹配
            4. 任务清单生成
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "session_id": "plan_abc123",
                    "user_id": 1
                }
            }
            """
            try:
                self.log.info(f"【执行规划】会话 {request.data.session_id} 开始规划")
                
                err, result = await self.planning_service.execute_planning(request.data)
                
                if err == ErrorCode.SUCCESS:
                    self.log.info(f"【执行规划】会话 {request.data.session_id} 规划完成，生成 {len(result.tasks)} 个任务")
                    return self._ok(result.model_dump())
                else:
                    self.log.error(f"【执行规划】会话 {request.data.session_id} 规划失败: {err}")
                    return self._fail(err, "执行规划失败")
                    
            except Exception as e:
                self.log.error(f"【执行规划】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
        
        # 3. 执行计划（运行生成的任务）
        @self.app.post("/api/v1/planning/execute_plan", response_model=ApiResponse)
        async def execute_plan(request: ExecutePlanningApiRequest):
            """
            执行已规划好的计划
            
            执行生成的任务清单，触发执行引擎
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "session_id": "plan_abc123",
                    "user_id": 1
                }
            }
            """
            try:
                self.log.info(f"【执行计划】会话 {request.data.session_id} 开始执行计划")
                
                err, result = await self.planning_service.execute_plan(request.data.session_id)
                
                if err == ErrorCode.SUCCESS:
                    success_count = len([r for r in result.get("execution_results", []) if r.get("status") == "completed"])
                    total_count = len(result.get("execution_results", []))
                    self.log.info(f"【执行计划】会话 {request.data.session_id} 执行完成，成功 {success_count}/{total_count}")
                    return self._ok(result)
                else:
                    self.log.error(f"【执行计划】会话 {request.data.session_id} 执行失败: {err}")
                    return self._fail(err, "执行计划失败")
                    
            except Exception as e:
                self.log.error(f"【执行计划】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
        
        # 4. 获取规划状态
        @self.app.post("/api/v1/planning/session/status", response_model=ApiResponse)
        async def get_session_status(request: GetPlanningStatusApiRequest):
            """
            获取规划会话状态
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "session_id": "plan_abc123"
                }
            }
            """
            try:
                err, result = await self.planning_service.get_session_status(request.data.session_id)
                
                if err == ErrorCode.SUCCESS:
                    return self._ok(result.model_dump() if result else None)
                else:
                    return self._fail(err, "获取规划状态失败")
                    
            except Exception as e:
                self.log.error(f"【获取规划状态】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
        
        # 5. 列出用户的规划会话
        @self.app.post("/api/v1/planning/sessions/list", response_model=ApiResponse)
        async def list_sessions(request: Dict[str, Any]):
            """
            列出用户的规划会话
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "user_id": 1,
                    "agent_type": "parking_billing",  # 可选
                    "status": "planning",  # 可选
                    "limit": 10,
                    "offset": 0
                }
            }
            """
            try:
                data = request.get("data", {})
                user_id = data.get("user_id", 0)
                agent_type = data.get("agent_type")
                status = data.get("status")
                limit = data.get("limit", 10)
                offset = data.get("offset", 0)
                
                err, rows = await self._run_in_thread(
                    self.planning_service.repo.list_user_planning_sessions,
                    user_id,
                    agent_type,
                    status,
                    limit,
                    offset
                )
                
                if err == ErrorCode.SUCCESS:
                    sessions = [{
                        "session_id": r.get("session_id"),
                        "agent_type": r.get("agent_type"),
                        "goal": r.get("goal"),
                        "status": r.get("status"),
                        "created_at": r.get("created_at").isoformat() if r.get("created_at") else None
                    } for r in rows]
                    return self._ok({"sessions": sessions, "total": len(sessions)})
                else:
                    return self._fail(err, "列出规划会话失败")
                    
            except Exception as e:
                self.log.error(f"【列出规划会话】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
        
        # 6. 获取任务DAG
        @self.app.post("/api/v1/planning/session/tasks", response_model=ApiResponse)
        async def get_session_tasks(request: GetPlanningStatusApiRequest):
            """
            获取会话的任务DAG
            
            返回任务列表及其依赖关系
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "session_id": "plan_abc123"
                }
            }
            """
            try:
                err, rows = await self._run_in_thread(
                    self.planning_service.repo.list_session_tasks,
                    request.data.session_id
                )
                
                if err == ErrorCode.SUCCESS:
                    tasks = [{
                        "task_id": r.get("task_id"),
                        "task_name": r.get("task_name"),
                        "task_type": r.get("task_type"),
                        "status": r.get("status"),
                        "dependencies": r.get("dependencies", []),
                        "is_critical_path": r.get("is_critical_path"),
                        "execution_order": r.get("execution_order"),
                        "parallel_group": r.get("parallel_group")
                    } for r in rows]
                    return self._ok({"tasks": tasks})
                else:
                    return self._fail(err, "获取任务列表失败")
                    
            except Exception as e:
                self.log.error(f"【获取任务列表】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
        
        # 7. 更新任务状态（用于外部执行器回调）
        @self.app.post("/api/v1/planning/task/update", response_model=ApiResponse)
        async def update_task_status(request: UpdateTaskStatusApiRequest):
            """
            更新任务状态
            
            由外部执行器调用，更新任务执行结果
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "session_id": "plan_abc123",
                    "task_id": "task_001",
                    "status": "completed",
                    "output_data": {
                        "result": "...",
                        "execution_time_ms": 1500
                    }
                }
            }
            """
            try:
                data = request.data
                
                update_data = {
                    "status": data.status.value,
                    "completed_at": datetime.now() if data.status in ["completed", "failed"] else None
                }
                
                if data.output_data:
                    update_data["output_data"] = data.output_data
                
                if data.error_info:
                    update_data["error_info"] = data.error_info
                
                err, _ = await self._run_in_thread(
                    self.planning_service.repo.update_task,
                    data.session_id,
                    data.task_id,
                    update_data
                )
                
                if err == ErrorCode.SUCCESS:
                    self.log.info(f"【更新任务状态】会话 {data.session_id} 任务 {data.task_id} 更新为 {data.status.value}")
                    return self._ok({"updated": True})
                else:
                    return self._fail(err, "更新任务状态失败")
                    
            except Exception as e:
                self.log.error(f"【更新任务状态】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
        
        # 8. 获取策略知识库
        @self.app.post("/api/v1/planning/knowledge/query", response_model=ApiResponse)
        async def query_strategy_knowledge(request: Dict[str, Any]):
            """
            查询策略知识库
            
            获取规划智能体的策略知识
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "agent_type": "parking_billing",
                    "scenario_type": "billing_exception"  # 可选
                }
            }
            """
            try:
                data = request.get("data", {})
                agent_type = data.get("agent_type", "")
                scenario_type = data.get("scenario_type")
                
                err, knowledge_list = await self.planning_service.query_strategy_knowledge(
                    agent_type,
                    scenario_type
                )
                
                if err == ErrorCode.SUCCESS:
                    return self._ok({
                        "knowledge_list": [k.model_dump() for k in knowledge_list]
                    })
                else:
                    return self._fail(err, "查询策略知识失败")
                    
            except Exception as e:
                self.log.error(f"【查询策略知识】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
        
        # 9. 获取执行轨迹和经验
        @self.app.post("/api/v1/planning/session/trajectory", response_model=ApiResponse)
        async def get_execution_trajectory(request: GetPlanningStatusApiRequest):
            """
            获取执行轨迹和经验分析
            
            返回会话的执行轨迹、成功模式、失败教训和优化建议
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "session_id": "plan_abc123"
                }
            }
            """
            try:
                # 获取执行轨迹
                err, trajectory = await self._run_in_thread(
                    self.planning_service.repo.get_execution_trajectory,
                    request.data.session_id
                )
                
                if err == ErrorCode.SUCCESS and trajectory:
                    return self._ok({
                        "trajectory_id": trajectory.get("trajectory_id"),
                        "success_patterns": trajectory.get("success_patterns", []),
                        "failure_lessons": trajectory.get("failure_lessons", []),
                        "optimization_suggestions": trajectory.get("optimization_suggestions", []),
                        "strategy_update_needed": trajectory.get("strategy_update_needed", False),
                        "created_at": trajectory.get("created_at").isoformat() if trajectory.get("created_at") else None
                    })
                else:
                    # 如果没有轨迹，尝试重新提取
                    err, result = await self.planning_service.extract_experience(request.data.session_id)
                    if err == ErrorCode.SUCCESS:
                        return self._ok(result)
                    return self._ok({"message": "暂无执行轨迹数据"})
                    
            except Exception as e:
                self.log.error(f"【获取执行轨迹】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
        
        # 10. 获取规划中间态
        @self.app.post("/api/v1/planning/session/intermediate", response_model=ApiResponse)
        async def get_intermediate_state(request: Dict[str, Any]):
            """
            获取规划中间态
            
            查看规划过程中的各个阶段状态
            
            请求示例：
            {
                "tag": "optional",
                "timestamp": 1234567890,
                "data": {
                    "session_id": "plan_abc123",
                    "stage": "decomposition"  # parsing/decomposition/dependency_analysis/tool_matching/task_generation
                }
            }
            """
            try:
                data = request.get("data", {})
                session_id = data.get("session_id", "")
                stage = data.get("stage", "")
                
                err, state = await self._run_in_thread(
                    self.planning_service.repo.get_intermediate_state,
                    session_id,
                    stage
                )
                
                if err == ErrorCode.SUCCESS and state:
                    return self._ok({
                        "session_id": session_id,
                        "stage": stage,
                        "state_data": state.get("state_data"),
                        "reasoning_chain": state.get("reasoning_chain"),
                        "conflicts_detected": state.get("conflicts_detected"),
                        "resolutions": state.get("resolutions"),
                        "created_at": state.get("created_at").isoformat() if state.get("created_at") else None
                    })
                else:
                    return self._ok({"message": "未找到中间态数据"})
                    
            except Exception as e:
                self.log.error(f"【获取中间态】异常: {e}")
                return self._fail(ErrorCode.SYSTEM_ERROR, str(e))
    
    async def _run_in_thread(self, func, *args):
        """在线程池中运行阻塞操作"""
        import asyncio
        return await asyncio.to_thread(func, *args)


from datetime import datetime
