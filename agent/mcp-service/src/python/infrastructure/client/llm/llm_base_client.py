from abc import ABC, abstractmethod
from typing import Any


class LlmBaseClient(ABC):
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    def generate(self, input_data: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
