import os
from typing import Any, Dict, Optional

from openai import OpenAI

from infrastructure.config.sys_config import SysConfig
from .llm_base_client import LlmBaseClient


class HsyqClient(LlmBaseClient):
    def __init__(self, config: Optional[SysConfig] = None, model: str = "doubao-seed-1-8-251228") -> None:
        if config is None:
            config = SysConfig()
        system_cfg = config.get_system_config() or {}
        vllm_cfg = system_cfg.get("vllm") or {}
        llm_cfg = vllm_cfg.get("llm") or {}
        hsyq_cfg = llm_cfg.get("hsyq") or {}

        api_key = hsyq_cfg.get("key") or os.getenv("ARK_API_KEY", "")
        base_url = hsyq_cfg.get("base_url") or "https://ark.cn-beijing.volces.com/api/v3"

        super().__init__(api_key=api_key, base_url=base_url, model=model)

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def generate(self, input_data: Any, **kwargs: Any) -> Any:
        payload: Dict[str, Any] = {
            "model": self.model,
            "input": input_data,
        }
        if kwargs:
            payload.update(kwargs)
        return self.client.responses.create(**payload)
