from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class InterfaceType(str, Enum):
    FULL = "full"
    COMPACT = "compact"

class BaseTool(ABC):
    name: str
    description: str
    tags: list[str] = []
    
    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def get_definition(self, interface_type: InterfaceType = InterfaceType.FULL) -> Dict[str, Any]:
        pass
