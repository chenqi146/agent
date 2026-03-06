from typing import Optional, List

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class MemoryConfig(BaseModel):
    """
    记忆配置 DTO，对应 memory_config 表中的一条记录。

    前端字段采用 camelCase 命名，通过 alias 与后端字段映射：
    - memoryHalfLife <-> memory_half_life
    - autoForgetEnabled <-> auto_forget_enabled
    - importanceWeight <-> importance_weight
    - recencyWeight <-> freshness_weight
    - frequencyWeight <-> frequency_weight
    - compressThreshold <-> compress_trigger_count
    - summaryStyle <-> summary_style
    - contextMaxItems <-> context_max_count
    - contextRetentionMinutes <-> context_retention_minutes
    - contextMaxCharsPerItem <-> single_item_max_chars
    - contextIncludeInLongTerm <-> important_context_to_long_term
    """

    model_config = ConfigDict(populate_by_name=True)

    memory_half_life: int = Field(
        default=24,
        ge=1,
        le=168,
        alias="memoryHalfLife",
        description="记忆半衰期（小时）",
    )
    auto_forget_enabled: bool = Field(
        default=True,
        alias="autoForgetEnabled",
        description="启用自动遗忘低价值记忆",
    )

    importance_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        alias="importanceWeight",
        description="重要性权重（0-1）",
    )
    freshness_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        alias="recencyWeight",
        description="新鲜度权重（0-1）",
    )
    frequency_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        alias="frequencyWeight",
        description="出现频次权重（0-1）",
    )

    compress_trigger_count: int = Field(
        default=200,
        ge=10,
        alias="compressThreshold",
        description="压缩触发条数",
    )
    summary_style: str = Field(
        default="compact_technical",
        max_length=50,
        alias="summaryStyle",
        description="摘要风格",
    )

    context_max_count: int = Field(
        default=20,
        ge=1,
        alias="contextMaxItems",
        description="上下文最大条数",
    )
    context_retention_minutes: int = Field(
        default=60,
        ge=1,
        alias="contextRetentionMinutes",
        description="上下文保留时长（分钟）",
    )
    single_item_max_chars: int = Field(
        default=500,
        ge=50,
        alias="contextMaxCharsPerItem",
        description="单条上下文最大字符数",
    )
    important_context_to_long_term: bool = Field(
        default=True,
        alias="contextIncludeInLongTerm",
        description="重要上下文是否写入长期记忆",
    )

    description: Optional[str] = Field(
        default=None,
        alias="description",
        description="配置描述说明",
    )


class MemoryConfigApiRequest(BaseModel):
    """
    前端保存记忆配置请求包裹结构：
    { tag, timestamp, data: MemoryConfig }
    """

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: MemoryConfig = Field(..., description="记忆配置内容")


class MemoryContentItem(BaseModel):
    """
    单条记忆内容记录。
    """

    id: str = Field(..., description="记忆ID")
    time: str = Field(..., description="记忆发生时间，ISO字符串")
    category: str = Field(..., alias="category", description="记忆类型")
    role_type: str = Field(..., alias="roleType", description="角色类型")
    fact: str = Field(..., alias="fact", description="事实摘要")
    detail: str = Field(..., alias="detail", description="详细内容")


class MemoryContentSearchRequest(BaseModel):
    """
    记忆内容查询条件。
    前端字段均使用 camelCase，通过 alias 映射。
    """

    time_range: str = Field(
        default="last1d",
        alias="timeRange",
        description="时间范围: last1d|last7d|last30d|last90d|all",
    )
    category: str = Field(
        default="all",
        alias="category",
        description="记忆类型: all|preference|device|query|system",
    )
    role_type: str = Field(
        default="all",
        alias="roleType",
        description="角色类型: all|police|customerService|analyst",
    )
    keyword: Optional[str] = Field(
        default=None,
        alias="keyword",
        description="按事实或内容关键字搜索",
    )
    page: int = Field(default=1, ge=1, alias="page", description="页码")
    page_size: int = Field(
        default=100,
        ge=1,
        le=500,
        alias="pageSize",
        description="分页大小",
    )


class MemoryContentSearchApiRequest(BaseModel):
    """
    记忆内容查询请求包裹结构。
    """

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: MemoryContentSearchRequest = Field(..., description="查询条件")


class MemoryContentDeleteRequest(BaseModel):
    """
    删除指定记忆记录请求。
    """

    ids: List[str] = Field(..., description="待删除的记忆ID列表")


class MemoryContentDeleteApiRequest(BaseModel):
    """
    记忆内容批量删除请求包裹。
    """

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: MemoryContentDeleteRequest = Field(..., description="删除参数")


class MemoryContentClearApiRequest(BaseModel):
    """
    清空当前智能体所有记忆内容。
    data 字段预留，目前不需要任何业务参数。
    """

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: Optional[dict] = Field(default=None, description="预留字段")
