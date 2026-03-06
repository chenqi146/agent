'''
VLM 请求/响应 DTO 定义
视觉语言模型接口数据传输对象，兼容 OpenAI Vision API 格式
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


class ImageDetail(str, Enum):
    """图像细节级别"""
    LOW = "low"
    HIGH = "high"
    AUTO = "auto"


class StreamMode(str, Enum):
    """流式输出模式"""
    TOKEN = "token"      # 真正的 token 级流式（使用 AsyncLLMEngine）
    CHUNK = "chunk"      # 分块流式（先生成完再分块发送）
    AUTO = "auto"        # 自动选择（默认使用 token 模式）


# ==================== 图像内容 DTO ====================

class ImageUrl(BaseModel):
    """图像 URL 内容"""
    url: str = Field(..., description="图像URL或base64编码（data:image/jpeg;base64,...）")
    detail: ImageDetail = Field(default=ImageDetail.AUTO, description="图像细节级别")


class TextContent(BaseModel):
    """文本内容"""
    type: str = Field(default="text", description="内容类型")
    text: str = Field(..., description="文本内容")


class ImageContent(BaseModel):
    """图像内容"""
    type: str = Field(default="image_url", description="内容类型")
    image_url: ImageUrl = Field(..., description="图像URL信息")


# 消息内容可以是文本或图像
ContentItem = Union[TextContent, ImageContent]


class VisionMessage(BaseModel):
    """视觉消息 - 支持多模态内容"""
    role: Role = Field(..., description="消息角色")
    content: Union[str, List[ContentItem]] = Field(..., description="消息内容（文本或多模态内容列表）")


# ==================== 请求 DTO ====================

class EmptyRequest(BaseModel):
    """空请求体"""
    pass


class StreamOptions(BaseModel):
    """流式输出选项"""
    mode: StreamMode = Field(default=StreamMode.AUTO, description="流式模式: token(真正流式)/chunk(分块)/auto(自动)")
    chunk_size: int = Field(default=10, ge=1, le=100, description="分块模式下每块字符数")
    include_usage: bool = Field(default=False, description="是否在最后一个块中包含 usage 信息")


class VisionCompletionRequest(BaseModel):
    """
    视觉补全请求 - 兼容 OpenAI Vision API
    """
    model: Optional[str] = Field(default=None, description="模型名称（可选）")
    messages: List[VisionMessage] = Field(..., min_length=1, description="对话历史（支持图像）")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192, description="最大生成token数")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="温度参数")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Top-p采样参数")
    top_k: Optional[int] = Field(default=None, ge=1, description="Top-k采样参数")
    stream: bool = Field(default=False, description="是否流式输出")
    stream_options: Optional[StreamOptions] = Field(default=None, description="流式输出选项")
    stop: Optional[Union[str, List[str]]] = Field(default=None, description="停止词")
    user: Optional[str] = Field(default=None, description="用户标识")


class ImageAnalyzeRequest(BaseModel):
    """
    图像分析请求 - 简化版接口
    """
    image: str = Field(..., description="图像URL或base64编码")
    prompt: str = Field(default="请描述这张图片", description="分析提示词")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192, description="最大生成token数")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="温度参数")
    detail: ImageDetail = Field(default=ImageDetail.AUTO, description="图像细节级别")


class MultiImageAnalyzeRequest(BaseModel):
    """
    多图像分析请求
    """
    images: List[str] = Field(..., min_length=1, max_length=10, description="图像URL或base64编码列表")
    prompt: str = Field(default="请分析这些图片", description="分析提示词")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192, description="最大生成token数")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="温度参数")


# ==================== 响应 DTO ====================

class Usage(BaseModel):
    """Token使用统计"""
    prompt_tokens: int = Field(default=0, description="输入token数")
    completion_tokens: int = Field(default=0, description="输出token数")
    total_tokens: int = Field(default=0, description="总token数")


class VisionChoice(BaseModel):
    """视觉补全选项"""
    index: int = Field(default=0, description="选项索引")
    message: VisionMessage = Field(..., description="生成的消息")
    finish_reason: Optional[str] = Field(default=None, description="完成原因")


class VisionCompletionResponse(BaseModel):
    """
    视觉补全响应 - 兼容 OpenAI 格式
    """
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}", description="请求ID")
    object: str = Field(default="chat.completion", description="对象类型")
    created: int = Field(default_factory=lambda: int(time.time()), description="创建时间戳")
    model: str = Field(default="", description="模型名称")
    choices: List[VisionChoice] = Field(default_factory=list, description="生成结果列表")
    usage: Usage = Field(default_factory=Usage, description="Token使用统计")


# ==================== 流式响应 DTO ====================

class DeltaMessage(BaseModel):
    """流式消息增量"""
    role: Optional[str] = Field(default=None, description="消息角色")
    content: Optional[str] = Field(default=None, description="消息内容增量")


class VisionChunkChoice(BaseModel):
    """流式视觉补全选项"""
    index: int = Field(default=0, description="选项索引")
    delta: DeltaMessage = Field(default_factory=DeltaMessage, description="消息增量")
    finish_reason: Optional[str] = Field(default=None, description="完成原因")


class VisionCompletionChunk(BaseModel):
    """
    流式视觉补全响应块
    """
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}", description="请求ID")
    object: str = Field(default="chat.completion.chunk", description="对象类型")
    created: int = Field(default_factory=lambda: int(time.time()), description="创建时间戳")
    model: str = Field(default="", description="模型名称")
    choices: List[VisionChunkChoice] = Field(default_factory=list, description="生成结果列表")


# ==================== 图像分析响应 DTO ====================

class ImageAnalyzeResponse(BaseModel):
    """图像分析响应"""
    description: str = Field(default="", description="图像描述")
    prompt_tokens: int = Field(default=0, description="输入token数")
    completion_tokens: int = Field(default=0, description="输出token数")
    latency_ms: float = Field(default=0.0, description="延迟(毫秒)")

