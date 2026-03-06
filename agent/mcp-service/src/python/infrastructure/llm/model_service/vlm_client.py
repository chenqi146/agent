import time
import requests
from typing import Any, Dict, List
from infrastructure.common.error.errcode import ErrorCode, is_success
from infrastructure.common.logging.logging import logger,init_logging

@logger()
class VlmClient:
    def __init__(self,config:Dict[str,Any]):
        self.log.info(f"vlm client config = {config}")
        self.config = config
        self.is_initialized = False
        self.session = requests.Session()
        self.base_url = config.get("base_url")
        self.vlm_uri = "/v1/vision/analyze"
        self.llm_uri = "/v1/chat/completions"
        self.api_key = config.get("api_key","qjzh-vllm")
        self.init_vlm()
        self.log.info(f"VlmClient initialized")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头，包含认证信息"""
        headers = {"Content-Type": "application/json"}
        if self.api_key != "" and self.api_key is not None:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _post(self, endpoint: str, data: Dict[str, Any] = None, timeout: int = 60) -> Dict[str, Any]:
        """发送 POST 请求，返回结果包含响应时间"""
        url = f"{self.base_url}{endpoint}"
        self.log.debug(f"post url={url}")
        self.log.debug(f"headers={self._get_headers()}")
        start_time = time.time()
        try:
            response = self.session.post(
                url,
                json=data or {},
                timeout=timeout,
                headers=self._get_headers()
            )
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "success": True,
                "elapsed_ms": elapsed_ms
            }
        except requests.exceptions.Timeout:
            elapsed_ms = (time.time() - start_time) * 1000
            return {"success": False, "error": "请求超时", "elapsed_ms": elapsed_ms}
        except requests.exceptions.ConnectionError:
            elapsed_ms = (time.time() - start_time) * 1000
            return {"success": False, "error": "连接失败，请确保服务已启动", "elapsed_ms": elapsed_ms}
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {"success": False, "error": str(e), "elapsed_ms": elapsed_ms}
    
    def init_vlm(self)->ErrorCode:
        try:
            self.log.info(f"init vlm")
            result = self._post("/ops/health")
            if not result["success"]:
                self.log.error(f"init vlm failed,status_code={result}")
                return ErrorCode.LINK_VLLM_SERVER_FAILURE
            self.log.info(f"check vlm health success,result={result}")
            result = self._post("/ops/metrics")
            if not result["success"]:
                self.log.error(f"init vlm failed,status_code={result}")
                return ErrorCode.LINK_VLLM_SERVER_FAILURE
            self.log.info(f"check vlm metrics success,result={result}")
            self.is_initialized = True
            return ErrorCode.SUCCESS
        except Exception as e:
            self.log.error(f"link vllm server except,{e}")
            return ErrorCode.LINK_VLLM_SERVER_FAILURE
    
    def invoke(self,prompt:str,vlm_mode:bool=False,image_base64_list:List[str]=None,temperature:float=0.8)->str:
        try:
            self.log.info(f"invoke prompt={prompt},vlm_mode={vlm_mode}")
            if not self.is_initialized:
                self.log.info(f"vlm not initialized,reinit vlm")
                if not is_success(self.init_vlm()):
                    self.log.error(f"reinit vlm failed")
                    return ErrorCode.VLM_NOT_INITIALIZED,None
            if vlm_mode and image_base64_list is not None:
                is_multi = len(image_base64_list) > 1
                uri = self.vlm_uri if not is_multi else self.vlm_uri + "/multi"
                prompt_text = prompt + "/thinking" if self.config.get("is_thinking") else prompt + "/no_think"
                
                if is_multi:
                    # 多图接口使用 "images" 字段
                    request_data = {
                        "images": image_base64_list,
                        "prompt": prompt_text,
                        "max_tokens": self.config.get("vlm_max_tokens"),
                        "temperature": temperature,
                    }
                    # 调试：打印请求大小
                    total_size = sum(len(img) for img in image_base64_list)
                    self.log.debug(f"Multi-image request: {len(image_base64_list)} images, total size: {total_size/1024:.1f}KB")
                else:
                    # 单图接口使用 "image" 字段
                    request_data = {
                        "image": image_base64_list[0],
                        "prompt": prompt_text,
                        "max_tokens": self.config.get("vlm_max_tokens"),
                        "temperature": temperature,
                    }
                    self.log.debug(f"Single-image request: size: {len(image_base64_list[0])/1024:.1f}KB")
            else:
                uri = self.llm_uri
                # 安全获取 llm 配置
                llm_config = self.config.get("llm", {}) or {}
                is_thinking = llm_config.get("is_thinking", False)
                prompt_text = prompt + "/thinking" if is_thinking else prompt + "/no_think"
                
                # OpenAI 兼容 API 需要 messages 格式
                request_data = {
                    "messages": [
                        {"role": "user", "content": prompt_text}
                    ],
                    "max_tokens": self.config.get("llm_max_tokens", 4096),
                    "temperature": temperature,
                }
            result = self._post(uri,request_data,timeout=180)
            if not result["success"]:
                self.log.error(f"invoke failed,status_code={result}")
                return ErrorCode.INVOKE_LLM_FAILURE,None
            
            # 调试：打印原始响应
            self.log.debug(f"Raw response: status_code={result.get('status_code')}, data={result.get('data')}")
            
            data = result.get("data", {})
            response_data = data.get("data", {})
            description = response_data.get("description", "") if isinstance(response_data, dict) else ""
            if vlm_mode and image_base64_list is not None:
                description = response_data.get("description", "") if isinstance(response_data, dict) else ""
                passed = (
                    result["status_code"] == 200 and
                    data.get("code") == 0 and
                    len(description) > 0
                )
                if passed:
                    msg = description  # 直接返回描述内容，而不是长度
                else:
                    msg = f"响应异常: code={data.get('code')}, message={data.get('message')}, data={data}"
            else:
                # OpenAI chat completion 响应格式
                # 直接从 data 获取 choices（不是 data.data.choices）
                choices = data.get("choices", [])
                self.log.debug(f"LLM响应: choices数量={len(choices)}")
                
                # 提取消息内容（支持 message.content 格式）
                content = ""
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", "") if isinstance(message, dict) else ""
                    self.log.debug(f"LLM响应: message={type(message)}, content长度={len(content)}")
                    # 兼容旧格式
                    if not content:
                        content = choices[0].get("text", "")
                
                passed = (
                    result["status_code"] == 200 and
                    len(content.strip()) > 0
                )
                self.log.debug(f"LLM响应判断: status={result['status_code']}, content_len={len(content.strip())}, passed={passed}")
                
                if passed:
                    usage = data.get("usage", {})
                    msg = content  # 返回完整内容
                    self.log.info(f"LLM生成成功: {len(content)}字符, tokens={usage.get('total_tokens', 0)}")
                else:
                    msg = f"响应异常: choices={len(choices)}, content_len={len(content)}"
                    self.log.warning(msg)
            return ErrorCode.SUCCESS,msg
        except Exception as e:
            self.log.error(f"invoke except,{e}")
            return ErrorCode.INVOKE_LLM_FAILURE,None