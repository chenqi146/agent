'''
Embedding 请求/响应 DTO 定义
兼容 OpenAI Embeddings API 格式
'''
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
import time
import uuid


# ==================== 请求 DTO ====================

class EmbeddingRequest(BaseModel):
    """
    Embedding 请求 - 兼容 OpenAI /v1/embeddings
    """
    model: Optional[str] = Field(default=None, description="模型名称（可选）")
    input: Union[str, List[str]] = Field(..., description="输入文本，支持单条或批量")
    encoding_format: str = Field(default="float", description="编码格式: float 或 base64")
    dimensions: Optional[int] = Field(default=None, description="输出向量维度（可选，部分模型支持）")
    user: Optional[str] = Field(default=None, description="用户标识")


# ==================== 响应 DTO ====================

class EmbeddingUsage(BaseModel):
    """Token 使用统计"""
    prompt_tokens: int = Field(default=0, description="输入 token 数")
    total_tokens: int = Field(default=0, description="总 token 数")


class EmbeddingData(BaseModel):
    """单个 Embedding 数据"""
    object: str = Field(default="embedding", description="对象类型")
    index: int = Field(default=0, description="索引")
    embedding: List[float] = Field(default_factory=list, description="向量数据")


class EmbeddingResponse(BaseModel):
    """
    Embedding 响应 - 兼容 OpenAI 格式
    """
    object: str = Field(default="list", description="对象类型")
    model: str = Field(default="", description="模型名称")
    data: List[EmbeddingData] = Field(default_factory=list, description="Embedding 列表")
    usage: EmbeddingUsage = Field(default_factory=EmbeddingUsage, description="Token 使用统计")


# ==================== 通用请求 DTO ====================

class EmptyRequest(BaseModel):
    """空请求体（用于无参数的 POST 接口）"""
    pass
