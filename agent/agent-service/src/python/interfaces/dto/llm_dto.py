import time
import uuid
from typing import List, Optional, Union, Any, Dict, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
from enum import StrEnum


# ==================== 通用枚举 ====================

class Role(StrEnum):
    """消息角色 —— 强制枚举化（防拼写错误 & Swagger 下拉）"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class FinishReason(StrEnum):
    """完成原因 —— OpenAI 官方值 + 扩展项"""
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"  # ✅ 新增：支持工具调用结束（Qwen-VL / Tool-LLaMA）
    NULL = "null"


class StreamMode(StrEnum):
    """流式输出模式 —— 明确语义与性能边界"""
    TOKEN = "token"  # ✅ 真·流式：AsyncLLMEngine + `stream=True` → 逐 token yield
    CHUNK = "chunk"  # ✅ 伪流式：同步生成后按字符/标点分块（适合 CPU 或低配 GPU）
    AUTO = "auto"  # ✅ 自动：有 AsyncLLMEngine 且 GPU 可用 → TOKEN；否则 CHUNK


# ==================== 请求 DTO ====================

class StreamOptions(BaseModel):
    """流式输出选项 —— 增加安全约束与默认行为优化"""

    mode: StreamMode = Field(
        default=StreamMode.AUTO,
        description="流式模式：token（真流式）、chunk（分块）、auto（自动选择）",
    )
    chunk_size: int = Field(
        default=10,
        ge=1,
        le=256,  # ✅ 放宽上限：支持中英文混合（中文平均 2–3 字/Token）
        description="chunk 模式下每块最大字符数（非 token 数）",
    )
    include_usage: bool = Field(
        default=False,
        description="是否在流式结束帧（[DONE]）中返回 usage 字段",
    )
    # ✅ 新增：chunk 分割策略（避免截断 emoji / 中文词）
    chunk_by: Literal["char", "punct", "sentence"] = Field(
        default="punct",
        description="chunk 切分依据：'char'=固定长度；'punct'=按标点（。！？.!?）；'sentence'=按句号/换行",
    )


class ChatMessage(BaseModel):
    """对话消息 —— 支持多模态 content 结构（为 Qwen-VL 预留）"""

    role: Role = Field(..., description="消息角色")
    content: Union[str, List[Dict[str, Any]]] = Field(  # ✅ 支持 text + image_url（OpenAI Vision 格式）
        ...,
        description="消息内容：字符串 或 多模态列表（如 [{'type': 'text', 'text': '...'}, {'type': 'image_url', 'image_url': {'url': '...'}}]）",
    )

    # ✅ 可选：name 字段（用于 function calling / agent 角色名）
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="自定义角色名（仅当 role == 'assistant' 或 'function' 时有效）",
    )

    # ✅ 自动校验：content 类型合法性
    @model_validator(mode="after")
    def validate_content_type(self) -> "ChatMessage":
        if isinstance(self.content, list):
            for i, item in enumerate(self.content):
                if not isinstance(item, dict):
                    raise ValueError(f"content[{i}] must be dict, got {type(item).__name__}")
                if "type" not in item:
                    raise ValueError(f"content[{i}] missing 'type' key")
                if item["type"] not in ("text", "image_url", "image_data"):
                    raise ValueError(f"content[{i}]['type'] must be 'text', 'image_url', or 'image_data'")
        return self


class CompletionRequest(BaseModel):
    """
    文本补全请求 - 兼容 OpenAI /v1/completions
    ✅ 注意：vLLM 不原生支持此接口，建议重定向至 chat/completions（统一处理）
    """
    model: Optional[str] = Field(default=None, description="模型名称（可选）")
    prompt: Union[str, List[str]] = Field(
        ...,
        description="输入提示词（单条或批量）",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=32768,  # ✅ vLLM 实际支持更大（如 Qwen2-VL 支持 32K context）
        description="最大生成 token 数",
    )
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="温度参数（默认 0.7）",
    )
    top_p: Optional[float] = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Top-p 采样（默认 1.0 = 关闭）",
    )
    top_k: Optional[int] = Field(
        default=-1,  # ✅ vLLM 默认 -1 = disabled；设为 0 则报错
        ge=-1,
        description="Top-k 采样（-1 = 关闭）",
    )
    n: int = Field(
        default=1,
        ge=1,
        le=10,
        description="生成数量（batch size）",
    )
    stream: bool = Field(
        default=False,
        description="是否启用流式（注意：vLLM 的 text_completion 不推荐流式）",
    )
    stop: Optional[Union[str, List[str]]] = Field(
        default=None,
        max_length=4,  # ✅ OpenAI 限制最多 4 个 stop word
        description="停止词（最多 4 个）",
    )
    presence_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="存在惩罚",
    )
    frequency_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="频率惩罚",
    )
    user: Optional[str] = Field(
        default=None,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_\-\.]+$",  # ✅ 安全用户名正则（防注入）
        description="用户唯一标识（用于审计与限流）",
    )
    # ✅ 新增：vLLM 原生支持字段（直接透传）
    repetition_penalty: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=2.0,
        description="重复惩罚（vLLM 原生）",
    )
    min_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Min-p 采样（vLLM 原生）",
    )
    seed: Optional[int] = Field(
        default=None,
        ge=0,
        le=2 ** 32 - 1,
        description="随机种子（确保可复现）",
    )


class ChatCompletionRequest(BaseModel):
    """
    对话补全请求 - 兼容 OpenAI /v1/chat/completions
    ✅ 主力接口，vLLM + Qwen-VL 均深度优化
    """
    model: Optional[str] = Field(default=None, description="模型名称")
    messages: List[ChatMessage] = Field(
        ...,
        min_length=1,
        max_length=1024,  # ✅ 防爆栈（vLLM 默认 max_model_len=32768，但 messages 过长易 OOM）
        description="对话历史（最多 1024 条）",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=32768,
        description="最大生成 token 数",
    )
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="温度参数",
    )
    top_p: Optional[float] = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Top-p 采样",
    )
    top_k: Optional[int] = Field(
        default=-1,
        ge=-1,
        description="Top-k 采样（-1 = 关闭）",
    )
    n: int = Field(
        default=1,
        ge=1,
        le=10,
        description="生成数量",
    )
    stream: bool = Field(
        default=False,
        description="是否流式（true → 返回 SSE；false → JSON）",
    )
    stream_options: Optional[StreamOptions] = Field(
        default=None,
        description="流式高级选项（仅 stream=True 时生效）",
    )
    stop: Optional[Union[str, List[str]]] = Field(
        default=None,
        max_length=4,
        description="停止词（最多 4 个）",
    )
    presence_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="存在惩罚",
    )
    frequency_penalty: Optional[float] = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="频率惩罚",
    )
    user: Optional[str] = Field(
        default=None,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_\-\.]+$",
        description="用户唯一标识",
    )
    # ✅ 新增：工具调用支持（Qwen2-VL / Tool-LLaMA）
    tools: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="可用工具列表（OpenAI Tools Schema）",
    )
    tool_choice: Optional[Union[str, Dict[str, str]]] = Field(
        default=None,
        description="工具调用策略（'none', 'auto', 或 {'type': 'function', 'function': {'name': 'xxx'}}）",
    )
    # ✅ 新增：响应格式控制（JSON Mode）
    response_format: Optional[Dict[str, str]] = Field(
        default=None,
        description="期望响应格式（如 {'type': 'json_object'}）",
    )


# ==================== 响应 DTO ====================

class Usage(BaseModel):
    """Token 使用统计 —— 增加字段完整性 & 审计字段"""

    prompt_tokens: int = Field(
        default=0,
        ge=0,
        description="输入 prompt token 数",
    )
    completion_tokens: int = Field(
        default=0,
        ge=0,
        description="生成的 completion token 数",
    )
    total_tokens: int = Field(
        default=0,
        ge=0,
        description="prompt + completion token 总数",
    )
    # ✅ 新增：审计字段（记录 token 计算方式，便于排查）
    calc_method: Literal["tiktoken", "jieba", "vllm"] = Field(
        default="vllm",
        description="token 计数器类型（vLLM 原生计数最准）",
    )

    # ✅ 自动校验：total = prompt + completion
    @model_validator(mode="after")
    def validate_total_tokens(self) -> "Usage":
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")
        return self


class CompletionChoice(BaseModel):
    """补全选项 —— 兼容 OpenAI 并预留扩展"""

    index: int = Field(default=0, description="选项索引")
    text: str = Field(default="", description="生成的文本")
    finish_reason: Optional[FinishReason] = Field(  # ✅ 枚举化 finish_reason
        default=None,
        description="完成原因",
    )
    logprobs: Optional[Any] = Field(
        default=None,
        description="对数概率（结构取决于 logprobs 参数）",
    )
    # ✅ 新增：vLLM 原生字段（便于 debug）
    prompt_logprobs: Optional[Any] = Field(
        default=None,
        description="Prompt token 的对数概率（仅当 echo=True）",
    )


class ChatCompletionChoice(BaseModel):
    """对话补全选项 —— 支持 tool_calls"""

    index: int = Field(default=0, description="选项索引")
    message: ChatMessage = Field(..., description="生成的消息")
    finish_reason: Optional[FinishReason] = Field(
        default=None,
        description="完成原因",
    )
    # ✅ 新增：工具调用支持（OpenAI spec）
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="工具调用列表（当 finish_reason == 'tool_calls' 时存在）",
    )


class CompletionResponse(BaseModel):
    """
    文本补全响应 - 兼容 OpenAI 格式
    ⚠️ 注意：vLLM 推荐使用 chat/completions，此接口仅用于 legacy 兼容
    """
    id: str = Field(
        default_factory=lambda: f"cmpl-{uuid.uuid4().hex[:24]}",
        pattern=r"^cmpl-[a-zA-Z0-9]{24}$",
        description="请求唯一 ID",
    )
    object: Literal["text_completion"] = Field(
        default="text_completion",
        description="对象类型",
    )
    created: int = Field(
        default_factory=lambda: int(time.time()),
        ge=1609459200,  # 2021-01-01
        description="创建时间戳（秒）",
    )
    model: str = Field(
        default="",
        min_length=1,
        max_length=128,
        description="实际服务的模型名称",
    )
    choices: List[CompletionChoice] = Field(
        default_factory=list,
        description="生成结果列表",
    )
    usage: Usage = Field(
        default_factory=Usage,
        description="Token 使用统计",
    )
    # ✅ 新增：服务元数据（便于运维定位）
    server_info: Dict[str, str] = Field(
        default_factory=lambda: {"engine": "vllm", "version": "0.6.3"},
        description="服务引擎信息（可动态注入）",
    )


class ChatCompletionResponse(BaseModel):
    """
    对话补全响应 - 兼容 OpenAI 格式（主力响应）
    """
    id: str = Field(
        default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}",
        pattern=r"^chatcmpl-[a-zA-Z0-9]{24}$",
        description="请求唯一 ID",
    )
    object: Literal["chat.completion"] = Field(
        default="chat.completion",
        description="对象类型",
    )
    created: int = Field(
        default_factory=lambda: int(time.time()),
        ge=1609459200,
        description="创建时间戳（秒）",
    )
    model: str = Field(
        default="",
        min_length=1,
        max_length=128,
        description="实际服务的模型名称",
    )
    choices: List[ChatCompletionChoice] = Field(
        default_factory=list,
        description="生成结果列表",
    )
    usage: Usage = Field(
        default_factory=Usage,
        description="Token 使用统计",
    )
    # ✅ 新增：延迟与资源指标（SRE 必备）
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="端到端延迟（毫秒，由中间件注入）",
    )
    gpu_memory_used_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="本次请求峰值显存占用（MB）",
    )


# ==================== 流式响应 DTO ====================

class DeltaMessage(BaseModel):
    """流式消息增量 —— 支持 tool_calls delta"""

    role: Optional[Role] = Field(
        default=None,
        description="角色增量（仅首块有）",
    )
    content: Optional[str] = Field(
        default=None,
        description="内容增量（字符串）",
    )
    # ✅ 新增：tool_calls 增量（支持 streaming tool calls）
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="工具调用增量（追加式）",
    )


class ChatCompletionChunkChoice(BaseModel):
    """流式对话补全选项"""

    index: int = Field(default=0, description="选项索引")
    delta: DeltaMessage = Field(
        default_factory=DeltaMessage,
        description="消息增量",
    )
    finish_reason: Optional[FinishReason] = Field(
        default=None,
        description="完成原因（仅最后一块有）",
    )


class ChatCompletionChunk(BaseModel):
    """
    流式对话补全响应块 - 兼容 OpenAI SSE 格式
    ✅ 注意：SSE 要求每行以 'data: ' 开头，此 DTO 仅为 Python 内部结构
    """
    id: str = Field(
        default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}",
        pattern=r"^chatcmpl-[a-zA-Z0-9]{24}$",
        description="请求唯一 ID",
    )
    object: Literal["chat.completion.chunk"] = Field(
        default="chat.completion.chunk",
        description="对象类型",
    )
    created: int = Field(
        default_factory=lambda: int(time.time()),
        ge=1609459200,
        description="创建时间戳（秒）",
    )
    model: str = Field(
        default="",
        min_length=1,
        max_length=128,
        description="模型名称",
    )
    choices: List[ChatCompletionChunkChoice] = Field(
        default_factory=list,
        description="生成结果列表",
    )
    # ✅ 新增：流式专用字段（用于 [DONE] 帧）
    usage: Optional[Usage] = Field(
        default=None,
        description="仅在最后 [DONE] 帧中出现（当 stream_options.include_usage=True）",
    )

    # ✅ 自动设置 usage（若存在且未填 total_tokens）
    @model_validator(mode="after")
    def ensure_usage_total(self) -> "ChatCompletionChunk":
        if self.usage and self.usage.total_tokens == 0:
            self.usage.total_tokens = self.usage.prompt_tokens + self.usage.completion_tokens
        return self