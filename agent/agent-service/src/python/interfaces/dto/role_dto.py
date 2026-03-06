from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field
from pydantic import ConfigDict

from interfaces.dto.rag_dto import StrEnum


class ApplicationRoleStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class ApplicationRoleInfo(BaseModel):
    id: int = Field(...)
    name: str = Field(...)
    createdAt: str = Field(default="")
    enableTime: str = Field(default="")
    enablePeriod: str = Field(default="")
    enabled: bool = Field(default=True)
    promptId: Optional[int] = Field(default=None)
    customPrompt: Optional[str] = Field(default=None)
    mode: str = Field(default="fixed")  # fixed, dynamic
    fixedPrompts: List[Dict[str, Any]] = Field(default_factory=list)
    dynamicPrompts: List[int] = Field(default_factory=list)


class ApplicationRolePage(BaseModel):
    items: List[ApplicationRoleInfo] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)


class ApplicationRoleListRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(default=1, ge=1, alias="page")
    size: int = Field(default=10, ge=1, le=100, alias="size")
    keyword: Optional[str] = Field(default=None)
    status: Optional[ApplicationRoleStatus] = Field(default=None)


class ApplicationRoleSaveRequest(BaseModel):
    id: Optional[int] = Field(default=None)
    name: str = Field(...)
    enableTime: str = Field(default="")
    enablePeriod: str = Field(default="")
    promptId: Optional[int] = Field(default=None)
    customPrompt: Optional[str] = Field(default=None)
    enabled: Optional[bool] = Field(default=True)
    mode: Optional[str] = Field(default="fixed")
    fixedPrompts: Optional[List[Dict[str, Any]]] = Field(default=None)
    dynamicPrompts: Optional[List[int]] = Field(default=None)


class ApplicationRoleIdRequest(BaseModel):
    id: int = Field(...)


class ApplicationRoleToggleStatusRequest(BaseModel):
    id: int = Field(...)
    enabled: bool = Field(...)


class ApplicationRoleListApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: ApplicationRoleListRequest = Field(...)


class ApplicationRoleSaveApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: ApplicationRoleSaveRequest = Field(...)


class ApplicationRoleIdApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: ApplicationRoleIdRequest = Field(...)


class ApplicationRoleToggleStatusApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: ApplicationRoleToggleStatusRequest = Field(...)


class ApplicationRoleActiveRequest(BaseModel):
    """获取当前时间有效的角色列表请求"""
    model_config = ConfigDict(populate_by_name=True)
    
    current_time: Optional[str] = Field(default=None, description="当前时间，格式：YYYY-MM-DD HH:MM:SS，默认使用服务器当前时间")
    require_selection: bool = Field(default=True, description="当多个角色有效时是否需要用户选择")
    selected_role_id: Optional[int] = Field(default=None, description="用户选中的角色ID（当知道要哪个角色时直接指定）")


class ApplicationRoleActiveApiRequest(BaseModel):
    """获取当前时间有效的角色列表API请求包装"""
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: ApplicationRoleActiveRequest = Field(...)


class ApplicationRoleActiveResult(BaseModel):
    """当前时间有效角色查询结果"""
    roles: List[ApplicationRoleInfo] = Field(default_factory=list, description="当前时间有效的角色列表")
    has_multiple: bool = Field(default=False, description="是否有多个角色同时有效")
    require_selection: bool = Field(default=False, description="是否需要用户选择")
    selected_role: Optional[ApplicationRoleInfo] = Field(default=None, description="如果已选择，返回选中的角色")
    current_time: str = Field(default="", description="查询使用的当前时间")

