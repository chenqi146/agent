from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    """意图分类类别"""
    CITY_PARKING = "city_parking"
    STEWARD = "steward"
    GENERAL_CHAT = "general_chat"
    TOOL_EXECUTION = "tool_execution"
    UNKNOWN = "unknown"


class IntentRecognitionResult(BaseModel):
    """意图识别结果"""
    primary_intent: str = Field(..., description="主要意图")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    candidates: List[Dict[str, Any]] = Field(default_factory=list, description="Top-N候选意图")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="提取的参数")
    reasoning: str = Field(default="", description="推理说明")
    ontology_matched: bool = Field(default=False, description="是否通过本体验证")


class SessionContext(BaseModel):
    """会话级上下文（Redis存储）"""
    session_id: str = Field(..., description="会话标识")
    user_id: int = Field(..., description="用户ID")
    intent_stack: List[str] = Field(default_factory=list, description="意图栈")
    confirmed_slots: Dict[str, Any] = Field(default_factory=dict, description="已确认槽位")
    dialogue_history: List[Dict[str, Any]] = Field(default_factory=list, description="最近5轮对话")
    temp_variables: Dict[str, Any] = Field(default_factory=dict, description="临时变量")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    ttl: int = Field(default=1800, description="过期时间（秒）")


class BusinessContext(BaseModel):
    """业务级上下文"""
    entity_states: Dict[str, Any] = Field(default_factory=dict, description="相关实体状态")
    process_progress: Dict[str, Any] = Field(default_factory=dict, description="业务流程进度")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="用户信息/权限")
    system_context: Dict[str, Any] = Field(default_factory=dict, description="系统状态/时间")


class DomainKnowledgeContext(BaseModel):
    """领域知识上下文"""
    ontology_context: List[Dict[str, Any]] = Field(default_factory=list, description="本体关系图谱")
    constraint_context: List[str] = Field(default_factory=list, description="业务约束")
    historical_context: List[Dict[str, Any]] = Field(default_factory=list, description="类似历史案例")


class FullContext(BaseModel):
    """完整上下文"""
    session: SessionContext
    business: BusinessContext
    domain: DomainKnowledgeContext
    rag_context: str = Field(default="", description="RAG检索上下文")
    memory_context: str = Field(default="", description="记忆上下文")


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str = Field(..., description="任务ID")
    session_id: str = Field(..., description="所属会话ID")
    task_type: str = Field(..., description="任务类型")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    intent: str = Field(..., description="关联意图")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    assigned_agent: Optional[str] = Field(default=None, description="分配的智能体")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = Field(default=None)
    completed_at: Optional[str] = Field(default=None)
    result: Optional[Any] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    execution_time_ms: Optional[int] = Field(default=None)


class AgentInfo(BaseModel):
    """规划智能体信息"""
    agent_id: str = Field(..., description="智能体ID")
    agent_name: str = Field(..., description="智能体名称")
    agent_type: str = Field(..., description="智能体类型")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    supported_intents: List[str] = Field(default_factory=list, description="支持的意图")
    status: str = Field(default="available", description="状态")


class CoordinateRequest(BaseModel):
    """协调请求"""
    query: str = Field(..., description="用户查询")
    session_id: Optional[str] = Field(default=None, description="会话ID（新建会话时为空）")
    user_id: int = Field(..., description="用户ID")
    context_override: Optional[Dict[str, Any]] = Field(default=None, description="上下文覆盖")
    thinking: bool = Field(default=False, description="是否启用深度思考（协调规划）")


class CoordinateResponse(BaseModel):
    """协调响应"""
    session_id: str = Field(..., description="会话ID")
    intent: IntentRecognitionResult = Field(..., description="识别的意图")
    tasks: List[TaskInfo] = Field(default_factory=list, description="创建的任务")
    response: str = Field(default="", description="响应内容")
    context_summary: Dict[str, Any] = Field(default_factory=dict, description="上下文摘要")


class TaskResult(BaseModel):
    """任务结果"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus
    result: Optional[Any] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    execution_time_ms: Optional[int] = Field(default=None)


class BatchTaskRequest(BaseModel):
    """批量任务请求"""
    session_id: str = Field(..., description="会话ID")
    tasks: List[Dict[str, Any]] = Field(..., description="任务列表")


class SessionStatus(BaseModel):
    """会话状态"""
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="会话状态")
    active_tasks: int = Field(default=0, description="活跃任务数")
    completed_tasks: int = Field(default=0, description="已完成任务数")
    failed_tasks: int = Field(default=0, description="失败任务数")
    created_at: str = Field(...)
    last_activity: str = Field(...)
    ttl_remaining: int = Field(..., description="剩余过期时间（秒）")


# ============== API请求包裹结构 ==============

class CoordinateApiRequest(BaseModel):
    """协调请求API包裹"""
    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: CoordinateRequest = Field(..., description="实际业务参数")


class TaskQueryRequest(BaseModel):
    """任务查询请求"""
    task_id: Optional[str] = Field(default=None, description="任务ID")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    status: Optional[TaskStatus] = Field(default=None, description="状态过滤")


class TaskQueryApiRequest(BaseModel):
    """任务查询API包裹"""
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: TaskQueryRequest = Field(...)


class SessionQueryRequest(BaseModel):
    """会话查询请求"""
    session_id: str = Field(..., description="会话ID")


class SessionQueryApiRequest(BaseModel):
    """会话查询API包裹"""
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: SessionQueryRequest = Field(...)
