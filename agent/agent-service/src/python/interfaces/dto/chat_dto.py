from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from interfaces.dto.rag_dto import StrEnum

class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class ContentType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    EVENT_JSON = "event-json"

class ChatMessageAttachmentDTO(BaseModel):
    id: Optional[int] = None
    messageId: str
    fileName: str
    fileType: str
    fileSize: int
    fileUrl: str
    thumbnailUrl: Optional[str] = None
    storageType: str = "local"
    metadata: Optional[Dict[str, Any]] = None

class ChatMessageDTO(BaseModel):
    id: Optional[str] = Field(None, description="Message ID (UUID)")
    messageId: str = Field(..., description="Message Unique ID")
    conversationId: str = Field(..., description="Conversation ID")
    parentMessageId: Optional[str] = Field(None, description="Parent Message ID")
    role: MessageRole
    content: str
    contentType: ContentType = Field(default=ContentType.TEXT)
    modelName: Optional[str] = None
    tokenCount: int = Field(default=0)
    isContext: bool = Field(default=False)
    metadata: Optional[Dict[str, Any]] = None
    createdAt: Optional[str] = None
    seqNo: int = Field(default=0)
    attachments: Optional[List[ChatMessageAttachmentDTO]] = None

class ChatConversationDTO(BaseModel):
    id: Optional[int] = Field(None, description="Database ID")
    conversationId: str = Field(..., description="Conversation Unique ID")
    userId: int = Field(..., description="User ID")
    title: Optional[str] = None
    modelName: str
    isPinned: bool = Field(default=False)
    messageCount: int = Field(default=0)
    tokenCount: int = Field(default=0)
    lastMessageTime: Optional[str] = None
    isDeleted: bool = Field(default=False)
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    conversations: List[ChatConversationDTO]

class ChatConversationResponse(BaseModel):
    conversation: ChatConversationDTO
    messages: List[ChatMessageDTO]

class ChatStreamRequest(BaseModel):
    message: str
    conversationId: Optional[str] = None
    model: Optional[str] = None
    messageId: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    thinking: bool = False
    roleId: Optional[int] = None

class ChatStopRequest(BaseModel):
    conversationId: str

    
class ChatMessageResponse(BaseModel):
    message: ChatMessageDTO
