from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic import ConfigDict

from interfaces.dto.rag_dto import StrEnum


class PromptStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    DRAFT = "draft"


class PromptVariable(BaseModel):
    key: str = Field(...)
    defaultValue: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    required: bool = Field(default=False)


class PromptTemplateInfo(BaseModel):
    id: int = Field(...)
    name: str = Field(...)
    content: str = Field(...)
    category: str = Field(default="general")
    version: str = Field(default="1.0.0")
    status: PromptStatus = Field(default=PromptStatus.DRAFT)
    createdAt: str = Field(default="")
    updatedAt: str = Field(default="")
    variables: List[PromptVariable] = Field(default_factory=list)


class PromptTemplatePage(BaseModel):
    items: List[PromptTemplateInfo] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    size: int = Field(default=10)


class PromptTemplateListRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(default=1, ge=1, alias="page")
    size: int = Field(default=10, ge=1, le=100, alias="size")
    keyword: Optional[str] = Field(default=None)
    status: Optional[PromptStatus] = Field(default=None)


class PromptTemplateSaveRequest(BaseModel):
    id: Optional[int] = Field(default=None)
    name: str = Field(...)
    content: str = Field(...)
    category: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)
    status: Optional[PromptStatus] = Field(default=None)
    variables: Optional[List[PromptVariable]] = Field(default=None)


class PromptTemplateIdRequest(BaseModel):
    id: int = Field(...)


class PromptTemplateToggleStatusRequest(BaseModel):
    id: int = Field(...)
    status: PromptStatus = Field(...)


class PromptTemplateListApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: PromptTemplateListRequest = Field(...)


class PromptTemplateSaveApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: PromptTemplateSaveRequest = Field(...)


class PromptTemplateIdApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: PromptTemplateIdRequest = Field(...)


class PromptTemplateToggleStatusApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: PromptTemplateToggleStatusRequest = Field(...)


class PromptTestType(StrEnum):
    AB_TEST = "ab_test"
    BATCH_TEST = "batch_test"
    QUICK_TEST = "quick_test"


class PromptAbTestRunRequest(BaseModel):
    templateAId: int = Field(...)
    templateBId: int = Field(...)
    inputText: str = Field(...)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    variablesA: Optional[dict] = Field(default=None)
    variablesB: Optional[dict] = Field(default=None)


class PromptQuickTestRunRequest(BaseModel):
    templateId: int = Field(...)
    inputText: str = Field(...)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    variables: Optional[dict] = Field(default=None)


class PromptBatchTestCase(BaseModel):
    index: int = Field(...)
    inputData: str = Field(...)
    expectedOutput: Optional[str] = Field(default=None)
    variables: Optional[dict] = Field(default=None)


class PromptBatchTestRunRequest(BaseModel):
    templateId: int = Field(...)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    samplingRate: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    variablesMapping: Optional[dict] = Field(default=None)
    cases: List[PromptBatchTestCase] = Field(default_factory=list)


class PromptTestInfo(BaseModel):
    id: int = Field(...)
    name: str = Field(...)
    type: PromptTestType = Field(...)
    status: str = Field(...)
    totalCases: int = Field(default=0)
    passedCases: int = Field(default=0)
    failedCases: int = Field(default=0)
    createdAt: str = Field(default="")


class PromptAbTestRunResult(BaseModel):
    test: PromptTestInfo = Field(...)
    results: Optional[List[dict]] = Field(default=None)


class PromptQuickTestRunResult(BaseModel):
    test: PromptTestInfo = Field(...)
    output: Optional[str] = Field(default=None)


class PromptBatchTestRunResult(BaseModel):
    test: PromptTestInfo = Field(...)
    results: Optional[List[dict]] = Field(default=None)


class PromptAbTestRunApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: PromptAbTestRunRequest = Field(...)


class PromptQuickTestRunApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: PromptQuickTestRunRequest = Field(...)


class PromptBatchTestRunApiRequest(BaseModel):
    tag: Optional[str] = Field(default=None)
    timestamp: int = Field(...)
    data: PromptBatchTestRunRequest = Field(...)
