'''
Reranker 请求/响应 DTO 定义
兼容 Jina AI / Cohere Rerank API 格式
'''
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


# ==================== 请求 DTO ====================

class RerankRequest(BaseModel):
    """
    Rerank 请求 - 兼容 Jina/Cohere /v1/rerank
    """
    model: Optional[str] = Field(default=None, description="模型名称（可选）")
    query: str = Field(..., description="查询文本")
    documents: List[str] = Field(..., description="待排序的文档列表")
    top_n: Optional[int] = Field(default=None, description="返回前N个结果（默认返回全部）")
    return_documents: bool = Field(default=True, description="是否返回文档内容")


class ScoreRequest(BaseModel):
    """
    Score 请求 - 对 query-document 对评分
    """
    query: str = Field(..., description="查询文本")
    documents: List[str] = Field(..., description="文档列表")


# ==================== 响应 DTO ====================

class DocumentInfo(BaseModel):
    """文档信息"""
    text: str = Field(default="", description="文档内容")


class RerankResultItem(BaseModel):
    """单个重排序结果"""
    index: int = Field(default=0, description="原始索引")
    relevance_score: float = Field(default=0.0, description="相关性分数")
    document: Optional[DocumentInfo] = Field(default=None, description="文档信息")


class RerankResponse(BaseModel):
    """
    Rerank 响应 - 兼容 Jina/Cohere 格式
    """
    model: str = Field(default="", description="模型名称")
    results: List[RerankResultItem] = Field(default_factory=list, description="重排序结果列表")
    usage: Dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "total_tokens": 0})


class ScoreResponse(BaseModel):
    """
    Score 响应
    """
    model: str = Field(default="", description="模型名称")
    scores: List[float] = Field(default_factory=list, description="分数列表")
    latency_ms: float = Field(default=0.0, description="响应延迟(ms)")


# ==================== 通用请求 DTO ====================

class EmptyRequest(BaseModel):
    """空请求体（用于无参数的 POST 接口）"""
    pass
