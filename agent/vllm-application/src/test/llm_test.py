#!/usr/bin/env python3
'''
LLM 服务接口测试用例
测试 LLMController 提供的所有 REST API 接口

使用方法:
    1. 先启动服务: cd src/python && python main.py
    2. 运行测试: python llm_test.py [--base-url http://127.0.0.1:18096]
'''
import requests
import json
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List, Tuple

SERVER_URL = "http://10.102.0.97:8800"
#SERVER_URL = "http://127.0.0.1:8800"

# API Key 认证
API_KEY = "qjzh-vllm"

# 是否启用链式思考（Chain-of-Thought）
# True: 模型会进行深度思考分析，响应更详细但耗时更长
# False: 模型直接回答，响应更快但可能不够详细
IS_THINKING = True


class LLMServiceTest:
    """LLM 服务测试类"""
    
    def __init__(self, base_url: str = SERVER_URL, enable_thinking: bool = IS_THINKING, api_key: str = API_KEY):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.test_results = []
        self.enable_thinking = enable_thinking
        self._server_engine_info = None  # 缓存服务端引擎信息
    
    def _get_server_engine_info(self) -> Dict[str, Any]:
        """获取服务端引擎信息（带缓存）"""
        if self._server_engine_info is not None:
            return self._server_engine_info
        
        try:
            response = self.session.post(
                f"{self.base_url}/metrics",
                json={},
                timeout=10,
                headers=self._get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    self._server_engine_info = data.get("data", {})
                    return self._server_engine_info
        except Exception:
            pass
        
        # 默认值
        return {"engine_type": "unknown", "token_stream_available": False}
    
    def _print_engine_info(self):
        """打印服务端引擎信息"""
        info = self._get_server_engine_info()
        engine_type = info.get("engine_type", "unknown")
        token_stream = info.get("token_stream_available", False)
        
        mode_desc = {
            "llm": "LLM 引擎（Chunk 流式）",
            "async": "AsyncLLMEngine（Token 流式）",
            "unknown": "未知"
        }
        
        print(f"    ℹ️  服务端引擎: {mode_desc.get(engine_type, engine_type)}")
        print(f"    ℹ️  Token 流式可用: {'是' if token_stream else '否'}")
    
    def _add_thinking_control(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        根据 enable_thinking 标识添加思考控制指令
        
        Qwen3 模型支持 /think 和 /no_think 标签控制思考模式
        """
        if not messages:
            return messages
        
        # 复制消息列表，避免修改原始数据
        new_messages = [msg.copy() for msg in messages]
        
        # 在最后一条用户消息中添加思考控制标签
        for i in range(len(new_messages) - 1, -1, -1):
            if new_messages[i].get("role") == "user":
                content = new_messages[i].get("content", "")
                if self.enable_thinking:
                    # 启用思考模式
                    if "/think" not in content and "/no_think" not in content:
                        new_messages[i]["content"] = content + " /think"
                else:
                    # 禁用思考模式
                    if "/think" not in content and "/no_think" not in content:
                        new_messages[i]["content"] = content + " /no_think"
                break
        
        return new_messages
    
    def _extract_thinking_content(self, content: str) -> Tuple[str, str]:
        """
        从响应内容中提取思考内容和实际回复
        
        Qwen3 模型的思考内容格式: <think>思考过程</think>实际回复
        
        Args:
            content: 模型的完整响应内容
            
        Returns:
            Tuple[str, str]: (思考内容, 实际回复)
        """
        import re
        
        thinking = ""
        answer = content
        
        # 匹配 <think>...</think> 标签
        think_pattern = r'<think>(.*?)</think>'
        match = re.search(think_pattern, content, re.DOTALL)
        
        if match:
            thinking = match.group(1).strip()
            # 移除思考标签，获取实际回复
            answer = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()
        
        return thinking, answer
    
    def _print_thinking_content(self, thinking: str, max_lines: int = 20):
        """
        格式化打印思考内容
        
        Args:
            thinking: 思考内容
            max_lines: 最大显示行数
        """
        if not thinking:
            return
        
        print(f"    ┌─ 思考过程 (Thinking) ──────────────────────────────────")
        lines = thinking.split('\n')
        
        if len(lines) > max_lines:
            # 显示前半部分
            for line in lines[:max_lines // 2]:
                print(f"    │ {line}")
            print(f"    │ ... (省略 {len(lines) - max_lines} 行) ...")
            # 显示后半部分
            for line in lines[-(max_lines // 2):]:
                print(f"    │ {line}")
        else:
            for line in lines:
                print(f"    │ {line}")
        
        print(f"    └────────────────────────────────────────────────────────")
    
    def _log(self, message: str, level: str = "INFO"):
        """打印日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头，包含认证信息"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _post(self, endpoint: str, data: Dict[str, Any] = None, timeout: int = 60) -> Dict[str, Any]:
        """发送 POST 请求，返回结果包含响应时间"""
        url = f"{self.base_url}{endpoint}"
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
    
    def _post_stream(self, endpoint: str, data: Dict[str, Any], timeout: int = 120):
        """发送流式 POST 请求，返回 (response, start_time)"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        try:
            response = self.session.post(
                url,
                json=data,
                timeout=timeout,
                headers=self._get_headers(),
                stream=True
            )
            return response, start_time
        except Exception as e:
            return None, start_time
    
    def _record_result(self, test_name: str, passed: bool, message: str = "", elapsed_ms: float = 0,
                        request_data: Dict[str, Any] = None, response_data: Dict[str, Any] = None):
        """记录测试结果"""
        self.test_results.append({
            "test_name": test_name,
            "passed": passed,
            "message": message,
            "elapsed_ms": elapsed_ms
        })
        status = "✓ PASS" if passed else "✗ FAIL"
        time_str = f"[{elapsed_ms:.0f}ms]" if elapsed_ms > 0 else ""
        self._log(f"{status}: {test_name} {time_str} {message}", "INFO" if passed else "ERROR")
        
        # 判断是否是推理测试（需要详细打印输入输出）
        is_inference_test = "completions" in test_name or any(kw in test_name for kw in 
            ["vehicle", "parking", "traffic", "road", "emergency"])
        
        # 打印输入输出详情
        if request_data is not None and request_data:
            request_str = json.dumps(request_data, ensure_ascii=False, indent=2)
            if is_inference_test:
                print(f"    ┌─ 请求 (Request) ─────────────────────────────────────")
                for line in request_str.split('\n'):
                    print(f"    │ {line}")
                print(f"    └────────────────────────────────────────────────────────")
            else:
                self._log(f"  📤 请求: {json.dumps(request_data, ensure_ascii=False)[:300]}")
        
        if response_data is not None:
            # 尝试提取思考内容（从 chat completion 响应中）
            thinking_content = ""
            actual_answer = ""
            
            if is_inference_test:
                # 尝试从响应中提取内容
                try:
                    # 处理标准响应格式
                    data_obj = response_data.get("data", response_data)
                    choices = data_obj.get("choices", [])
                    if choices:
                        # 对话补全响应
                        msg = choices[0].get("message", {})
                        content = msg.get("content", "")
                        if not content:
                            # 文本补全响应
                            content = choices[0].get("text", "")
                        
                        if content:
                            thinking_content, actual_answer = self._extract_thinking_content(content)
                    
                    # 处理流式响应摘要
                    if "full_content" in response_data:
                        content = response_data.get("full_content", "")
                        if content:
                            thinking_content, actual_answer = self._extract_thinking_content(content)
                except Exception:
                    pass
                
                # 打印思考内容（如果有）
                if thinking_content:
                    self._print_thinking_content(thinking_content)
                
                # 打印实际回复（如果有思考内容，单独显示回复）
                if actual_answer:
                    print(f"    ┌─ 实际回复 (Answer) ─────────────────────────────────")
                    lines = actual_answer.split('\n')
                    if len(lines) > 30:
                        for line in lines[:15]:
                            print(f"    │ {line}")
                        print(f"    │ ... (省略 {len(lines) - 30} 行) ...")
                        for line in lines[-15:]:
                            print(f"    │ {line}")
                    else:
                        for line in lines:
                            print(f"    │ {line}")
                    print(f"    └────────────────────────────────────────────────────────")
                
                # 如果没有思考内容，显示完整响应
                if not thinking_content:
                    print(f"    ┌─ 响应 (Response) ────────────────────────────────────")
                    response_str = json.dumps(response_data, ensure_ascii=False, indent=2)
                    lines = response_str.split('\n')
                    if len(lines) > 50:
                        for line in lines[:25]:
                            print(f"    │ {line}")
                        print(f"    │ ... (省略 {len(lines) - 50} 行) ...")
                        for line in lines[-25:]:
                            print(f"    │ {line}")
                    else:
                        for line in lines:
                            print(f"    │ {line}")
                    print(f"    └────────────────────────────────────────────────────────")
            else:
                response_str = json.dumps(response_data, ensure_ascii=False)
                if len(response_str) > 500:
                    response_str = response_str[:500] + "..."
                self._log(f"  📥 响应: {response_str}")
    
    # ==================== 健康检查测试 ====================
    
    def test_ops_ping(self) -> bool:
        """测试 /ops/ping 接口"""
        self._log("测试 Ops Ping 接口...")
        request_data = {}
        result = self._post("/ops/ping", request_data)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_ops_ping", False, result.get("error", ""), elapsed_ms, request_data)
            return False
        
        data = result["data"]
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            data.get("data", {}).get("status") == "pong"
        )
        self._record_result("test_ops_ping", passed, f"status={data.get('data', {}).get('status')}", elapsed_ms, request_data, data)
        return passed
    
    def test_ops_health(self) -> bool:
        """测试 /ops/health 接口"""
        self._log("测试 Ops Health 接口...")
        request_data = {}
        result = self._post("/ops/health", request_data)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_ops_health", False, result.get("error", ""), elapsed_ms, request_data)
            return False
        
        data = result["data"]
        passed = result["status_code"] == 200 and data.get("code") == 0
        self._record_result("test_ops_health", passed, f"状态: {data.get('data', {}).get('status')}", elapsed_ms, request_data, data)
        return passed
    
    def test_llm_health(self) -> bool:
        """测试 /health 接口（LLM 健康检查）"""
        self._log("测试 LLM Health 接口...")
        request_data = {}
        result = self._post("/health", request_data)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_llm_health", False, result.get("error", ""), elapsed_ms, request_data)
            return False
        
        data = result["data"]
        health_data = data.get("data") or {}  # 处理 data 为 None 的情况
        passed = result["status_code"] == 200 and data.get("code") == 0
        self._record_result(
            "test_llm_health",
            passed,
            f"is_healthy={health_data.get('is_healthy')}, status={health_data.get('model_status')}, code={data.get('code')}, msg={data.get('message')}",
            elapsed_ms,
            request_data,
            data
        )
        return passed
    
    # ==================== 模型信息测试 ====================
    
    def test_list_models(self) -> bool:
        """测试 /v1/models 接口"""
        self._log("测试获取模型列表...")
        request_data = {}
        result = self._post("/v1/models", request_data)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_list_models", False, result.get("error", ""), elapsed_ms, request_data)
            return False
        
        data = result["data"]
        inner_data = data.get("data") or {}
        models = inner_data.get("data") or []
        passed = result["status_code"] == 200 and data.get("code") == 0
        self._record_result("test_list_models", passed, f"模型数量: {len(models)}, code={data.get('code')}, msg={data.get('message')}", elapsed_ms, request_data, data)
        return passed
    
    def test_metrics(self) -> bool:
        """测试 /metrics 接口"""
        self._log("测试获取服务指标...")
        request_data = {}
        result = self._post("/metrics", request_data)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_metrics", False, result.get("error", ""), elapsed_ms, request_data)
            return False
        
        data = result["data"]
        metrics = data.get("data", {})
        passed = result["status_code"] == 200 and data.get("code") == 0
        self._record_result(
            "test_metrics",
            passed,
            f"总请求数: {metrics.get('statistics', {}).get('total_requests', 0)}",
            elapsed_ms,
            request_data,
            data
        )
        return passed
    
    def test_gpu_resources(self) -> bool:
        """测试 /gpu/resources 接口"""
        self._log("测试获取 GPU 资源...")
        request_data = {}
        result = self._post("/gpu/resources", request_data)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_gpu_resources", False, result.get("error", ""), elapsed_ms, request_data)
            return False
        
        data = result["data"]
        resources = data.get("data", [])
        passed = result["status_code"] == 200 and data.get("code") == 0
        
        if resources and len(resources) > 0:
            gpu_info = resources[0]
            msg = f"GPU: {gpu_info.get('gpu_name')}, 显存: {gpu_info.get('used_memory_mb', 0):.0f}/{gpu_info.get('total_memory_mb', 0):.0f} MB"
        else:
            msg = "未检测到 GPU"
        
        self._record_result("test_gpu_resources", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    # ==================== 推理接口测试 ====================
    
    def test_completions_simple(self) -> bool:
        """测试 /v1/completions 接口（简单文本补全）"""
        self._log("测试文本补全接口（简单请求）...")
        
        request_data = {
            "prompt": "Hello, my name is",
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        result = self._post("/v1/completions", request_data, timeout=120)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        if not result["success"]:
            self._record_result("test_completions_simple", False, result.get("error", ""), elapsed_ms, request_data, data)
            return False
        
        response_data = data.get("data", {})
        choices = response_data.get("choices", [])
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(choices) > 0 and
            choices[0].get("text", "").strip() != ""
        )
        
        if passed:
            text = choices[0].get("text", "")[:50]
            usage = response_data.get("usage", {})
            msg = f"生成文本: '{text}...', tokens: {usage.get('total_tokens', 0)}"
        else:
            msg = f"响应异常"
        
        self._record_result("test_completions_simple", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    def test_completions_batch(self) -> bool:
        """测试 /v1/completions 接口（批量文本补全）"""
        self._log("测试文本补全接口（批量请求）...")
        
        request_data = {
            "prompt": ["Hello", "How are you", "What is AI"],
            "max_tokens": 30,
            "temperature": 0.5
        }
        
        result = self._post("/v1/completions", request_data, timeout=180)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        if not result["success"]:
            self._record_result("test_completions_batch", False, result.get("error", ""), elapsed_ms, request_data, data)
            return False
        
        response_data = data.get("data", {})
        choices = response_data.get("choices", [])
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(choices) == 3
        )
        
        self._record_result("test_completions_batch", passed, f"返回 {len(choices)} 条结果", elapsed_ms, request_data, data)
        return passed
    
    def test_chat_completions_simple(self) -> bool:
        """测试 /v1/chat/completions 接口（简单对话）"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试对话补全接口（简单请求，思考模式: {thinking_mode}）...")
        
        messages = [
            {"role": "user", "content": "你好，请介绍一下你自己"}
        ]
        # 根据 enable_thinking 添加思考控制
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        result = self._post("/v1/chat/completions", request_data, timeout=120)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        if not result["success"]:
            self._record_result("test_chat_completions_simple", False, result.get("error", ""), elapsed_ms, request_data, data)
            return False
        
        response_data = data.get("data", {})
        choices = response_data.get("choices", [])
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(choices) > 0 and
            choices[0].get("message", {}).get("content", "").strip() != ""
        )
        
        if passed:
            content = choices[0].get("message", {}).get("content", "")[:50]
            usage = response_data.get("usage", {})
            msg = f"回复: '{content}...', tokens: {usage.get('total_tokens', 0)}"
        else:
            msg = f"响应异常"
        
        self._record_result("test_chat_completions_simple", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    def test_chat_completions_multi_turn(self) -> bool:
        """测试 /v1/chat/completions 接口（多轮对话）"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试对话补全接口（多轮对话，思考模式: {thinking_mode}）...")
        
        messages = [
            {"role": "system", "content": "你是一个友好的助手"},
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"},
            {"role": "user", "content": "今天天气怎么样？"}
        ]
        # 根据 enable_thinking 添加思考控制
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        result = self._post("/v1/chat/completions", request_data, timeout=120)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        if not result["success"]:
            self._record_result("test_chat_completions_multi_turn", False, result.get("error", ""), elapsed_ms, request_data, data)
            return False
        
        response_data = data.get("data", {})
        choices = response_data.get("choices", [])
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(choices) > 0
        )
        
        self._record_result("test_chat_completions_multi_turn", passed, f"多轮对话测试", elapsed_ms, request_data, data)
        return passed
    
    def test_chat_completions_stream(self) -> bool:
        """测试 /v1/chat/completions 接口（流式响应）"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试对话补全接口（流式响应，思考模式: {thinking_mode}）...")
        
        messages = [
            {"role": "user", "content": "写一首短诗"}
        ]
        # 根据 enable_thinking 添加思考控制
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 100,
            "temperature": 0.8,
            "stream": True
        }
        
        response, start_time = self._post_stream("/v1/chat/completions", request_data)
        
        if response is None:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_chat_completions_stream", False, "连接失败", elapsed_ms, request_data)
            return False
        
        chunks = []
        full_content = ""
        
        try:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            chunks.append(chunk)
                            # 提取内容
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_chat_completions_stream", False, f"解析错误: {e}", elapsed_ms, request_data)
            return False
        
        elapsed_ms = (time.time() - start_time) * 1000
        passed = len(chunks) > 0 and len(full_content) > 0
        
        # 构造流式响应摘要
        stream_response = {
            "chunks_count": len(chunks),
            "full_content": full_content,
            "first_chunk": chunks[0] if chunks else None
        }
        
        self._record_result(
            "test_chat_completions_stream",
            passed,
            f"收到 {len(chunks)} 个数据块, 内容长度: {len(full_content)}",
            elapsed_ms,
            request_data,
            stream_response
        )
        return passed
    
    def test_stream_token_mode(self) -> bool:
        """测试 Token 级流式输出"""
        # 获取服务端引擎信息
        engine_info = self._get_server_engine_info()
        engine_type = engine_info.get("engine_type", "unknown")
        token_available = engine_info.get("token_stream_available", False)
        
        if token_available:
            self._log("测试 Token 级流式输出（服务端支持真正的 Token 流式）...")
        else:
            self._log("测试 Token 级流式输出（服务端将降级为 Chunk 模式）...")
        
        messages = [
            {"role": "user", "content": "用一句话介绍人工智能"}
        ]
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 100,
            "temperature": 0.7,
            "stream": True,
            "stream_options": {
                "mode": "token",
                "include_usage": True
            }
        }
        
        start_time = time.time()
        first_chunk_time = None
        response, _ = self._post_stream("/v1/chat/completions", request_data)
        
        if response is None:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_stream_token_mode", False, "连接失败", elapsed_ms)
            return False
        
        chunks = []
        full_content = ""
        usage_info = None
        error_info = None
        
        try:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            chunks.append(chunk)
                            
                            if "error" in chunk:
                                error_info = chunk["error"]
                                continue
                            
                            if first_chunk_time is None:
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if delta.get("content"):
                                    first_chunk_time = time.time()
                            
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                            
                            if "usage" in chunk:
                                usage_info = chunk["usage"]
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_stream_token_mode", False, f"解析错误: {e}", elapsed_ms)
            return False
        
        elapsed_ms = (time.time() - start_time) * 1000
        first_token_latency = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0
        passed = len(chunks) > 0 and len(full_content) > 0 and error_info is None
        
        # 根据引擎类型显示不同标题
        if token_available:
            mode_desc = f"Token 流式（{engine_type} 引擎）"
        else:
            mode_desc = f"Token 请求 → Chunk 实际（{engine_type} 引擎）"
        
        print(f"\n    ┌─ Token 流式测试结果 ────────────────────────────────")
        print(f"    │ 📊 性能指标:")
        print(f"    │   • 总耗时: {elapsed_ms:.0f} ms")
        print(f"    │   • 首内容延迟: {first_token_latency:.0f} ms")
        print(f"    │   • 数据块数量: {len(chunks)}")
        print(f"    │   • 输出长度: {len(full_content)} 字符")
        if usage_info:
            print(f"    │   • Token 统计: prompt={usage_info.get('prompt_tokens', 0)}, "
                  f"completion={usage_info.get('completion_tokens', 0)}")
        if error_info:
            print(f"    │   ⚠️ 服务端错误: {error_info.get('message', error_info)}")
        print(f"    │   ℹ️ 服务端引擎: {engine_type}, Token流式: {'可用' if token_available else '不可用'}")
        print(f"    └────────────────────────────────────────────────────────\n")
        
        self._record_result(
            "test_stream_token_mode",
            passed,
            f"{mode_desc}: 首内容 {first_token_latency:.0f}ms, 共 {len(chunks)} 块",
            elapsed_ms,
            request_data
        )
        return passed
    
    def test_stream_chunk_mode(self) -> bool:
        """测试 Chunk 级流式输出"""
        self._log("测试 Chunk 级流式输出...")
        
        engine_info = self._get_server_engine_info()
        engine_type = engine_info.get("engine_type", "unknown")
        
        messages = [
            {"role": "user", "content": "简单描述一下春天"}
        ]
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 100,
            "temperature": 0.7,
            "stream": True,
            "stream_options": {
                "mode": "chunk",
                "chunk_size": 20,
                "include_usage": True
            }
        }
        
        start_time = time.time()
        first_chunk_time = None
        response, _ = self._post_stream("/v1/chat/completions", request_data)
        
        if response is None:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_stream_chunk_mode", False, "连接失败", elapsed_ms)
            return False
        
        chunks = []
        full_content = ""
        usage_info = None
        error_info = None
        
        try:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            chunks.append(chunk)
                            
                            if "error" in chunk:
                                error_info = chunk["error"]
                                continue
                            
                            if first_chunk_time is None:
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if delta.get("content"):
                                    first_chunk_time = time.time()
                            
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                            
                            if "usage" in chunk:
                                usage_info = chunk["usage"]
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_stream_chunk_mode", False, f"解析错误: {e}", elapsed_ms)
            return False
        
        elapsed_ms = (time.time() - start_time) * 1000
        first_chunk_latency = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0
        passed = len(chunks) > 0 and len(full_content) > 0 and error_info is None
        
        avg_chunk_size = len(full_content) / (len(chunks) - 1) if len(chunks) > 1 else 0
        
        print(f"\n    ┌─ Chunk 流式测试结果 ───────────────────────────────")
        print(f"    │ 📊 性能指标:")
        print(f"    │   • 总耗时: {elapsed_ms:.0f} ms")
        print(f"    │   • 首块延迟: {first_chunk_latency:.0f} ms")
        print(f"    │   • 数据块数量: {len(chunks)}")
        print(f"    │   • 平均块大小: {avg_chunk_size:.1f} 字符")
        print(f"    │   • 输出长度: {len(full_content)} 字符")
        if usage_info:
            print(f"    │   • Token 统计: prompt={usage_info.get('prompt_tokens', 0)}, "
                  f"completion={usage_info.get('completion_tokens', 0)}")
        if error_info:
            print(f"    │   ⚠️ 服务端错误: {error_info.get('message', error_info)}")
        print(f"    │   ℹ️ 服务端引擎: {engine_type}")
        print(f"    └────────────────────────────────────────────────────────\n")
        
        self._record_result(
            "test_stream_chunk_mode",
            passed,
            f"Chunk流式: 首块 {first_chunk_latency:.0f}ms, {len(chunks)} 块, 平均 {avg_chunk_size:.1f} 字符/块",
            elapsed_ms,
            request_data
        )
        return passed
    
    def test_stream_auto_mode(self) -> bool:
        """测试 Auto 模式流式输出"""
        engine_info = self._get_server_engine_info()
        engine_type = engine_info.get("engine_type", "unknown")
        token_available = engine_info.get("token_stream_available", False)
        
        auto_mode = "Token" if token_available else "Chunk"
        self._log(f"测试 Auto 模式流式输出（服务端将自动选择 {auto_mode} 模式）...")
        
        messages = [
            {"role": "user", "content": "什么是机器学习？"}
        ]
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 80,
            "temperature": 0.7,
            "stream": True,
            "stream_options": {
                "mode": "auto"
            }
        }
        
        start_time = time.time()
        first_chunk_time = None
        response, _ = self._post_stream("/v1/chat/completions", request_data)
        
        if response is None:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_stream_auto_mode", False, "连接失败", elapsed_ms)
            return False
        
        chunks = []
        full_content = ""
        error_info = None
        
        try:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            chunks.append(chunk)
                            
                            if "error" in chunk:
                                error_info = chunk["error"]
                                continue
                            
                            if first_chunk_time is None:
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if delta.get("content"):
                                    first_chunk_time = time.time()
                            
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_stream_auto_mode", False, f"解析错误: {e}", elapsed_ms)
            return False
        
        elapsed_ms = (time.time() - start_time) * 1000
        first_content_latency = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0
        passed = len(chunks) > 0 and len(full_content) > 0 and error_info is None
        
        print(f"\n    ┌─ Auto 模式流式测试结果 ──────────────────────────────")
        print(f"    │ 📊 性能指标:")
        print(f"    │   • 实际模式: {auto_mode} 模式（服务端自动选择）")
        print(f"    │   • 服务端引擎: {engine_type}")
        print(f"    │   • 总耗时: {elapsed_ms:.0f} ms")
        print(f"    │   • 首内容延迟: {first_content_latency:.0f} ms")
        print(f"    │   • 数据块数量: {len(chunks)}")
        print(f"    │   • 输出长度: {len(full_content)} 字符")
        if error_info:
            print(f"    │   ⚠️ 服务端错误: {error_info.get('message', error_info)}")
        print(f"    └────────────────────────────────────────────────────────\n")
        
        self._record_result(
            "test_stream_auto_mode",
            passed,
            f"Auto→{auto_mode}({engine_type}): 首内容 {first_content_latency:.0f}ms, {len(chunks)} 块",
            elapsed_ms,
            request_data
        )
        return passed
    
    # ==================== 城市道路路侧车辆管理测试 ====================
    
    def test_vehicle_violation_detection(self) -> bool:
        """测试车辆违章检测场景"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试车辆违章检测场景（思考模式: {thinking_mode}）...")
        
        messages = [
            {"role": "system", "content": "你是一个城市道路路侧车辆管理系统的AI助手，负责分析车辆违章行为并提供处理建议。"},
            {"role": "user", "content": "系统检测到一辆车牌号为京A12345的白色轿车在禁停区域停放超过30分钟，请分析该违章行为并给出处理建议。"}
        ]
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        result = self._post("/v1/chat/completions", request_data, timeout=120)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        if not result["success"]:
            self._record_result("test_vehicle_violation_detection", False, result.get("error", ""), elapsed_ms, request_data, data)
            return False
        
        response_data = data.get("data", {})
        choices = response_data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        
        # 检查响应是否包含关键词
        keywords = ["违章", "停放", "处理", "罚款", "建议"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(content) > 50 and
            has_relevant_content
        )
        
        msg = f"回复长度: {len(content)}, 包含相关内容: {has_relevant_content}"
        self._record_result("test_vehicle_violation_detection", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    def test_parking_space_management(self) -> bool:
        """测试路侧停车位管理场景（双线程并发）"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试路侧停车位管理场景（双线程并发，思考模式: {thinking_mode}）...")
        
        # 定义两个不同路段的停车查询请求
        messages_1 = [
            {"role": "system", "content": "你是一个智能路侧停车管理系统的AI助手，负责分析停车数据并优化停车资源配置。"},
            {"role": "user", "content": """【A路段】当前停车数据如下：
- 总停车位：50个
- 已占用：45个
- 平均停车时长：2.5小时
- 高峰时段：8:00-10:00, 17:00-19:00
- 周转率：3.2次/天

请分析当前停车状况，并给出优化建议。"""}
        ]
        messages_1 = self._add_thinking_control(messages_1)
        
        request_data_1 = {
            "messages": messages_1,
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        messages_2 = [
            {"role": "system", "content": "你是一个智能路侧停车管理系统的AI助手，负责分析停车数据并优化停车资源配置。"},
            {"role": "user", "content": """【B路段】当前停车数据如下：
- 总停车位：80个
- 已占用：32个
- 平均停车时长：1.2小时
- 高峰时段：11:00-13:00, 18:00-20:00
- 周转率：5.8次/天
- 空闲率较高，需要分析原因

请分析当前停车状况，并给出运营建议。"""}
        ]
        messages_2 = self._add_thinking_control(messages_2)
        
        request_data_2 = {
            "messages": messages_2,
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        # 用于存储线程执行结果
        results: List[Dict[str, Any]] = [None, None]
        thread_timings: List[float] = [0, 0]
        
        def execute_request(index: int, request_data: Dict[str, Any]):
            """线程执行函数"""
            thread_name = f"Thread-{index + 1}"
            start_time = time.time()
            self._log(f"  [{thread_name}] 开始请求...")
            
            result = self._post("/v1/chat/completions", request_data, timeout=120)
            
            elapsed_ms = (time.time() - start_time) * 1000
            thread_timings[index] = elapsed_ms
            results[index] = {
                "request": request_data,
                "result": result,
                "thread_name": thread_name,
                "elapsed_ms": elapsed_ms
            }
            self._log(f"  [{thread_name}] 完成, 耗时: {elapsed_ms:.0f}ms")
        
        # 创建并启动两个线程
        overall_start = time.time()
        
        thread_1 = threading.Thread(target=execute_request, args=(0, request_data_1), name="ParkingThread-A")
        thread_2 = threading.Thread(target=execute_request, args=(1, request_data_2), name="ParkingThread-B")
        
        self._log("  启动双线程并发请求...")
        thread_1.start()
        thread_2.start()
        
        # 等待两个线程完成
        thread_1.join()
        thread_2.join()
        
        overall_elapsed = (time.time() - overall_start) * 1000
        
        # 分析两个线程的结果
        all_passed = True
        response_contents = []
        
        for i, res in enumerate(results):
            if res is None:
                all_passed = False
                continue
                
            result = res["result"]
            request_data = res["request"]
            thread_name = res["thread_name"]
            
            if not result.get("success"):
                all_passed = False
                continue
            
            data = result.get("data", {})
            response_data = data.get("data", {})
            choices = response_data.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
            
            keywords = ["停车", "占用", "优化", "建议", "管理", "分析"]
            has_relevant_content = any(kw in content for kw in keywords)
            
            thread_passed = (
                result.get("status_code") == 200 and
                data.get("code") == 0 and
                len(content) > 50 and
                has_relevant_content
            )
            
            if not thread_passed:
                all_passed = False
            
            response_contents.append({
                "thread": thread_name,
                "content_length": len(content),
                "has_relevant": has_relevant_content,
                "passed": thread_passed,
                "elapsed_ms": res["elapsed_ms"]
            })
        
        # 构造汇总响应
        summary_response = {
            "concurrent_threads": 2,
            "overall_elapsed_ms": overall_elapsed,
            "thread_results": response_contents,
            "thread_1_response": results[0]["result"].get("data", {}) if results[0] else None,
            "thread_2_response": results[1]["result"].get("data", {}) if results[1] else None
        }
        
        # 汇总请求信息
        summary_request = {
            "thread_1_request": request_data_1,
            "thread_2_request": request_data_2
        }
        
        # 计算并发效率
        sequential_time = sum(thread_timings)
        concurrency_speedup = sequential_time / overall_elapsed if overall_elapsed > 0 else 0
        
        msg = (f"并发完成, 总耗时: {overall_elapsed:.0f}ms, "
               f"线程1: {thread_timings[0]:.0f}ms, 线程2: {thread_timings[1]:.0f}ms, "
               f"并发加速比: {concurrency_speedup:.2f}x")
        
        self._record_result("test_parking_space_management", all_passed, msg, overall_elapsed, summary_request, summary_response)
        return all_passed
    
    def test_traffic_flow_analysis(self) -> bool:
        """测试交通流量分析场景"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试交通流量分析场景（思考模式: {thinking_mode}）...")
        
        messages = [
            {"role": "system", "content": "你是一个城市交通流量分析系统的AI助手，负责分析道路交通数据并提供通行优化建议。"},
            {"role": "user", "content": """路口监测数据（过去1小时）：
- 东向西车流量：1200辆
- 西向东车流量：800辆
- 南向北车流量：600辆
- 北向南车流量：650辆
- 平均车速：25km/h
- 拥堵指数：7.5（满分10）

请分析交通状况并提出疏导建议。"""}
        ]
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 400,
            "temperature": 0.7
        }
        
        result = self._post("/v1/chat/completions", request_data, timeout=120)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        if not result["success"]:
            self._record_result("test_traffic_flow_analysis", False, result.get("error", ""), elapsed_ms, request_data, data)
            return False
        
        response_data = data.get("data", {})
        choices = response_data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        
        keywords = ["交通", "车流", "拥堵", "疏导", "优化"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(content) > 50 and
            has_relevant_content
        )
        
        msg = f"回复长度: {len(content)}, 包含相关内容: {has_relevant_content}"
        self._record_result("test_traffic_flow_analysis", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    def test_vehicle_recognition_query(self) -> bool:
        """测试车辆识别查询场景"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试车辆识别查询场景（思考模式: {thinking_mode}）...")
        
        messages = [
            {"role": "system", "content": "你是一个车辆识别与追踪系统的AI助手，负责解答车辆识别相关问题。"},
            {"role": "user", "content": "系统识别到一辆可疑车辆，特征如下：车牌模糊（疑似套牌），车身有明显刮痕，多次出现在监控盲区。请分析该车辆的风险等级并给出追踪建议。"}
        ]
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        result = self._post("/v1/chat/completions", request_data, timeout=120)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        if not result["success"]:
            self._record_result("test_vehicle_recognition_query", False, result.get("error", ""), elapsed_ms, request_data, data)
            return False
        
        response_data = data.get("data", {})
        choices = response_data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        
        keywords = ["风险", "追踪", "监控", "建议", "车辆"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(content) > 50 and
            has_relevant_content
        )
        
        msg = f"回复长度: {len(content)}, 包含相关内容: {has_relevant_content}"
        self._record_result("test_vehicle_recognition_query", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    def test_road_safety_assessment(self) -> bool:
        """测试道路安全评估场景"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试道路安全评估场景（思考模式: {thinking_mode}）...")
        
        messages = [
            {"role": "system", "content": "你是一个道路安全评估系统的AI助手，负责分析道路安全隐患并提供改进建议。"},
            {"role": "user", "content": """某路段近期安全数据：
- 路段长度：2公里
- 近30天事故数：8起
- 主要事故类型：追尾（5起）、侧翻（2起）、剐蹭（1起）
- 事故高发时段：夜间22:00-02:00
- 路面状况：部分路段有坑洼
- 照明情况：3处路灯损坏

请评估该路段的安全风险等级，并提出改进措施。"""}
        ]
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 400,
            "temperature": 0.7
        }
        
        result = self._post("/v1/chat/completions", request_data, timeout=120)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        if not result["success"]:
            self._record_result("test_road_safety_assessment", False, result.get("error", ""), elapsed_ms, request_data, data)
            return False
        
        response_data = data.get("data", {})
        choices = response_data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        
        keywords = ["安全", "风险", "事故", "改进", "措施"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(content) > 50 and
            has_relevant_content
        )
        
        msg = f"回复长度: {len(content)}, 包含相关内容: {has_relevant_content}"
        self._record_result("test_road_safety_assessment", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    def test_emergency_vehicle_dispatch(self) -> bool:
        """测试应急车辆调度场景"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试应急车辆调度场景（思考模式: {thinking_mode}）...")
        
        messages = [
            {"role": "system", "content": "你是一个城市应急车辆调度系统的AI助手，负责优化应急响应路线和资源调配。"},
            {"role": "user", "content": """紧急事件报告：
- 事件类型：交通事故（多车追尾）
- 事发地点：XX路与YY街交叉口
- 伤亡情况：疑似有人员受伤
- 当前交通状况：该路段严重拥堵
- 附近可调度资源：
  - 救护车A（距离1.2km，预计5分钟）
  - 救护车B（距离2.5km，预计10分钟）
  - 交警巡逻车（距离0.8km，预计3分钟）
  - 消防车（距离3km，预计12分钟）

请制定应急响应方案和最优调度策略。"""}
        ]
        messages = self._add_thinking_control(messages)
        
        request_data = {
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        result = self._post("/v1/chat/completions", request_data, timeout=120)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        if not result["success"]:
            self._record_result("test_emergency_vehicle_dispatch", False, result.get("error", ""), elapsed_ms, request_data, data)
            return False
        
        response_data = data.get("data", {})
        choices = response_data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        
        keywords = ["调度", "响应", "救护", "交警", "方案"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(content) > 50 and
            has_relevant_content
        )
        
        msg = f"回复长度: {len(content)}, 包含相关内容: {has_relevant_content}"
        self._record_result("test_emergency_vehicle_dispatch", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    # ==================== 错误处理测试 ====================
    
    def test_invalid_request(self) -> bool:
        """测试无效请求处理"""
        self._log("测试无效请求处理...")
        
        # 缺少必要参数
        request_data = {
            "max_tokens": 100
            # 缺少 prompt 或 messages
        }
        
        result = self._post("/v1/completions", request_data)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        # 应该返回 400 或 422 错误
        passed = result["status_code"] in [400, 422] or data.get("code") != 0
        self._record_result("test_invalid_request", passed, f"状态码: {result.get('status_code')}", elapsed_ms, request_data, data)
        return passed
    
    def test_invalid_temperature(self) -> bool:
        """测试无效温度参数"""
        self._log("测试无效温度参数...")
        
        request_data = {
            "prompt": "Hello",
            "temperature": 5.0  # 超出范围 [0, 2]
        }
        
        result = self._post("/v1/completions", request_data)
        elapsed_ms = result.get("elapsed_ms", 0)
        data = result.get("data", {})
        
        # 应该返回参数验证错误
        passed = result["status_code"] in [400, 422] or data.get("code") != 0
        self._record_result("test_invalid_temperature", passed, f"状态码: {result.get('status_code')}", elapsed_ms, request_data, data)
        return passed
    
    # ==================== 运行所有测试 ====================
    
    def run_all_tests(self, skip_inference: bool = False):
        """运行所有测试"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log("=" * 60)
        self._log("开始 LLM 服务接口测试")
        self._log(f"服务地址: {self.base_url}")
        self._log(f"思考模式: {thinking_mode}")
        self._log("=" * 60)
        
        start_time = time.time()
        
        # 1. 健康检查测试
        self._log("\n--- 健康检查测试 ---")
        self.test_ops_ping()
        self.test_ops_health()
        self.test_llm_health()
        
        # 2. 模型信息测试
        self._log("\n--- 模型信息测试 ---")
        self.test_list_models()
        self.test_metrics()
        self.test_gpu_resources()
        
        if not skip_inference:
            # 3. 推理接口测试
            self._log("\n--- 推理接口测试 ---")
            self.test_completions_simple()
            self.test_completions_batch()
            self.test_chat_completions_simple()
            self.test_chat_completions_multi_turn()
            self.test_chat_completions_stream()
            
            # 4. 流式模式测试
            self._log("\n--- 流式模式测试 ---")
            self._print_engine_info()
            self.test_stream_token_mode()
            self.test_stream_chunk_mode()
            self.test_stream_auto_mode()
            
            # 5. 城市道路路侧车辆管理测试
            self._log("\n--- 城市道路路侧车辆管理测试 ---")
            self.test_vehicle_violation_detection()
            self.test_parking_space_management()
            self.test_traffic_flow_analysis()
            self.test_vehicle_recognition_query()
            self.test_road_safety_assessment()
            self.test_emergency_vehicle_dispatch()
            
            # 5. 错误处理测试
            self._log("\n--- 错误处理测试 ---")
            self.test_invalid_request()
            self.test_invalid_temperature()
        
        # 统计结果
        elapsed = time.time() - start_time
        passed_count = sum(1 for r in self.test_results if r["passed"])
        total_count = len(self.test_results)
        total_response_time = sum(r.get("elapsed_ms", 0) for r in self.test_results)
        avg_response_time = total_response_time / total_count if total_count > 0 else 0
        
        self._log("\n" + "=" * 60)
        self._log("测试结果汇总")
        self._log("=" * 60)
        self._log(f"总测试数: {total_count}")
        self._log(f"通过: {passed_count}")
        self._log(f"失败: {total_count - passed_count}")
        self._log(f"总耗时: {elapsed:.2f} 秒")
        self._log(f"总响应时间: {total_response_time:.0f} ms")
        self._log(f"平均响应时间: {avg_response_time:.0f} ms")
        self._log("=" * 60)
        
        # 打印各接口响应时间
        self._log("\n接口响应时间明细:")
        for r in self.test_results:
            status = "✓" if r["passed"] else "✗"
            self._log(f"  {status} {r['test_name']}: {r.get('elapsed_ms', 0):.0f} ms")
        
        # 打印失败的测试
        failed_tests = [r for r in self.test_results if not r["passed"]]
        if failed_tests:
            self._log("\n失败的测试:")
            for test in failed_tests:
                self._log(f"  - {test['test_name']}: {test['message']}", "ERROR")
        
        return passed_count == total_count


def main():
    parser = argparse.ArgumentParser(description="LLM 服务接口测试")
    parser.add_argument(
        "--base-url",
        type=str,
        default=SERVER_URL,
        help=f"服务地址 (默认: {SERVER_URL})"
    )
    parser.add_argument(
        "--skip-inference",
        action="store_true",
        help="跳过推理接口测试（只测试健康检查和模型信息）"
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        default=IS_THINKING,
        help="启用链式思考模式（模型会进行深度分析，响应更详细但耗时更长）"
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="禁用链式思考模式（模型直接回答，响应更快）"
    )
    
    args = parser.parse_args()
    
    # 处理思考模式参数
    enable_thinking = IS_THINKING
    if args.thinking:
        enable_thinking = True
    if args.no_thinking:
        enable_thinking = False
    
    tester = LLMServiceTest(base_url=args.base_url, enable_thinking=enable_thinking)
    success = tester.run_all_tests(skip_inference=args.skip_inference)
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()

