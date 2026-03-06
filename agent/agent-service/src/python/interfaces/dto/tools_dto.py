from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ToolType(str, Enum):
    FUNCTION = "function"
    SERVICE = "service"
    DEVICE = "device"

class InterfaceType(str, Enum):
    FULL = "full"
    COMPACT = "compact"

# --- Tool Integration & Management ---
class ToolCreateRequest(BaseModel):
    name: str = Field(..., description="Tool unique name")
    display_name: Optional[str] = Field(None, description="Display name")
    description_short: Optional[str] = Field(None, description="Short description")
    description_full: Optional[str] = Field(None, description="Full description")
    tool_type: str = Field(..., description="Tool type")
    category: Optional[str] = Field(None, description="Category")
    server_id: Optional[int] = Field(None, description="MCP Server ID")
    endpoint_url: Optional[str] = Field(None, description="Tool endpoint URL (relative to server base)")
    api_key: Optional[str] = Field(None, description="API Key for this tool interface")
    tags: Optional[List[str]] = Field(None, description="Tags")
    primary_skill_id: Optional[int] = Field(None, description="Primary skill ID")

class ToolUpdateRequest(BaseModel):
    id: int
    display_name: Optional[str] = None
    description_short: Optional[str] = None
    description_full: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    server_id: Optional[int] = None
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None

class ToolResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    tool_type: str
    is_active: bool
    created_at: datetime

# --- Tool Logs ---
class ToolLogQuery(BaseModel):
    tool_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 20

# --- Tool Rating ---
class ToolRatingCreateRequest(BaseModel):
    tool_id: int
    skill_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

# --- Tool Relationships ---
class ToolRelationCreateRequest(BaseModel):
    source_tool_id: int
    target_tool_id: int
    relationship_type: str
    weight: float = 1.0

# --- Snapshot Version Management ---
class ToolSnapshotCreateRequest(BaseModel):
    tool_id: int
    version: str
    interface_type: str = "full"
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

# --- Tool Discovery ---
class ToolDiscoveryQuery(BaseModel):
    skill_id: Optional[int] = None
    category: Optional[str] = None
