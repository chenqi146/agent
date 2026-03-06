"""
Planning Agent DTOs
规划智能体数据传输对象
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class PlanningAgentType(str, Enum):
    """规划智能体类型"""
    PARKING_BILLING = "parking_billing"  # 停车计费
    PARKING_OPERATION = "parking_operation"  # 停车运营
    ARREARS_COLLECTION = "arrears_collection"  # 欠费追缴


class PlanningSessionStatus(str, Enum):
    """规划会话状态"""
    PLANNING = "planning"      # 规划中
    EXECUTING = "executing"    # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"        # 待执行
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    SKIPPED = "skipped"        # 已跳过


class TaskType(str, Enum):
    """任务类型"""
    ANALYSIS = "analysis"      # 分析
    DECISION = "decision"      # 决策
    ACTION = "action"          # 执行
    VERIFICATION = "verification"  # 验证


class DependencyType(str, Enum):
    """依赖类型"""
    STRONG = "strong"          # 强依赖（必须完成）
    WEAK = "weak"              # 弱依赖（条件满足即可）


# ==================== 请求 DTOs ====================

class CreatePlanningSessionRequest(BaseModel):
    """创建规划会话请求"""
    user_id: int = Field(..., description="用户ID")
    agent_type: PlanningAgentType = Field(..., description="智能体类型")
    goal: str = Field(..., description="目标描述")
    initial_context: Optional[Dict[str, Any]] = Field(default=None, description="初始上下文")


class ExecutePlanningRequest(BaseModel):
    """执行规划请求"""
    session_id: str = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")


class GetPlanningStatusRequest(BaseModel):
    """获取规划状态请求"""
    session_id: str = Field(..., description="会话ID")


class UpdateTaskStatusRequest(BaseModel):
    """更新任务状态请求"""
    session_id: str = Field(..., description="会话ID")
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="新状态")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="输出数据")
    error_info: Optional[Dict[str, Any]] = Field(default=None, description="错误信息")


# ==================== 响应 DTOs ====================

class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    task_type: TaskType = Field(..., description="任务类型")
    description: Optional[str] = Field(default=None, description="任务描述")
    status: TaskStatus = Field(..., description="任务状态")
    dependencies: List[str] = Field(default_factory=list, description="依赖任务ID列表")
    is_critical_path: bool = Field(default=False, description="是否在关键路径上")
    execution_order: int = Field(default=0, description="执行顺序")
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")
    timeout_seconds: int = Field(default=30, description="超时时间")


class ToolMatchInfo(BaseModel):
    """工具匹配信息"""
    tool_id: str = Field(..., description="工具ID")
    tool_name: str = Field(..., description="工具名称")
    match_score: float = Field(..., description="匹配分数")
    match_reason: Optional[str] = Field(default=None, description="匹配原因")
    is_primary: bool = Field(default=True, description="是否是主工具")
    fallback_tools: List[str] = Field(default_factory=list, description="回退工具列表")


class PlanningResult(BaseModel):
    """规划结果"""
    session_id: str = Field(..., description="会话ID")
    status: PlanningSessionStatus = Field(..., description="规划状态")
    tasks: List[TaskInfo] = Field(default_factory=list, description="任务列表")
    critical_path: List[str] = Field(default_factory=list, description="关键路径任务ID列表")
    parallel_groups: List[List[str]] = Field(default_factory=list, description="并行执行组")
    tool_matches: Dict[str, List[ToolMatchInfo]] = Field(default_factory=dict, description="任务-工具匹配")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")


class PlanningSessionResponse(BaseModel):
    """规划会话响应"""
    session_id: str = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    agent_type: PlanningAgentType = Field(..., description="智能体类型")
    goal: str = Field(..., description="目标描述")
    status: PlanningSessionStatus = Field(..., description="状态")
    plan_result: Optional[PlanningResult] = Field(default=None, description="规划结果")
    execution_log: Optional[Dict[str, Any]] = Field(default=None, description="执行日志")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class StrategyKnowledgeInfo(BaseModel):
    """策略知识信息"""
    knowledge_id: str = Field(..., description="知识ID")
    agent_type: str = Field(..., description="适用的智能体类型")
    scenario_type: str = Field(..., description="场景类型")
    pattern_name: str = Field(..., description="模式名称")
    description: Optional[str] = Field(default=None, description="描述")
    success_criteria: List[str] = Field(default_factory=list, description="成功标准")
    best_practice: Optional[str] = Field(default=None, description="最佳实践")
    tool_combination: List[str] = Field(default_factory=list, description="推荐工具组合")
    effectiveness_score: float = Field(default=0.0, description="有效性评分")


class PlanningIntermediateState(BaseModel):
    """规划中间态"""
    stage: str = Field(..., description="阶段")
    state_data: Dict[str, Any] = Field(..., description="状态数据")
    reasoning_chain: Optional[str] = Field(default=None, description="推理链")
    conflicts_detected: Optional[List[Dict[str, Any]]] = Field(default=None, description="检测到的冲突")
    resolutions: Optional[List[Dict[str, Any]]] = Field(default=None, description="冲突解决方案")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


# ==================== API 包装 DTOs ====================

class ApiRequest(BaseModel):
    """通用API请求包装"""
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: Dict[str, Any] = Field(...)


class ApiResponse(BaseModel):
    """通用API响应包装"""
    code: int = Field(default=0)
    message: str = Field(default="success")
    data: Optional[Any] = Field(default=None)


class CreatePlanningSessionApiRequest(ApiRequest):
    """创建规划会话API请求"""
    data: CreatePlanningSessionRequest = Field(...)


class ExecutePlanningApiRequest(ApiRequest):
    """执行规划API请求"""
    data: ExecutePlanningRequest = Field(...)


class GetPlanningStatusApiRequest(ApiRequest):
    """获取规划状态API请求"""
    data: GetPlanningStatusRequest = Field(...)


class UpdateTaskStatusApiRequest(ApiRequest):
    """更新任务状态API请求"""
    data: UpdateTaskStatusRequest = Field(...)
