from fastapi import FastAPI, Depends
import time
import traceback

from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

from interfaces.dto.response_dto import ApiResponse, ok, fail
from interfaces.deps.user_context import UserContext, get_validated_user_context
from interfaces.controller.base_controller import BaseController
from interfaces.dto.coordinator_dto import (
    CoordinateApiRequest, CoordinateResponse,
    TaskQueryApiRequest, TaskQueryRequest, TaskStatus,
    SessionQueryApiRequest, SessionQueryRequest,
    BatchTaskRequest
)
from domain.service.agent_coordinator import AgentCoordinator


@logger()
class CoordinatorController(BaseController):
    """
    协调智能体控制器
    提供意图识别、上下文管理、任务管理、会话管理等接口
    """

    def __init__(
        self, 
        config: SysConfig, 
        web_app: FastAPI, 
        coordinator: AgentCoordinator
    ):
        self.config = config
        self.app = web_app
        self.coordinator = coordinator
        self._start_time = time.time()
        self._app_name = "pg-agent-coordinator"
        self._version = self._get_version_from_config()
        
        self._register_routes()

    def _get_version_from_config(self) -> str:
        """从配置中获取版本号"""
        try:
            system_config = self.config.get_system_config()
            return system_config.get("version", "1.0.0")
        except Exception:
            return "1.0.0"

    def _register_routes(self):
        """注册协调智能体相关路由"""

        @self.app.post("/v1/agent/coordinator/coordinate", response_model=ApiResponse)
        async def coordinate(
            request: CoordinateApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """
            协调智能体主入口
            
            执行流程：
            - 深度思考模式（deep_thinking=true）：意图识别 → 上下文构建 → 任务创建 → 任务分发 → 结果汇总
            - 简化模式（deep_thinking=false）：意图识别 → 记忆/RAG检索 → 直接LLM响应 → 保存记忆
            """
            try:
                user_id = int(user_ctx.user_id)
                data = request.data
                data.user_id = user_id
                
                err, result = await self.coordinator.coordinate(data)
                
                if err == ErrorCode.SUCCESS:
                    return ok(result.model_dump() if hasattr(result, "model_dump") else result)
                else:
                    return fail(err, "协调失败")
                    
            except Exception as e:
                self.log.error(f"coordinate error: {e}\n{traceback.format_exc()}")
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/coordinator/session/status", response_model=ApiResponse)
        async def get_session_status(
            request: SessionQueryApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """获取会话状态和任务列表"""
            try:
                data = request.data
                result = await self.coordinator.get_session_status(data.session_id)
                
                if "error" in result:
                    return fail(ErrorCode.SYSTEM_ERROR, result["error"])
                
                return ok(result)
                
            except Exception as e:
                self.log.error(f"get_session_status error: {e}\n{traceback.format_exc()}")
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/coordinator/tasks/query", response_model=ApiResponse)
        async def query_tasks(
            request: TaskQueryApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """查询任务"""
            try:
                data = request.data
                
                if data.task_id:
                    # 查询单个任务
                    err, result = await self.coordinator.get_task_result(data.task_id)
                    if err == ErrorCode.SUCCESS:
                        return ok(result.model_dump() if hasattr(result, "model_dump") else result)
                    else:
                        return fail(err, "任务不存在")
                
                elif data.session_id:
                    # 查询会话的所有任务
                    err, tasks = await self.coordinator.task_manager.get_session_tasks(
                        data.session_id, 
                        status=data.status
                    )
                    if err == ErrorCode.SUCCESS:
                        return ok({
                            "session_id": data.session_id,
                            "tasks": [t.model_dump() for t in tasks],
                            "total": len(tasks)
                        })
                    else:
                        return fail(err, "查询失败")
                
                else:
                    return fail(ErrorCode.INVALID_PARAMETER, "task_id 或 session_id 必填其一")
                
            except Exception as e:
                self.log.error(f"query_tasks error: {e}\n{traceback.format_exc()}")
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/coordinator/tasks/cancel", response_model=ApiResponse)
        async def cancel_task(
            request: TaskQueryApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """取消任务"""
            try:
                data = request.data
                
                if not data.task_id:
                    return fail(ErrorCode.INVALID_PARAMETER, "task_id 不能为空")
                
                err = await self.coordinator.task_manager.cancel_task(data.task_id)
                
                if err == ErrorCode.SUCCESS:
                    return ok({"message": "任务已取消", "task_id": data.task_id})
                else:
                    return fail(err, "取消任务失败")
                
            except Exception as e:
                self.log.error(f"cancel_task error: {e}\n{traceback.format_exc()}")
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/coordinator/results/aggregate", response_model=ApiResponse)
        async def aggregate_results(
            request: SessionQueryApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """汇总会话任务结果"""
            try:
                data = request.data
                result = await self.coordinator.aggregate_results(data.session_id)
                
                if "error" in result:
                    return fail(ErrorCode.SYSTEM_ERROR, result["error"])
                
                return ok(result)
                
            except Exception as e:
                self.log.error(f"aggregate_results error: {e}\n{traceback.format_exc()}")
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.get("/v1/agent/coordinator/agents", response_model=ApiResponse)
        async def get_available_agents(
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """获取可用的规划智能体列表"""
            try:
                agents = self.coordinator.task_manager.get_available_agents()
                return ok({"agents": agents, "total": len(agents)})
                
            except Exception as e:
                self.log.error(f"get_available_agents error: {e}\n{traceback.format_exc()}")
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/coordinator/intent/recognize", response_model=ApiResponse)
        async def recognize_intent(
            request: CoordinateApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """
            意图识别接口（独立调用）
            使用FastText+Neo4j双引擎进行意图识别
            """
            try:
                user_id = int(user_ctx.user_id)
                query = request.data.query
                
                # 1. FastText快速分类
                ft_err, ft_candidates = await self.coordinator.fasttext_client.classify_intent(
                    query, top_k=3
                )
                
                # 2. Neo4j本体验证
                intent_result = await self.coordinator._neo4j_intent_verification(
                    ft_candidates, query, user_id
                )
                
                return ok(intent_result.model_dump())
                
            except Exception as e:
                self.log.error(f"recognize_intent error: {e}\n{traceback.format_exc()}")
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.post("/v1/agent/coordinator/context/resolve-reference", response_model=ApiResponse)
        async def resolve_reference(
            request: CoordinateApiRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """解析查询中的指代词（如'那辆车'）"""
            try:
                user_id = int(user_ctx.user_id)
                session_id = request.data.session_id or f"sess_{user_ctx.user_id}_{int(time.time())}"
                query = request.data.query
                
                # 加载会话上下文
                err, session_ctx = await self.coordinator.context_manager.load_session_context(
                    session_id, user_id
                )
                
                # 解析指代
                ref_err, ref_result = await self.coordinator.fasttext_client.resolve_reference(
                    query,
                    session_ctx.dialogue_history,
                    session_ctx.confirmed_slots
                )
                
                return ok({
                    "session_id": session_id,
                    "query": query,
                    "reference_resolution": ref_result
                })
                
            except Exception as e:
                self.log.error(f"resolve_reference error: {e}\n{traceback.format_exc()}")
                return fail(ErrorCode.SYSTEM_ERROR, str(e))
