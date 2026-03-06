from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class ToolType(str, Enum):
    FUNCTION = "function"
    SERVICE = "service"
    DEVICE = "device"

class InterfaceType(str, Enum):
    FULL = "full"
    COMPACT = "compact"

# --- Tool Execution ---
class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(..., description="Tool name to execute")
    interface_type: InterfaceType = Field(InterfaceType.FULL, description="Interface type (full/compact)")
    arguments: Dict[str, Any] = Field(..., description="Arguments for the tool")
    user_id: Optional[str] = Field(None, description="User ID invoking the tool")

class ToolExecutionResponse(BaseModel):
    status: str = Field(..., description="Execution status (success/error)")
    result: Any = Field(None, description="Execution result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: float = Field(0.0, description="Execution time in ms")

# --- Tool Management (Subset for MCP Service) ---
class ToolRegisterRequest(BaseModel):
    name: str
    display_name: Optional[str] = None
    description_short: Optional[str] = None
    description_full: Optional[str] = None
    tool_type: ToolType
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    endpoint_url: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

class ToolInfo(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: str
    tool_type: str
    is_active: bool

