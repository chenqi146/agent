"""
Planning Agent Repository
规划智能体数据访问层
"""
from typing import Any, Dict, List, Optional, Tuple
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.persistences.mysql_persistence import MysqlPersistence
from infrastructure.common.logging.logging import logger


@logger()
class PlanningAgentRepository:
    """规划智能体数据仓库"""
    
    def __init__(self, mysql: MysqlPersistence):
        self.mysql = mysql
    
    # ==================== 规划会话管理 ====================
    
    def create_planning_session(
        self,
        session_id: str,
        user_id: int,
        agent_type: str,
        goal: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ErrorCode, int]:
        """创建规划会话"""
        data = {
            "session_id": session_id,
            "user_id": user_id,
            "agent_type": agent_type,
            "goal": goal,
            "initial_context": initial_context,
            "status": "planning"
        }
        return self.mysql.insert("planning_session_tbl", data)
    
    def get_planning_session(
        self,
        session_id: str
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """获取规划会话"""
        condition = "session_id = %s"
        return self.mysql.select_one("planning_session_tbl", condition=condition, params=(session_id,))
    
    def update_planning_session(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> Tuple[ErrorCode, int]:
        """更新规划会话"""
        condition = "session_id = %s"
        return self.mysql.update("planning_session_tbl", data=data, condition=condition, params=(session_id,))
    
    def list_user_planning_sessions(
        self,
        user_id: int,
        agent_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """列出用户的规划会话"""
        conditions = ["user_id = %s"]
        params: List[Any] = [user_id]
        
        if agent_type:
            conditions.append("agent_type = %s")
            params.append(agent_type)
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        condition = " AND ".join(conditions)
        return self.mysql.select(
            "planning_session_tbl",
            condition=condition,
            params=tuple(params),
            order_by="created_at DESC",
            limit=limit,
            offset=offset
        )
    
    # ==================== 任务DAG管理 ====================
    
    def create_task(
        self,
        session_id: str,
        task_id: str,
        task_name: str,
        task_type: str,
        description: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        is_critical_path: bool = False,
        execution_order: int = 0,
        parallel_group: int = 0,
        max_retries: int = 3,
        timeout_seconds: int = 30
    ) -> Tuple[ErrorCode, int]:
        """创建任务"""
        data = {
            "session_id": session_id,
            "task_id": task_id,
            "task_name": task_name,
            "task_type": task_type,
            "description": description,
            "dependencies": dependencies,
            "is_critical_path": is_critical_path,
            "execution_order": execution_order,
            "parallel_group": parallel_group,
            "max_retries": max_retries,
            "timeout_seconds": timeout_seconds,
            "status": "pending"
        }
        return self.mysql.insert("task_dag_tbl", data)
    
    def get_task(
        self,
        session_id: str,
        task_id: str
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """获取任务"""
        condition = "session_id = %s AND task_id = %s"
        return self.mysql.select_one("task_dag_tbl", condition=condition, params=(session_id, task_id))
    
    def update_task(
        self,
        session_id: str,
        task_id: str,
        data: Dict[str, Any]
    ) -> Tuple[ErrorCode, int]:
        """更新任务"""
        condition = "session_id = %s AND task_id = %s"
        return self.mysql.update("task_dag_tbl", data=data, condition=condition, params=(session_id, task_id))
    
    def list_session_tasks(
        self,
        session_id: str
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """列出会话的所有任务"""
        condition = "session_id = %s"
        return self.mysql.select(
            "task_dag_tbl",
            condition=condition,
            params=(session_id,),
            order_by="execution_order ASC"
        )
    
    def get_tasks_by_status(
        self,
        session_id: str,
        status: str
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """获取指定状态的任务"""
        condition = "session_id = %s AND status = %s"
        return self.mysql.select(
            "task_dag_tbl",
            condition=condition,
            params=(session_id, status),
            order_by="execution_order ASC"
        )
    
    # ==================== 依赖关系管理 ====================
    
    def create_dependency(
        self,
        session_id: str,
        task_id: str,
        depends_on_task_id: str,
        dependency_type: str = "strong",
        condition_expression: Optional[str] = None
    ) -> Tuple[ErrorCode, int]:
        """创建任务依赖关系"""
        data = {
            "session_id": session_id,
            "task_id": task_id,
            "depends_on_task_id": depends_on_task_id,
            "dependency_type": dependency_type,
            "condition_expression": condition_expression
        }
        return self.mysql.insert("task_dependency_tbl", data)
    
    def get_task_dependencies(
        self,
        session_id: str,
        task_id: str
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """获取任务的依赖关系"""
        condition = "session_id = %s AND task_id = %s"
        return self.mysql.select(
            "task_dependency_tbl",
            condition=condition,
            params=(session_id, task_id)
        )
    
    # ==================== 工具匹配管理 ====================
    
    def create_tool_match(
        self,
        session_id: str,
        task_id: str,
        tool_id: str,
        tool_name: str,
        match_score: float,
        match_reason: Optional[str] = None,
        input_params: Optional[Dict[str, Any]] = None,
        fallback_tools: Optional[List[str]] = None,
        is_primary: bool = True,
        execution_order: int = 1
    ) -> Tuple[ErrorCode, int]:
        """创建工具匹配记录"""
        data = {
            "session_id": session_id,
            "task_id": task_id,
            "tool_id": tool_id,
            "tool_name": tool_name,
            "match_score": match_score,
            "match_reason": match_reason,
            "input_params": input_params,
            "fallback_tools": fallback_tools,
            "is_primary": is_primary,
            "execution_order": execution_order,
            "status": "pending"
        }
        return self.mysql.insert("tool_matching_tbl", data)
    
    def get_task_tools(
        self,
        session_id: str,
        task_id: str
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """获取任务的工具匹配列表"""
        condition = "session_id = %s AND task_id = %s"
        return self.mysql.select(
            "tool_matching_tbl",
            condition=condition,
            params=(session_id, task_id),
            order_by="match_score DESC"
        )
    
    def update_tool_match_status(
        self,
        id: int,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_info: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> Tuple[ErrorCode, int]:
        """更新工具匹配状态"""
        data = {"status": status}
        if result is not None:
            data["result"] = result
        if error_info is not None:
            data["error_info"] = error_info
        if execution_time_ms is not None:
            data["execution_time_ms"] = execution_time_ms
        
        condition = "id = %s"
        return self.mysql.update("tool_matching_tbl", data=data, condition=condition, params=(id,))
    
    # ==================== 策略知识库管理 ====================
    
    def get_strategy_knowledge(
        self,
        agent_type: str,
        scenario_type: Optional[str] = None,
        is_active: bool = True
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """获取策略知识"""
        conditions = ["agent_type = %s"]
        params: List[Any] = [agent_type]
        
        if scenario_type:
            conditions.append("scenario_type = %s")
            params.append(scenario_type)
        
        if is_active:
            conditions.append("is_active = 1")
        
        condition = " AND ".join(conditions)
        return self.mysql.select(
            "strategy_knowledge_tbl",
            condition=condition,
            params=tuple(params),
            order_by="effectiveness_score DESC"
        )
    
    def get_strategy_by_id(
        self,
        knowledge_id: str
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """根据ID获取策略知识"""
        condition = "knowledge_id = %s"
        return self.mysql.select_one("strategy_knowledge_tbl", condition=condition, params=(knowledge_id,))
    
    def update_strategy_effectiveness(
        self,
        knowledge_id: str,
        effectiveness_score: float
    ) -> Tuple[ErrorCode, int]:
        """更新策略有效性评分"""
        data = {"effectiveness_score": effectiveness_score}
        condition = "knowledge_id = %s"
        return self.mysql.update("strategy_knowledge_tbl", data=data, condition=condition, params=(knowledge_id,))
    
    # ==================== 规划中间态管理 ====================
    
    def save_intermediate_state(
        self,
        session_id: str,
        stage: str,
        state_data: Dict[str, Any],
        reasoning_chain: Optional[str] = None,
        conflicts_detected: Optional[List[Dict[str, Any]]] = None,
        resolutions: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[ErrorCode, int]:
        """保存规划中间态"""
        data = {
            "session_id": session_id,
            "stage": stage,
            "state_data": state_data,
            "reasoning_chain": reasoning_chain,
            "conflicts_detected": conflicts_detected,
            "resolutions": resolutions
        }
        return self.mysql.insert("planning_intermediate_state_tbl", data)
    
    def get_intermediate_state(
        self,
        session_id: str,
        stage: str
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """获取规划中间态"""
        condition = "session_id = %s AND stage = %s"
        return self.mysql.select_one("planning_intermediate_state_tbl", condition=condition, params=(session_id, stage))
    
    # ==================== 执行轨迹管理 ====================
    
    def save_execution_trajectory(
        self,
        session_id: str,
        trajectory_id: str,
        trace_data: Dict[str, Any],
        analysis_result: Optional[Dict[str, Any]] = None,
        success_patterns: Optional[List[str]] = None,
        failure_lessons: Optional[List[str]] = None,
        optimization_suggestions: Optional[List[str]] = None,
        strategy_update_needed: bool = False
    ) -> Tuple[ErrorCode, int]:
        """保存执行轨迹"""
        data = {
            "session_id": session_id,
            "trajectory_id": trajectory_id,
            "trace_data": trace_data,
            "analysis_result": analysis_result,
            "success_patterns": success_patterns,
            "failure_lessons": failure_lessons,
            "optimization_suggestions": optimization_suggestions,
            "strategy_update_needed": strategy_update_needed
        }
        return self.mysql.insert("execution_trajectory_tbl", data)
    
    def get_execution_trajectory(
        self,
        session_id: str
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """获取执行轨迹"""
        condition = "session_id = %s"
        return self.mysql.select_one("execution_trajectory_tbl", condition=condition, params=(session_id,), order_by="created_at DESC")
    
    # ==================== 智能体配置管理 ====================
    
    def get_agent_config(
        self,
        agent_type: str
    ) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        """获取智能体配置"""
        condition = "agent_type = %s"
        return self.mysql.select_one("planning_agent_config_tbl", condition=condition, params=(agent_type,))
