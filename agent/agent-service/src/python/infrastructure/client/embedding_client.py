"""
调用 vllm-application 的 /v1/embeddings 接口实现文本向量化（知识嵌入）
兼容 OpenAI Embeddings API 请求格式。
"""
from typing import List, Optional, Tuple
import requests

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode


@logger()
class EmbeddingClient:
    """
    调用 vllm-application 的 Embedding 服务，将文本转为向量。
    """

    def __init__(self, base_url: str, timeout: float = 60.0, api_key: str | None = None):
        """
        Args:
            base_url: vllm-application 服务根地址，如 http://127.0.0.1:8800
            timeout: 请求超时秒数
        """
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or None
        self._available = bool(self.base_url)
        if not self._available:
            self.log.warning("EmbeddingClient: base_url 为空，知识嵌入将不可用")

    def is_available(self) -> bool:
        """是否已配置并可调用"""
        return self._available

    def embed(
        self,
        texts: List[str],
        dimensions: Optional[int] = None,
    ) -> Tuple[ErrorCode, List[List[float]]]:
        """
        调用 vllm-application POST /v1/embeddings，返回向量列表。

        Args:
            texts: 待向量化的文本列表
            dimensions: 可选，输出向量维度（部分模型支持，如 Qwen3-Embedding 支持 32~1024）

        Returns:
            (ErrorCode, embeddings): 成功时 embeddings 与 texts 一一对应；失败时为空列表
        """
        if not self._available:
            self.log.error("EmbeddingClient: base_url 未配置")
            return ErrorCode.CONFIG_NOT_FOUND, []

        if not texts:
            return ErrorCode.SUCCESS, []

        url = f"{self.base_url}/v1/embeddings"
        payload = {"input": texts if len(texts) > 1 else texts[0]}
        if dimensions is not None:
            payload["dimensions"] = dimensions

        try:
            headers = {}
            if self.api_key:
                # 与 vllm-application 的 ApiKeyAuthMiddleware 约定：
                # 优先使用 Authorization: Bearer <api_key>
                headers["Authorization"] = f"Bearer {self.api_key}"

            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                self.log.error(
                    f"Embedding request failed: status={resp.status_code}, body={resp.text[:500]}"
                )
                return ErrorCode.EXTERNAL_SERVICE_ERROR, []

            data = resp.json()
            if "data" not in data or not isinstance(data["data"], list):
                self.log.error(f"Embedding response missing data: {list(data.keys())}")
                return ErrorCode.DATA_FORMAT_INVALID, []

            # 按 index 排序，保证与输入顺序一致
            items = sorted(data["data"], key=lambda x: x.get("index", 0))
            embeddings = []
            for item in items:
                vec = item.get("embedding")
                if vec is None:
                    self.log.warning("Embedding item missing 'embedding' field")
                    embeddings.append([])
                else:
                    embeddings.append(
                        vec if isinstance(vec, list) else getattr(vec, "tolist", lambda: list(vec))()
                    )

            if len(embeddings) != len(texts):
                self.log.warning(
                    f"Embedding count mismatch: requested {len(texts)}, got {len(embeddings)}"
                )

            return ErrorCode.SUCCESS, embeddings

        except requests.exceptions.Timeout:
            self.log.error("Embedding request timeout")
            return ErrorCode.EXTERNAL_SERVICE_TIMEOUT, []
        except requests.exceptions.RequestException as e:
            self.log.error(f"Embedding request error: {e}")
            return ErrorCode.EXTERNAL_SERVICE_ERROR, []
        except Exception as e:
            self.log.error(f"Embedding error: {e}", exc_info=True)
            return ErrorCode.INTERNAL_ERROR, []
