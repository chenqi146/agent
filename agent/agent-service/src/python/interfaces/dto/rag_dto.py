from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field
from pydantic import ConfigDict

class StrEnum(str,Enum):
    def __str__(self):
        return str.__str__(self)
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()


class KnowledgeBaseStatus(StrEnum):
    """知识库状态"""

    ENABLED = "enabled"      # 启用
    DISABLED = "disabled"    # 禁用
    BUILDING = "building"    # 向量构建中


class KnowledgeBaseType(StrEnum):
    """知识库类型"""

    DOCUMENT = "document"    # 文档库（pdf/office/txt/html）
    FAQ = "faq"              # FAQ 库
    STRUCTURED = "structured"  # 结构化数据


class ChunkStrategy(StrEnum):
    """文档切割策略"""

    FIXED = "fixed"        # 固定长度切割
    RECURSIVE = "recursive"  # 递归式切割
    SLIDING = "sliding"      # 滑动窗口
    SEMANTIC = "semantic"    # 语义切割


class FileProcessingStatus(StrEnum):
    """文件处理状态"""

    NOT_STARTED = "not_started"           # 0 - 未开始
    UPLOADING = "uploading"              # 1 - 正在上传文件
    VECTORIZING = "vectorizing"          # 2 - 正在向量化知识
    COMPLETED = "completed"              # 3 - 已完成
    FAILED = "failed"                   # 4 - 失败


class ChunkParams(BaseModel):
    """文档切割参数（不同策略下可用字段不同，后续可扩展）"""

    chunkLength: int | None = Field(
        default=None,
        ge=1,
        description="切割长度（字符数），固定长度 / 滑动窗口必填",
    )
    chunkOverlap: int | None = Field(
        default=None,
        ge=0,
        description="重叠长度（字符数），滑动窗口可选",
    )
    semanticModel: str | None = Field(
        default=None,
        max_length=128,
        description="语义切割所使用的模型标识",
    )


class KnowledgeBaseInfo(BaseModel):
    """知识库基础信息（列表 & 详情统一使用，对应 rag_tbl）"""

    id: int = Field(..., description="知识库ID（rag_tbl.id）")
    name: str = Field(..., min_length=1, max_length=50, description="知识库名称（rag_tbl.rag_name）")
    kb_type: KnowledgeBaseType = Field(
        default=KnowledgeBaseType.DOCUMENT, description="知识库类型（rag_tbl.type）"
    )
    status: KnowledgeBaseStatus = Field(
        default=KnowledgeBaseStatus.ENABLED, description="知识库状态（由 rag_tbl.status 映射）"
    )
    created_at: int = Field(
        ..., ge=0, description="创建时间戳（毫秒，用于前端格式化显示，对应 rag_tbl.create_time）"
    )
    updated_at: int = Field(
        ..., ge=0, description="最后更新时间戳（毫秒，用于前端格式化显示，对应 rag_tbl.update_time）"
    )
    file_capacity: int = Field(
        default=0, ge=0, description="知识库容量（rag_tbl.file_capacity，单位由业务约定）"
    )
    file_count: int = Field(
        default=0, ge=0, description="知识库中文件总数（rag_tbl.file_count）"
    )
    binding_user: int = Field(
        default=0, ge=0, description="绑定用户ID（rag_tbl.binding_user）"
    )


class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库请求"""

    name: str = Field(..., min_length=1, max_length=128, description="知识库名称")
    kb_type: KnowledgeBaseType = Field(
        default=KnowledgeBaseType.DOCUMENT, description="知识库类型"
    )
    description: Optional[str] = Field(
        default=None, max_length=512, description="知识库描述"
    )
    chunk_strategy: ChunkStrategy = Field(
        default=ChunkStrategy.FIXED, description="文档切割策略"
    )
    chunk_params: Optional[ChunkParams] = Field(
        default=None, description="文档切割策略参数（根据不同策略携带不同字段）"
    )


class KnowledgeBaseUpdateRequest(BaseModel):
    """更新知识库基本信息"""

    id: int = Field(..., description="知识库ID")
    name: Optional[str] = Field(
        default=None, min_length=1, max_length=128, description="知识库名称"
    )
    description: Optional[str] = Field(
        default=None, max_length=512, description="知识库描述"
    )
    status: Optional[KnowledgeBaseStatus] = Field(
        default=None, description="知识库状态"
    )


class KnowledgeBaseIdRequest(BaseModel):
    """仅携带知识库ID的请求"""

    id: int = Field(..., description="知识库ID")


class KnowledgeBaseListRequest(BaseModel):
    """知识库分页查询请求"""

    model_config = ConfigDict(populate_by_name=True)

    page_no: int = Field(
        default=1, ge=1, alias="page", description="页码，从 1 开始"
    )
    page_size: int = Field(
        default=10, ge=1, le=100, alias="size", description="每页数量，最大 100"
    )
    keyword: Optional[str] = Field(
        default=None, max_length=128, description="按名称模糊搜索关键字"
    )


class KnowledgeBasePage(BaseModel):
    """知识库分页结果"""

    items: List[KnowledgeBaseInfo] = Field(
        default_factory=list, description="当前页数据"
    )
    total: int = Field(default=0, ge=0, description="总记录数")
    page_no: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")


class RagQueryRequest(BaseModel):
    """RAG 问答请求"""

    kb_id: int = Field(..., description="目标知识库ID")
    query: str = Field(..., min_length=1, max_length=1024, description="用户问题")
    top_k: int = Field(
        default=5, ge=1, le=50, description="召回文档数量（TopK）"
    )


class RagQueryAnswer(BaseModel):
    """RAG 问答结果"""

    answer: str = Field(..., description="生成的回答")
    kb_id: int = Field(..., description="使用的知识库ID")
    query: str = Field(..., description="原始问题")
    top_k: int = Field(..., ge=1, le=50, description="召回文档数量")
    source_documents: List[str] = Field(
        default_factory=list, description="简要的来源片段列表（仅用于展示）"
    )


class HybridRagQueryRequest(BaseModel):
    """混合 RAG 查询请求"""

    kb_id: int = Field(..., description="目标知识库ID")
    query: str = Field(..., min_length=1, max_length=1024, description="用户问题")
    top_k: int = Field(
        default=5, ge=1, le=50, description="召回文档数量（TopK）"
    )
    similarity_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="相似度阈值"
    )


class HybridRagQueryResponse(BaseModel):
    """混合 RAG 查询响应"""

    original_query: str = Field(..., description="原始查询")
    enhanced_query: str = Field(..., description="增强后的查询")
    related_concepts: List[str] = Field(..., description="提取的相关概念")
    results: List[Dict[str, Any]] = Field(..., description="最终召回的知识片段列表")


class FileInfo(BaseModel):
    """前端上报的文件基础信息"""

    name: str = Field(..., description="文件名称")
    size: int = Field(..., ge=0, description="文件大小（字节）")
    type: Optional[str] = Field(default=None, description="MIME 类型")
    lastModified: Optional[str] = Field(
        default=None, description="最后修改时间（ISO 字符串，可选）"
    )
    charCount: Optional[int] = Field(
        default=None, ge=0, description="文本字符数（仅文本文件可选）"
    )


class FileProcessRequest(BaseModel):
    """知识库文件处理请求（文件已上传至 MinIO，仅做元数据入库等）"""

    filename: str = Field(..., description="MinIO 对象名 / 文件路径")
    fileInfo: FileInfo = Field(..., description="文件基础信息")
    command: str = Field(..., min_length=1, max_length=32, description="处理指令（create/append 等）")
    kbId: Optional[int] = Field(default=None, description="目标知识库ID")
    chunkStrategy: ChunkStrategy = Field(
        default=ChunkStrategy.FIXED, description="文档切割策略"
    )
    chunkParams: Optional[ChunkParams] = Field(
        default=None, description="文档切割参数"
    )


# ==================== 前端通用请求包裹结构 ====================


class KnowledgeBaseCreateApiRequest(BaseModel):
    """前端创建知识库请求包裹：{ tag, timestamp, data: KnowledgeBaseCreateRequest }"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: KnowledgeBaseCreateRequest = Field(..., description="实际业务参数")


class KnowledgeBaseUpdateApiRequest(BaseModel):
    """前端更新知识库请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: KnowledgeBaseUpdateRequest = Field(..., description="实际业务参数")


class KnowledgeBaseIdApiRequest(BaseModel):
    """前端按 ID 操作知识库（详情 / 删除）请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: KnowledgeBaseIdRequest = Field(..., description="实际业务参数")


class KnowledgeBaseListApiRequest(BaseModel):
    """前端分页查询知识库列表请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: KnowledgeBaseListRequest = Field(..., description="实际业务参数")


class RagQueryApiRequest(BaseModel):
    """前端 RAG 查询请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: RagQueryRequest = Field(..., description="实际业务参数")


class HybridRagQueryApiRequest(BaseModel):
    """前端混合 RAG 查询请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: HybridRagQueryRequest = Field(..., description="实际业务参数")


class FileProcessApiRequest(BaseModel):
    """前端文件处理请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: FileProcessRequest = Field(..., description="实际业务参数")


class FileVectorizationStatusRequest(BaseModel):
    """文件向量化状态查询请求。支持按 file_id 或 file_name 查询，二选一；kb_id 必填。"""

    file_id: Optional[int] = Field(default=None, description="文件记录ID（与 file_name 二选一）")
    file_name: Optional[str] = Field(default=None, description="文件名称（与 file_id 二选一）")
    kb_id: int = Field(..., description="知识库ID")


class FileVectorizationStatusResponse(BaseModel):
    """文件向量化状态查询响应"""

    file_name: str = Field(..., description="文件名称")
    kb_id: int = Field(..., description="知识库ID")
    is_vectorized: bool = Field(..., description="是否已向量化")
    file_id: Optional[int] = Field(default=None, description="文件记录ID（如果存在）")
    embedding_status: Optional[int] = Field(default=None, description="嵌入处理状态（0-未开始，1-正在上传文件，2-正在向量化知识，3-已完成，4-失败）")
    embedding_status_text: Optional[str] = Field(default=None, description="处理状态文本描述")
    embedding_progress: Optional[float] = Field(default=None, description="向量化进度（0.0-1.0）")
    error_message: Optional[str] = Field(default=None, description="错误信息（如果有）")
    processing_status: Optional[str] = Field(default=None, description="前端用：pending|processing|completed|failed，与 embedding_status 对应")
    
    def __init__(self, **data):
        super().__init__(**data)
        # 自动设置状态文本描述
        if self.embedding_status is not None:
            status_map = {
                0: "未开始",
                1: "正在上传文件", 
                2: "正在向量化知识",
                3: "已完成",
                4: "失败"
            }
            self.embedding_status_text = status_map.get(self.embedding_status, "未知状态")
            # 供前端轮询判断：pending / processing / completed / failed
            if self.embedding_status == 3:
                self.processing_status = "completed"
            elif self.embedding_status == 4:
                self.processing_status = "failed"
            elif self.embedding_status in (1, 2):
                self.processing_status = "processing"
            else:
                self.processing_status = "pending"


class FileVectorizationStatusApiRequest(BaseModel):
    """前端文件向量化状态查询请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: FileVectorizationStatusRequest = Field(..., description="实际业务参数")


class FileIdWithKbRequest(BaseModel):
    """按文件ID和知识库ID操作单个文件（删除 / 下载等）"""

    file_id: int = Field(..., description="文件记录ID")
    kb_id: int = Field(..., description="知识库ID")


class FileIdWithKbApiRequest(BaseModel):
    """前端按文件ID操作文件（删除 / 下载）请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: FileIdWithKbRequest = Field(..., description="实际业务参数")


class FileUpdateStatusRequest(BaseModel):
    """更新文件启用状态请求"""

    file_id: int = Field(..., description="文件记录ID")
    kb_id: int = Field(..., description="知识库ID")
    status: int = Field(..., description="文件状态：1=启用，0=禁用")


class FileUpdateStatusApiRequest(BaseModel):
    """前端更新文件状态请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: FileUpdateStatusRequest = Field(..., description="实际业务参数")


class KnowledgeItemInfo(BaseModel):
    """知识信息列表中的单条记录（当前按文件维度聚合）"""

    id: int = Field(..., description="记录ID，对应关联文件ID")
    file_name: str = Field(..., description="关联文件名称")
    recall_count: int = Field(default=0, ge=0, description="召回次数")
    last_access_time: Optional[str] = Field(
        default=None, description="最后检索时间（暂未采集，预留字段）"
    )
    avg_score: Optional[float] = Field(
        default=None, description="平均检索得分（暂未采集，预留字段）"
    )
    instruction_score: Optional[float] = Field(
        default=None, description="指令评分（暂未采集，预留字段）"
    )
    relevance_score: Optional[float] = Field(
        default=None, description="相关性评分（暂未采集，预留字段）"
    )
    is_noise: bool = Field(default=False, description="是否为噪音（预留字段）")
    is_redundant: bool = Field(default=False, description="是否冗余（预留字段）")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")
    qdrant_vector_id: Optional[str] = Field(default=None, description="Qdrant向量ID")
    neo4j_node_id: Optional[str] = Field(default=None, description="Neo4j节点ID")


class KnowledgeItemListRequest(BaseModel):
    """知识信息列表查询请求（按知识库ID）"""

    kb_id: int = Field(..., description="知识库ID")
    min_recall_count: Optional[int] = Field(
        default=None, ge=0, description="最小召回次数"
    )
    max_recall_count: Optional[int] = Field(
        default=None, ge=0, description="最大召回次数"
    )
    recent_days: Optional[int] = Field(
        default=None, ge=1, le=365, description="最近多少天内的记录"
    )
    sort_by: Optional[str] = Field(
        default=None, description="排序字段: recall_count | upload_time"
    )
    sort_order: Optional[str] = Field(
        default="desc", description="排序方向: asc | desc"
    )


class KnowledgeItemListApiRequest(BaseModel):
    """前端查询知识信息列表请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: KnowledgeItemListRequest = Field(..., description="实际业务参数")


# ===================== 知识片段（rag_knowledge_segment_tbl） =====================

class KnowledgeSegmentInfo(BaseModel):
    """知识片段基础信息（列表展示用）"""

    id: int = Field(..., description="片段唯一ID")
    title: str = Field(default="", description="片段标题")
    content: Optional[str] = Field(default=None, description="片段详细内容")
    summary: Optional[str] = Field(default=None, description="内容摘要")
    snippet_type: Optional[str] = Field(default="text", description="片段类型")
    sort_index: Optional[int] = Field(default=9999, description="排序索引")
    status: int = Field(default=1, description="状态: 0-禁用, 1-草稿, 2-启用")
    recall_count: int = Field(default=0, description="召回次数")
    last_search_time: Optional[str] = Field(default=None, description="最后搜索时间")
    average_retrieval_score: Optional[float] = Field(default=None, description="平均检索分数")
    command_score: Optional[float] = Field(default=None, description="命令评分")
    relevance_score: Optional[float] = Field(default=None, description="相关性评分")
    is_noise: bool = Field(default=False, description="是否为噪声片段")
    is_redundant: bool = Field(default=False, description="是否为冗余片段")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")


class KnowledgeSegmentListRequest(BaseModel):
    """查询知识片段列表请求（按文件维度）"""

    file_id: int = Field(..., description="关联文件ID（rag_file_tbl.id）")
    page_no: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    status: Optional[int] = Field(default=None, description="状态过滤: 0/1/2，缺省为全部")
    sort_by: Optional[str] = Field(default=None, description="排序字段: recall_count, updated_at")
    sort_order: Optional[str] = Field(default="desc", description="排序方向: asc, desc")


class KnowledgeSegmentListApiRequest(BaseModel):
    """前端查询知识片段列表请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: KnowledgeSegmentListRequest = Field(..., description="实际业务参数")

class KnowledgeSegmentCreateRequest(BaseModel):
    """创建知识片段请求"""

    file_id: int = Field(..., description="所属文件ID")
    content: str = Field(..., min_length=1, description="内容")
    status: int = Field(default=2, ge=0, le=2, description="状态：0-禁用, 1-草稿, 2-启用")
    title: Optional[str] = Field(default=None, description="标题")


class KnowledgeSegmentCreateApiRequest(BaseModel):
    """前端创建知识片段请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: KnowledgeSegmentCreateRequest = Field(..., description="实际业务参数")


class KnowledgeSegmentUpdateRequest(BaseModel):
    """更新知识片段请求"""

    id: int = Field(..., description="知识片段ID")
    content: Optional[str] = Field(default=None, min_length=1, description="内容")
    status: Optional[int] = Field(default=None, ge=0, le=2, description="状态：0-禁用, 1-草稿, 2-启用")
    title: Optional[str] = Field(default=None, description="标题")


class KnowledgeSegmentUpdateApiRequest(BaseModel):
    """前端更新知识片段请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: KnowledgeSegmentUpdateRequest = Field(..., description="实际业务参数")


class KnowledgeSegmentIdRequest(BaseModel):
    """知识片段ID请求"""
    id: int = Field(..., description="片段唯一ID")


class KnowledgeSegmentIdApiRequest(BaseModel):
    """前端知识片段ID请求包裹"""

    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: KnowledgeSegmentIdRequest = Field(..., description="实际业务参数")


class OntologyNodeListRequest(BaseModel):
    """查询本体节点列表请求"""
    label: Optional[str] = Field(default=None, description="节点标签")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, description="每页数量")
    keyword: Optional[str] = Field(default=None, description="搜索关键字")

class OntologyNodeListApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: OntologyNodeListRequest = Field(..., description="实际业务参数")


# ===================== 本体管理（Ontology） =====================

class OntologyNodeCreateRequest(BaseModel):
    """创建本体节点请求"""
    name: str = Field(..., min_length=1, description="节点名称")
    label: str = Field(..., min_length=1, description="节点标签")
    properties: Optional[dict] = Field(default_factory=dict, description="其它属性")

class OntologyNodeCreateApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: OntologyNodeCreateRequest = Field(..., description="实际业务参数")

class OntologyNodeUpdateRequest(BaseModel):
    """更新本体节点请求"""
    id: str = Field(..., description="节点ID")
    name: Optional[str] = Field(default=None, min_length=1, description="节点名称")
    properties: Optional[dict] = Field(default=None, description="待更新属性")

class OntologyNodeUpdateApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: OntologyNodeUpdateRequest = Field(..., description="实际业务参数")

class OntologyNodeDeleteRequest(BaseModel):
    """删除本体节点请求"""
    id: str = Field(..., description="节点ID")

class OntologyNodeDeleteApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None, description="调用方标记")
    timestamp: int = Field(..., description="调用时间戳（毫秒）")
    data: OntologyNodeDeleteRequest = Field(..., description="实际业务参数")
