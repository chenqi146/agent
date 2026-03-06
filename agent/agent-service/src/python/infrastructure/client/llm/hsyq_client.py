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
        # 兼容旧接口，底层调用 chat
        messages = [{"role": "user", "content": str(input_data)}]
        return self.chat(messages, **kwargs)

    def chat(self, messages: list, **kwargs: Any) -> Any:
        """
        调用 LLM 进行对话
        :param messages: 消息列表，如 [{"role": "user", "content": "hello"}]
        :param kwargs: 其他参数，如 temperature, max_tokens 等
        :return: 响应内容（字符串）
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if kwargs:
            payload.update(kwargs)
        
        try:
            response = self.client.chat.completions.create(**payload)
            return response.choices[0].message.content
        except Exception as e:
            # 简单的错误处理，实际生产中可能需要更复杂的重试或日志
            print(f"HsyqClient chat error: {e}")
            return ""
