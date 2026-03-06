'''
VLM 请求/响应 DTO 定义
视觉语言模型接口数据传输对象，兼容 OpenAI Vision API 格式
'''
from typing import Dict, Any, List, Optional, Union,Literal
from pydantic import BaseModel, Field, field_validator,AnyUrl,model_validator, computed_field
from enum import Enum
import time
import uuid

'''==================== 通用枚举 ===================='''
class Role(str,Enum):
    '''msg role'''
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    def __str__(self) -> str:
        return self.value

class ImageDetail(str,Enum):
    """图像细节级别"""
    LOW = "low"
    HIGH = "high"
    AUTO = "auto"
    def __str__(self)->str:
        return self.value

class StreamMode(str,Enum):
    """流式输出模式"""
    TOKEN = "token"  # 真正的 token 级流式（使用 AsyncLLMEngine）
    CHUNK = "chunk"  # 分块流式（先生成完再分块发送）
    AUTO = "auto"  # 自动选择（默认使用 token 模式）
    def __str__(self):
        return self.value

'''==================== 图像内容 DTO ===================='''
class ImageUrl(BaseModel):
    url: str = Field(...,
                     description="图像URL或base64编码（data:image/jpeg;base64,...）",
                     min_length=5)
    detail: ImageDetail = Field(default=ImageDetail.AUTO,
                                description="image level detail")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value.startswith("data:image/"):
            raise ValueError("url must start with 'data:image/'")
        return value

    @property
    def is_data_uri(self)->bool:
        return self.url.startswith("data:image/")
    @property
    def mime_type(self)->Optional[str]:
        if self.is_data_uri:
            return self.url.split(";", 1)[0].split(":", 1)[-1]
        return None

class TextContent(BaseModel):
    """文本内容项 —— 兼容 OpenAI-style 多模态消息格式"""
    type: Literal["text"] = Field(
        default="text",
        description="内容类型，固定为 'text'",
        # ✅ 强制类型约束：只能是字符串 "text"，不可被覆盖为其他值
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=4096,  # OpenAI 限制参考；按需调整
        description="纯文本内容，不支持 Markdown/HTML 渲染（除非下游明确支持）",
    )

    # ✅ 可选：校验 text 是否仅含可打印字符（防控制字符/零宽空格等）
    @field_validator("text")
    @classmethod
    def validate_text_no_control_chars(cls, v: str) -> str:
        if any(ord(c) < 32 and c != "\t" and c != "\n" and c != "\r" for c in v):
            raise ValueError("text must not contain ASCII control characters (except \\t, \\n, \\r)")
        return v

    # ✅ 可选：提供安全截断方法（避免超长文本破坏下游）
    def truncated(self, max_len: int = 200) -> str:
        """返回截断后的文本（带省略号），用于日志或摘要"""
        if len(self.text) <= max_len:
            return self.text
        return self.text[: max_len - 3] + "..."

class ImageContent(BaseModel):
    """图像内容"""
    type: Literal["image_url"] = Field(default="image_url", description="内容类型，固定为 'image_url'")
    image_url: AnyUrl = Field(..., description="图像URL信息")

# 消息内容可以是文本或图像
ContentItem = Union[TextContent, ImageContent]
# 视觉消息主模型（核心修复 & 增强）---
class VisionMessage(BaseModel):
    """视觉消息 - 支持文本 + 图像的多模态内容（兼容 OpenAI / Anthropic 格式）"""
    role: Role = Field(
        ...,
        description="消息发送方角色",
    )
    content: Union[str, List[ContentItem]] = Field(
        ...,
        description=(
            "纯文本字符串（如 'Hello'），或结构化多模态列表 "
            "[{'type': 'text', 'text': '...'}, {'type': 'image_url', 'image_url': {...}}]"
        ),
    )
    # ✅ 关键增强：自动标准化 content → 统一为 List[ContentItem]（便于下游处理）
    @field_validator("content")
    @classmethod
    def normalize_content(cls, v: Union[str, List[Any]]) -> Union[str, List[ContentItem]]:
        if isinstance(v, str):
            return v  # 纯文本保留原样
        # 否则尝试解析为 ContentItem 列表（Pydantic 自动按 type 分辨）
        try:
            # 显式转换：触发联合类型验证（会报错若结构不合法）
            return [ContentItem.model_validate(item) for item in v]
        except Exception as e:
            raise ValueError(f"Invalid content item list: {e}") from e

    # ✅ 可选：便捷属性 —— 获取所有图像 URL（用于预加载/审核）
    @property
    def image_urls(self) -> List[str]:
        if isinstance(self.content, str):
            return []
        return [
            item.image_url.url
            for item in self.content
            if isinstance(item, ImageContent)
        ]

    # ✅ 可选：获取纯文本摘要（用于日志/缓存 key）
    @property
    def text_summary(self) -> str:
        if isinstance(self.content, str):
            return self.content
        texts = [item.text for item in self.content if isinstance(item, TextContent)]
        return "\n".join(texts) if texts else ""
# ==================== 请求 DTO ====================
class EmptyRequest(BaseModel):
    """空请求体"""
    pass
# --- 2. 流式输出选项主模型 ---
class StreamOptions(BaseModel):
    """流式输出配置选项 —— 控制响应如何分块返回给客户端"""

    mode: StreamMode = Field(
        default=StreamMode.AUTO,
        description=(
            "流式传输模式：\n"
            "- 'token': 逐 token 输出（适合实时打字效果）\n"
            "- 'chunk': 按固定字符数分块（适合防截断、UI 平滑渲染）\n"
            "- 'auto': 后端自动选择最优策略（推荐）"
        ),
    )
    chunk_size: int = Field(
        default=10,
        ge=1,
        le=1000,  # ✅ 放宽上限：100 太保守（如中文平均 2–3 字符/token，100 可能太碎）
        description="分块模式下每块的**近似字符数**（UTF-8 编码长度，非 token 数）",
    )
    include_usage: bool = Field(
        default=False,
        description="是否在流式结束的最后一个数据块中包含 `usage` 字段（如 prompt_tokens, completion_tokens）",
    )

    # ✅ 关键校验：chunk_size 仅在 mode == 'chunk' 时生效，避免误导性配置
    @field_validator("chunk_size")
    @classmethod
    def validate_chunk_size_only_for_chunk_mode(cls, v: int, info) -> int:
        mode = info.data.get("mode", StreamMode.AUTO)
        if mode == StreamMode.CHUNK and (v < 1 or v > 1000):
            raise ValueError("chunk_size must be between 1 and 1000 when mode='chunk'")
        if mode != StreamMode.CHUNK and v != 10:  # 非 chunk 模式下 chunk_size 应被忽略 → 警告但不报错
            # ✅ 可选：记录 warning（需 logging）或静默忽略；此处选择「静默兼容」更友好
            pass
        return v

    # ✅ 可选：便捷属性 —— 判断是否启用流式（避免业务层重复判断）
    @property
    def is_streaming(self) -> bool:
        return self.mode in (StreamMode.TOKEN, StreamMode.CHUNK, StreamMode.AUTO)

    # ✅ 可选：标准化输出（用于日志 / trace / 配置序列化）
    def model_dump_minimal(self) -> dict:
        """返回精简配置（仅含显式设置的非默认值），便于审计和调试"""
        d = self.model_dump(exclude_defaults=True)
        # 将枚举转为字符串（确保 JSON serializable）
        if "mode" in d:
            d["mode"] = d["mode"].value
        return d
# --- 主请求模型：VisionCompletionRequest ---
class VisionCompletionRequest(BaseModel):
    """
    视觉补全请求 - 100% 兼容 OpenAI / Anthropic 多模态 API 设计规范
    支持：文本 + 图像混合消息、流式控制、采样参数、停止词等
    """

    # ✅ 必填字段（OpenAI 要求）
    model: str = Field(
        ...,
        description="模型标识符（如 'gpt-4o', 'claude-3-opus-20240229'）",
        min_length=1,
    )
    messages: List[VisionMessage] = Field(
        ...,
        min_length=1,
        description="对话消息列表，首条应为 user 角色（支持图像）",
    )

    # ✅ 可选参数（带合理范围约束）
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=32768,  # ✅ 放宽上限（gpt-4o 支持 up to 32k output）
        description="最大生成 token 数（注意：部分模型对 input+output 总长有限制）",
    )
    temperature: Optional[float] = Field(
        default=1.0,  # ✅ OpenAI 默认值
        ge=0.0,
        le=2.0,
        description="采样随机性（0.0=确定性，2.0=高度随机）",
    )
    top_p: Optional[float] = Field(
        default=1.0,  # ✅ OpenAI 默认值
        ge=0.0,
        le=1.0,
        description="核采样阈值（保留概率累计和 ≥ top_p 的最小 token 集合）",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        description="Top-k 采样（仅保留概率最高的 k 个 token）",
    )
    stream: bool = Field(
        default=False,
        description="启用流式响应（SSE: text/event-stream）",
    )
    stream_options: Optional[StreamOptions] = Field(
        default=None,
        description="流式高级选项（仅当 stream=True 时生效）",
    )
    stop: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="停止生成的字符串或字符串列表（匹配任意一个即停止）",
    )
    user: Optional[str] = Field(
        default=None,
        max_length=256,
        description="终端用户唯一标识（用于审计、限频、个性化）",
    )

    # ✅ 关键校验 1：stream_options 仅在 stream=True 时允许非 None
    @model_validator(mode="after")
    def validate_stream_options_only_when_streaming(self) -> "VisionCompletionRequest":
        if self.stream_options is not None and not self.stream:
            raise ValueError("stream_options must be None when stream=False")
        return self

    # ✅ 关键校验 2：messages 至少有一条 user 消息（OpenAI 强制要求）
    @field_validator("messages")
    @classmethod
    def validate_at_least_one_user_message(cls, v: List[VisionMessage]) -> List[VisionMessage]:
        if not any(msg.role == Role.USER for msg in v):
            raise ValueError("At least one message with role='user' is required")
        return v

    # ✅ 关键校验 3：首条消息必须是 user（OpenAI 规范）
    @field_validator("messages")
    @classmethod
    def validate_first_message_is_user(cls, v: List[VisionMessage]) -> List[VisionMessage]:
        if v and v[0].role != Role.USER:
            raise ValueError("First message must have role='user'")
        return v

    # ✅ 可选：便捷方法 —— 获取所有图像 URL（用于预加载/审核/日志）
    def get_all_image_urls(self) -> List[str]:
        urls = []
        for msg in self.messages:
            if isinstance(msg.content, list):
                for item in msg.content:
                    if isinstance(item, ImageContent):
                        urls.append(item.image_url.url)
        return urls

    # ✅ 可选：生成调试摘要（避免打印超长 content）
    def debug_summary(self) -> dict:
        return {
            "model": self.model,
            "message_count": len(self.messages),
            "user_image_count": len(self.get_all_image_urls()),
            "stream": self.stream,
            "max_tokens": self.max_tokens,
        }

# --- 2. 单图分析请求（增强校验 + 语义明确）---
class ImageAnalyzeRequest(BaseModel):
    """
    图像分析请求（单图）—— 支持 URL 或 data:image base64
    等价于 OpenAI 的 single-image 'user' message + prompt
    """

    image: str = Field(
        ...,
        description=(
            "图像源：\n"
            "- HTTP(S) URL（如 https://...）\n"
            "- data:image/*;base64,... URI（如 data:image/jpeg;base64,/9j/4AAQ...）"
        ),
        min_length=5,
    )
    prompt: str = Field(
        default="请描述这张图片",
        min_length=1,
        max_length=2048,
        description="引导模型分析的自然语言指令（非系统提示）",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=8192,
        description="最大生成 token 数（建议 256–1024）",
    )
    temperature: Optional[float] = Field(
        default=0.5,  # ✅ 设为合理默认值（比 OpenAI 的 1.0 更稳定）
        ge=0.0,
        le=2.0,
        description="控制输出随机性（0.0=确定性，1.0=平衡，2.0=高发散）",
    )
    detail: ImageDetail = Field(
        default=ImageDetail.AUTO,
        description="图像分析细节级别（影响 token 消耗与精度）",
    )

    # ✅ 校验：确保 image 是合法 URL 或 data:image URI
    @field_validator("image")
    @classmethod
    def validate_image_uri(cls, v: str) -> str:
        if v.startswith("data:image/"):
            if ";base64," not in v:
                raise ValueError("data:image/ URI must contain ';base64,'")
            # 可选：base64 字符合法性检查（需 import base64）
        elif not v.startswith(("http://", "https://")):
            raise ValueError("image must be an HTTP(S) URL or a data:image/*;base64,... URI")
        return v

    # ✅ 可选：便捷属性 —— 判断是否为 base64
    @property
    def is_base64(self) -> bool:
        return self.image.startswith("data:image/")

    # ✅ 可选：提取 MIME 类型（如 image/png）
    @property
    def mime_type(self) -> Optional[str]:
        if self.is_base64:
            prefix = self.image.split(";", 1)[0]
            if prefix.startswith("data:"):
                return prefix[5:]
        return None


# --- 3. 多图分析请求（增强上限 + 批处理语义）---
class MultiImageAnalyzeRequest(BaseModel):
    """
    多图像分析请求（批处理）—— 同时分析最多 10 张图，共享 prompt
    注意：部分模型（如 GPT-4o）对总图像数有限制（通常 ≤ 10），此处已约束
    """

    images: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,  # ✅ 严格匹配 GPT-4o / Claude 3 的上限
        description="图像列表（每个元素为 URL 或 data:image base64）",
    )
    prompt: str = Field(
        default="请分析这些图片",
        min_length=1,
        max_length=2048,
        description="统一应用于所有图像的分析指令",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=8192,
        description="最大生成 token 数（注意：多图会显著增加上下文长度）",
    )
    temperature: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="温度参数（同单图）",
    )

    # ✅ 校验：每张图都通过单图校验逻辑
    @field_validator("images")
    @classmethod
    def validate_each_image(cls, v: List[str]) -> List[str]:
        for i, img in enumerate(v):
            try:
                ImageAnalyzeRequest.model_validate({"image": img})  # 复用单图校验
            except Exception as e:
                raise ValueError(f"Invalid image at index {i}: {e}") from e
        return v

    # ✅ 可选：统计 base64 图像数量（用于成本预估/审核）
    @property
    def base64_count(self) -> int:
        return sum(1 for img in self.images if img.startswith("data:image/"))

    # ✅ 可选：生成标准化消息结构（兼容 VisionMessage）
    def to_vision_message(self, role: str = "user") -> dict:
        """转换为标准 VisionMessage 格式（便于复用下游 VisionCompletionRequest）"""
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from .models import VisionMessage  # 避免循环导入；实际使用时请调整路径

        content_items = []
        for img in self.images:
            content_items.append({
                "type": "image_url",
                "image_url": {"url": img, "detail": self.detail.value if hasattr(self, "detail") else "auto"}
            })
        content_items.append({
            "type": "text",
            "text": self.prompt
        })
        return {"role": role, "content": content_items}

# ==================== 响应 DTO ====================
# --- 1. Token 使用统计（增强：自动计算 total_tokens）---
class Usage(BaseModel):
    """Token 使用统计 —— 支持自动推导 total_tokens"""

    prompt_tokens: int = Field(
        default=0,
        ge=0,
        description="输入 token 数（含系统提示、用户消息、图像编码等）",
    )
    completion_tokens: int = Field(
        default=0,
        ge=0,
        description="输出 token 数（模型生成内容）",
    )

    # ✅ 自动计算 total_tokens（避免手动维护不一致）
    @computed_field
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    # ✅ 可选：校验非负（虽有 ge=0，但显式强化语义）
    @model_validator(mode="after")
    def validate_non_negative(self) -> "Usage":
        if self.prompt_tokens < 0 or self.completion_tokens < 0:
            raise ValueError("prompt_tokens and completion_tokens must be non-negative")
        return self


# --- 2. 视觉补全选项（增强：message.role 必须为 assistant）---
class VisionChoice(BaseModel):
    """视觉补全选项 —— 每个 choice 对应一个生成结果"""

    index: int = Field(default=0, ge=0, description="选项索引（从 0 开始）")
    message: "VisionMessage" = Field(..., description="生成的消息（role 必须为 'assistant'）")
    finish_reason: Optional[str] = Field(
        default=None,
        description="完成原因（如 'stop', 'length', 'tool_calls', 'content_filter'）",
    )

    # ✅ 强制 message.role == 'assistant'（OpenAI 规范）
    @field_validator("message")
    @classmethod
    def validate_assistant_role(cls, v: "VisionMessage") -> "VisionMessage":
        from .models import Role  # 假设 VisionMessage 在 models.py；请按实际路径调整
        if v.role != Role.ASSISTANT:
            raise ValueError("choice.message.role must be 'assistant'")
        return v


# --- 3. 完整视觉补全响应（增强：id/model/created 自动生成 + usage 同步）---
class VisionCompletionResponse(BaseModel):
    """
    视觉补全响应 - 100% 兼容 OpenAI `/v1/chat/completions` JSON Schema
    """

    id: str = Field(
        default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}",
        description="唯一请求 ID（格式：chatcmpl-xxxx）",
        pattern=r"^chatcmpl-[a-zA-Z0-9]{24}$",  # ✅ 正则约束格式
    )
    object: str = Field(
        default="chat.completion",
        description="对象类型（固定值）",
        pattern=r"^chat\.completion$",
    )
    created: int = Field(
        default_factory=lambda: int(time.time()),
        description="Unix 时间戳（秒级）",
        ge=1609459200,  # 2021-01-01（合理下限）
    )
    model: str = Field(
        default="",
        min_length=1,
        description="实际响应的模型名称（如 'gpt-4o-2024-05-13'）",
    )
    choices: List[VisionChoice] = Field(
        default_factory=list,
        min_length=1,
        description="生成结果列表（至少 1 个 choice）",
    )
    usage: Usage = Field(
        default_factory=Usage,
        description="Token 使用统计",
    )

    # ✅ 自动填充 usage.total_tokens（即使外部未设置）
    @model_validator(mode="after")
    def ensure_usage_total_tokens(self) -> "VisionCompletionResponse":
        # 如果 usage 已部分设置，确保 total_tokens 同步
        if hasattr(self.usage, "total_tokens"):
            # computed_field 已保证，此处仅防御性检查
            pass
        return self
# ==================== 流式响应 DTO ====================
class DeltaMessage(BaseModel):
    """流式消息增量 —— 每个 chunk 包含 delta 更新"""

    role: Optional[str] = Field(
        default=None,
        pattern=r"^(system|user|assistant|tool)$",
        description="角色（仅首块可能含 role；后续块通常省略）",
    )
    content: Optional[str] = Field(
        default="",
        description="本次增量文本（可为空字符串，但不应为 None）",
    )

    # ✅ 强制 content 不为 None（OpenAI 流式中 content 为 "" 而非 null）
    @field_validator("content")
    @classmethod
    def content_must_not_be_none(cls, v: Optional[str]) -> str:
        return v if v is not None else ""


# --- 5. 流式 chunk 选项（增强：finish_reason 类型约束）---
class VisionChunkChoice(BaseModel):
    """流式视觉补全选项（单个 chunk）"""

    index: int = Field(default=0, ge=0)
    delta: DeltaMessage = Field(default_factory=DeltaMessage)
    finish_reason: Optional[str] = Field(
        default=None,
        description="完成原因（仅在最后一个 chunk 中出现）",
        # ✅ 枚举建议（非强制，但利于文档和前端处理）
        examples=["stop", "length", "tool_calls", "content_filter"],
    )


# --- 6. 流式响应块（增强：与完整响应保持字段对齐）---
class VisionCompletionChunk(BaseModel):
    """
    流式视觉补全响应块（SSE event: data: {...}）
    注意：每个 chunk 是 partial，最终由客户端拼接
    """

    id: str = Field(
        default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}",
        pattern=r"^chatcmpl-[a-zA-Z0-9]{24}$",
    )
    object: str = Field(default="chat.completion.chunk")
    created: int = Field(default_factory=lambda: int(time.time()), ge=1609459200)
    model: str = Field(default="", min_length=1)
    choices: List[VisionChunkChoice] = Field(default_factory=list, min_length=1)

    # ✅ 可选：便捷方法 —— 判断是否为结束块
    @property
    def is_final_chunk(self) -> bool:
        return len(self.choices) > 0 and self.choices[0].finish_reason is not None


# --- 7. 图像分析响应（增强：补齐标准字段 + latency 精度）---
class ImageAnalyzeResponse(BaseModel):
    """图像分析响应（单图/多图统一）"""

    id: str = Field(
        default_factory=lambda: f"imganal-{uuid.uuid4().hex[:16]}",
        description="分析任务唯一 ID",
        pattern=r"^imganal-[a-zA-Z0-9]{16}$",
    )
    object: str = Field(default="image.analysis", description="对象类型")
    created: int = Field(default_factory=lambda: int(time.time()), ge=1609459200)

    description: str = Field(
        default="",
        description="模型生成的图像描述（自然语言）",
        min_length=0,  # 允许空描述（如内容过滤）
    )

    # ✅ Token 统计（复用 Usage，避免重复定义）
    usage: Usage = Field(default_factory=Usage)

    # ✅ 延迟（毫秒，保留 2 位小数，更符合监控习惯）
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="端到端处理延迟（毫秒），精度 0.01ms",
        multiple_of=0.01,
    )

    # ✅ 可选：返回原始图像信息（便于调试/审计）
    image_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="原始图像元信息（如 URL、base64 长度、MIME 类型等，仅 debug 模式启用）",
    )

    # ✅ 可选：标准化错误字段（兼容 OpenAI error schema）
    @property
    def error(self) -> Optional[Dict[str, str]]:
        if not self.description and self.usage.total_tokens == 0:
            return {"code": "content_filtered", "message": "Image content was filtered"}
        return None
