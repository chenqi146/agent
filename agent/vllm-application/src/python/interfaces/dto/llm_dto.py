'''
LLM 请求/响应 DTO 定义
兼容 OpenAI API 格式
'''
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import time
import uuid


# ==================== 通用枚举 ====================

class Role(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class FinishReason(str, Enum):
    """完成原因"""
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    NULL = "null"


class StreamMode(str, Enum):
    """流式输出模式"""
    TOKEN = "token"   # Token 级流式（真正的流式，需要 AsyncLLMEngine）
    CHUNK = "chunk"   # Chunk 级流式（伪流式，先生成完再分块发送）
    AUTO = "auto"     # 自动选择（优先 token 模式）


# ==================== 请求 DTO ====================

class StreamOptions(BaseModel):
    """流式输出选项"""
    mode: StreamMode = Field(default=StreamMode.AUTO, description="流式模式: token/chunk/auto")
    chunk_size: int = Field(default=10, ge=1, le=100, description="chunk 模式下每块字符数")
    include_usage: bool = Field(default=False, description="是否在最后返回 usage 信息")

class ChatMessage(BaseModel):
    """对话消息"""
    role: Role = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")


class CompletionRequest(BaseModel):
    """
    文本补全请求 - 兼容 OpenAI /v1/completions
    """
    model: Optional[str] = Field(default=None, description="模型名称（可选，使用默认模型）")
    prompt: Union[str, List[str]] = Field(..., description="输入提示词，支持单条或批量")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192, description="最大生成token数")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="温度参数")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Top-p采样参数")
    top_k: Optional[int] = Field(default=None, ge=1, description="Top-k采样参数")
    n: int = Field(default=1, ge=1, le=10, description="生成数量")
    stream: bool = Field(default=False, description="是否流式输出")
    stop: Optional[Union[str, List[str]]] = Field(default=None, description="停止词")
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0, description="存在惩罚")
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0, description="频率惩罚")
    user: Optional[str] = Field(default=None, description="用户标识")


class ChatCompletionRequest(BaseModel):
    """
    对话补全请求 - 兼容 OpenAI /v1/chat/completions
    """
    model: Optional[str] = Field(default=None, description="模型名称（可选，使用默认模型）")
    messages: List[ChatMessage] = Field(..., min_length=1, description="对话历史")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192, description="最大生成token数")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="温度参数")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Top-p采样参数")
    top_k: Optional[int] = Field(default=None, ge=1, description="Top-k采样参数")
    n: int = Field(default=1, ge=1, le=10, description="生成数量")
    stream: bool = Field(default=False, description="是否流式输出")
    stream_options: Optional[StreamOptions] = Field(default=None, description="流式输出选项")
    stop: Optional[Union[str, List[str]]] = Field(default=None, description="停止词")
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0, description="存在惩罚")
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0, description="频率惩罚")
    user: Optional[str] = Field(default=None, description="用户标识")


# ==================== 响应 DTO ====================

class Usage(BaseModel):
    """Token使用统计"""
    prompt_tokens: int = Field(default=0, description="输入token数")
    completion_tokens: int = Field(default=0, description="输出token数")
    total_tokens: int = Field(default=0, description="总token数")


class CompletionChoice(BaseModel):
    """补全选项"""
    index: int = Field(default=0, description="选项索引")
    text: str = Field(default="", description="生成的文本")
    finish_reason: Optional[str] = Field(default=None, description="完成原因")
    logprobs: Optional[Any] = Field(default=None, description="对数概率")


class ChatCompletionChoice(BaseModel):
    """对话补全选项"""
    index: int = Field(default=0, description="选项索引")
    message: ChatMessage = Field(..., description="生成的消息")
    finish_reason: Optional[str] = Field(default=None, description="完成原因")


class CompletionResponse(BaseModel):
    """
    文本补全响应 - 兼容 OpenAI 格式
    """
    id: str = Field(default_factory=lambda: f"cmpl-{uuid.uuid4().hex[:24]}", description="请求ID")
    object: str = Field(default="text_completion", description="对象类型")
    created: int = Field(default_factory=lambda: int(time.time()), description="创建时间戳")
    model: str = Field(default="", description="模型名称")
    choices: List[CompletionChoice] = Field(default_factory=list, description="生成结果列表")
    usage: Usage = Field(default_factory=Usage, description="Token使用统计")


class ChatCompletionResponse(BaseModel):
    """
    对话补全响应 - 兼容 OpenAI 格式
    """
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}", description="请求ID")
    object: str = Field(default="chat.completion", description="对象类型")
    created: int = Field(default_factory=lambda: int(time.time()), description="创建时间戳")
    model: str = Field(default="", description="模型名称")
    choices: List[ChatCompletionChoice] = Field(default_factory=list, description="生成结果列表")
    usage: Usage = Field(default_factory=Usage, description="Token使用统计")


# ==================== 流式响应 DTO ====================

class DeltaMessage(BaseModel):
    """流式消息增量"""
    role: Optional[str] = Field(default=None, description="消息角色")
    content: Optional[str] = Field(default=None, description="消息内容增量")


class ChatCompletionChunkChoice(BaseModel):
    """流式对话补全选项"""
    index: int = Field(default=0, description="选项索引")
    delta: DeltaMessage = Field(default_factory=DeltaMessage, description="消息增量")
    finish_reason: Optional[str] = Field(default=None, description="完成原因")


class ChatCompletionChunk(BaseModel):
    """
    流式对话补全响应块 - 兼容 OpenAI SSE 格式
    """
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}", description="请求ID")
    object: str = Field(default="chat.completion.chunk", description="对象类型")
    created: int = Field(default_factory=lambda: int(time.time()), description="创建时间戳")
    model: str = Field(default="", description="模型名称")
    choices: List[ChatCompletionChunkChoice] = Field(default_factory=list, description="生成结果列表")


# ==================== 模型信息 DTO ====================

class ModelInfo(BaseModel):
    """模型信息"""
    id: str = Field(..., description="模型ID")
    object: str = Field(default="model", description="对象类型")
    created: int = Field(default_factory=lambda: int(time.time()), description="创建时间戳")
    owned_by: str = Field(default="organization", description="所有者")


class ModelListResponse(BaseModel):
    """模型列表响应"""
    object: str = Field(default="list", description="对象类型")
    data: List[ModelInfo] = Field(default_factory=list, description="模型列表")


# ==================== 通用请求 DTO ====================

class EmptyRequest(BaseModel):
    """空请求体（用于无参数的 POST 接口）"""
    pass


class ModelReloadRequest(BaseModel):
    """模型重载请求"""
    force: bool = Field(default=False, description="是否强制重载")


# ==================== 健康检查 DTO ====================

class GPUResourceDTO(BaseModel):
    """GPU资源信息"""
    gpu_id: int = Field(..., description="GPU ID")
    gpu_name: str = Field(default="", description="GPU名称")
    total_memory_mb: float = Field(default=0.0, description="总显存(MB)")
    used_memory_mb: float = Field(default=0.0, description="已用显存(MB)")
    free_memory_mb: float = Field(default=0.0, description="空闲显存(MB)")
    memory_utilization: float = Field(default=0.0, description="显存利用率")
    gpu_utilization: float = Field(default=0.0, description="GPU利用率")
    temperature: float = Field(default=0.0, description="温度(°C)")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    is_healthy: bool = Field(..., description="是否健康")
    model_status: str = Field(default="unknown", description="模型状态")
    model_name: str = Field(default="", description="模型名称")
    uptime_seconds: float = Field(default=0.0, description="运行时间(秒)")
    total_requests: int = Field(default=0, description="总请求数")
    successful_requests: int = Field(default=0, description="成功请求数")
    failed_requests: int = Field(default=0, description="失败请求数")
    active_requests: int = Field(default=0, description="当前活跃请求数")
    avg_latency_ms: float = Field(default=0.0, description="平均延迟(毫秒)")
    gpu_resources: List[GPUResourceDTO] = Field(default_factory=list, description="GPU资源信息")
    error_message: Optional[str] = Field(default=None, description="错误信息")

