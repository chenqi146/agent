#!/usr/bin/env python3
'''
VLM 服务接口测试用例
测试 VLMController 提供的所有 REST API 接口（视觉语言模型）
包含城市道路路侧车辆管理相关测试用例

使用方法:
    1. 先启动服务: cd src/python && python main.py
    2. 运行测试: python vlm_test.py [--base-url http://127.0.0.1:18096]
'''
import requests
import json
import time
import argparse
import base64
import os
import re
import yaml
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List, Tuple


# 本地测试图片目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(SCRIPT_DIR, "img")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.yaml")


def load_config() -> Dict[str, Any]:
    """从 config.yaml 加载配置"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


# 从配置文件读取 SERVER_URL
_config = load_config()
SERVER_URL = _config.get('server', {}).get('base_url', 'http://127.0.0.1:8800')

# API Key 认证
API_KEY = "qjzh-vllm"

# 是否启用链式思考
IS_THINKING = True

class VLMServiceTest:
    """VLM 服务测试类"""
    
    def __init__(self, base_url: str = SERVER_URL, enable_thinking: bool = IS_THINKING, api_key: str = API_KEY):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.test_results = []
        self.enable_thinking = enable_thinking
        self.local_images = self._load_local_images()
        self._server_engine_info = None  # 缓存服务端引擎信息
    
    def _load_local_images(self) -> List[str]:
        """加载本地测试图片列表"""
        if not os.path.exists(IMG_DIR):
            return []
        images = []
        for f in sorted(os.listdir(IMG_DIR)):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                images.append(os.path.join(IMG_DIR, f))
        return images
    
    def _image_to_base64(self, image_path: str) -> str:
        """将本地图片转换为 base64 data URL"""
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 根据扩展名确定 MIME 类型
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_types.get(ext, 'image/jpeg')
        
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"
    
    def _get_server_engine_info(self) -> Dict[str, Any]:
        """获取服务端引擎信息（带缓存）"""
        if self._server_engine_info is not None:
            return self._server_engine_info
        
        try:
            response = self.session.post(
                f"{self.base_url}/vlm/metrics",
                json={},
                timeout=10
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
    
    def _add_thinking_control(self, content: str) -> str:
        """根据 enable_thinking 添加思考控制指令"""
        if "/think" in content or "/no_think" in content:
            return content
        
        if self.enable_thinking:
            return content + " /think"
        else:
            return content + " /no_think"
    
    def _extract_thinking_content(self, content: str) -> Tuple[str, str]:
        """从响应中提取思考内容和实际回复"""
        thinking = ""
        answer = content
        
        think_pattern = r'<think>(.*?)</think>'
        match = re.search(think_pattern, content, re.DOTALL)
        
        if match:
            thinking = match.group(1).strip()
            answer = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()
        
        return thinking, answer
    
    def _print_thinking_content(self, thinking: str, max_lines: int = 15):
        """格式化打印思考内容"""
        if not thinking:
            return
        
        print(f"    ┌─ 思考过程 (Thinking) ──────────────────────────────────")
        lines = thinking.split('\n')
        
        if len(lines) > max_lines:
            for line in lines[:max_lines // 2]:
                print(f"    │ {line}")
            print(f"    │ ... (省略 {len(lines) - max_lines} 行) ...")
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
    
    def _log_image_info(self, image_paths: List[str]):
        """打印使用的图片信息"""
        if isinstance(image_paths, str):
            image_paths = [image_paths]
        print(f"    📷 使用图片 ({len(image_paths)} 张):")
        for i, path in enumerate(image_paths, 1):
            print(f"       [{i}] {os.path.basename(path)}")
    
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
    
    def _post_stream(self, endpoint: str, data: Dict[str, Any], timeout: int = 180):
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
    
    def _parse_response(self, result: Dict[str, Any], test_name: str) -> tuple:
        """
        解析响应数据，处理错误情况
        
        Returns:
            (success, response_data, content, error_msg, elapsed_ms)
        """
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result.get("success"):
            return False, None, "", result.get("error", "请求失败"), elapsed_ms
        
        data = result.get("data", {}) or {}
        code = data.get("code")
        
        # 检查业务错误码
        if code != 0:
            error_msg = data.get("message", "服务返回错误")
            self._log(f"    ⚠️ 服务错误 (code={code}): {error_msg}", "WARN")
            return False, None, "", f"服务错误: {error_msg}", elapsed_ms
        
        # 获取响应数据，处理 None 情况
        response_data = data.get("data") or {}
        
        # 提取内容
        choices = response_data.get("choices", []) if isinstance(response_data, dict) else []
        content = ""
        if choices:
            message = choices[0].get("message", {}) or {}
            content = message.get("content", "")
        
        return True, response_data, content, "", elapsed_ms
    
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
        
        # 判断是否需要详细打印
        is_inference_test = any(kw in test_name for kw in 
            ["vision", "analyze", "vehicle", "parking", "plate", "license", "violation", "behavior", "time_series"])
        
        if is_inference_test:
            # 打印输入内容
            if request_data:
                self._print_request_data(request_data)
            
            # 打印输出内容
            if response_data:
                self._print_response_data(response_data)
    
    def _print_request_data(self, request_data: Dict[str, Any]):
        """格式化打印请求数据（简化版，不打印图片详情）"""
        print(f"    ┌─ 请求输入 (Request) ────────────────────────────────────")
        
        # 统计图片数量
        image_count = 0
        
        # 处理 messages 格式（vision completions）
        if "messages" in request_data:
            messages = request_data.get("messages", [])
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                
                if isinstance(content, str):
                    # 纯文本消息
                    content_preview = content[:150].replace(" /think", "").replace(" /no_think", "")
                    if len(content) > 150:
                        content_preview += "..."
                    print(f"    │ [{role}]: {content_preview}")
                elif isinstance(content, list):
                    # 多模态消息 - 只打印文本部分
                    text_parts = []
                    for item in content:
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif item.get("type") == "image_url":
                            image_count += 1
                    
                    if text_parts:
                        text = " ".join(text_parts)[:150].replace(" /think", "").replace(" /no_think", "")
                        print(f"    │ [{role}]: {text}...")
        
        # 处理 analyze 格式（单图/多图分析）
        elif "image" in request_data or "images" in request_data:
            if "prompt" in request_data:
                prompt = request_data.get("prompt", "")[:150].replace(" /think", "").replace(" /no_think", "")
                print(f"    │ 提示词: {prompt}...")
            
            if "image" in request_data:
                image_count = 1
            if "images" in request_data:
                image_count = len(request_data.get("images", []))
        
        # 显示图片数量
        if image_count > 0:
            print(f"    │ 图片: {image_count} 张")
        
        # 打印其他参数
        params = []
        if "max_tokens" in request_data:
            params.append(f"max_tokens={request_data['max_tokens']}")
        if "temperature" in request_data:
            params.append(f"temperature={request_data['temperature']}")
        if params:
            print(f"    │ 参数: {', '.join(params)}")
        
        print(f"    └────────────────────────────────────────────────────────")
    
    def _print_response_data(self, response_data: Dict[str, Any]):
        """格式化打印响应数据"""
        try:
            if not response_data:
                print(f"    ⚠️ 响应数据为空")
                return
            
            data_obj = response_data.get("data") or response_data
            if not isinstance(data_obj, dict):
                print(f"    ⚠️ 响应数据格式异常: {type(data_obj)}")
                return
            
            choices = data_obj.get("choices", []) or []
            content = ""
            
            if choices and isinstance(choices, list) and len(choices) > 0:
                msg = choices[0].get("message", {}) or {}
                content = msg.get("content", "") if isinstance(msg, dict) else ""
            
            # 也检查 description 字段（analyze 接口）
            if not content:
                content = data_obj.get("description", "") or ""
            
            if content:
                thinking, answer = self._extract_thinking_content(content)
                
                # 打印思考内容
                if thinking:
                    self._print_thinking_content(thinking)
                
                # 打印实际回复
                if answer:
                    print(f"    ┌─ 模型输出 (Response) ──────────────────────────────────")
                    lines = answer.split('\n')
                    for line in lines[:30]:
                        print(f"    │ {line}")
                    if len(lines) > 30:
                        print(f"    │ ... (省略 {len(lines) - 30} 行) ...")
                    print(f"    │ [输出长度: {len(answer)} 字符]")
                    print(f"    └────────────────────────────────────────────────────────")
            
            # 打印 usage 信息
            usage = data_obj.get("usage") or {}
            if usage and isinstance(usage, dict):
                prompt_tokens = usage.get("prompt_tokens", 0) or 0
                completion_tokens = usage.get("completion_tokens", 0) or 0
                total_tokens = usage.get("total_tokens", 0) or 0
                print(f"    📊 Token 使用: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")
        
        except Exception as e:
            print(f"    ⚠️ 解析响应失败: {e}")
    
    # ==================== 健康检查测试 ====================
    
    def test_vlm_health(self) -> bool:
        """测试 /vlm/health 接口"""
        self._log("测试 VLM Health 接口...")
        result = self._post("/vlm/health")
        
        if not result["success"]:
            self._record_result("test_vlm_health", False, result.get("error", ""))
            return False
        
        data = result["data"]
        health_data = data.get("data") or {}
        passed = result["status_code"] == 200 and data.get("code") == 0
        self._record_result(
            "test_vlm_health",
            passed,
            f"is_healthy={health_data.get('is_healthy')}, status={health_data.get('model_status')}, code={data.get('code')}, msg={data.get('message')}"
        )
        return passed
    
    def test_vlm_metrics(self) -> bool:
        """测试 /vlm/metrics 接口"""
        self._log("测试 VLM Metrics 接口...")
        result = self._post("/vlm/metrics")
        
        if not result["success"]:
            self._record_result("test_vlm_metrics", False, result.get("error", ""))
            return False
        
        data = result["data"]
        metrics = data.get("data") or {}
        passed = result["status_code"] == 200 and data.get("code") == 0
        self._record_result(
            "test_vlm_metrics",
            passed,
            f"model_type={metrics.get('model_type')}, status={metrics.get('status')}, code={data.get('code')}, msg={data.get('message')}"
        )
        return passed
    
    def test_vlm_gpu_resources(self) -> bool:
        """测试 /vlm/gpu/resources 接口"""
        self._log("测试 VLM GPU 资源接口...")
        result = self._post("/vlm/gpu/resources")
        
        if not result["success"]:
            self._record_result("test_vlm_gpu_resources", False, result.get("error", ""))
            return False
        
        data = result["data"]
        resources = data.get("data", [])
        passed = result["status_code"] == 200 and data.get("code") == 0
        
        if resources and len(resources) > 0:
            gpu_info = resources[0]
            msg = f"GPU: {gpu_info.get('gpu_name')}, 显存: {gpu_info.get('used_memory_mb', 0):.0f}/{gpu_info.get('total_memory_mb', 0):.0f} MB"
        else:
            msg = "未检测到 GPU"
        
        self._record_result("test_vlm_gpu_resources", passed, msg)
        return passed
    
    # ==================== 图像分析测试 ====================
    
    def test_analyze_single_image(self) -> bool:
        """测试 /v1/vision/analyze 接口（单图像分析）"""
        self._log("测试单图像分析接口...")
        
        if not self.local_images:
            self._record_result("test_analyze_single_image", False, "未找到本地测试图片")
            return False
        
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        request_data = {
            "image": image_base64,
            "prompt": self._add_thinking_control("请描述这张图片中的内容"),
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/analyze", request_data, timeout=180)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_analyze_single_image", False, result.get("error", ""), elapsed_ms)
            return False
        
        data = result.get("data", {}) or {}
        response_data = data.get("data") or {}
        description = response_data.get("description", "") if isinstance(response_data, dict) else ""
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(description) > 0
        )
        
        if passed:
            msg = f"图片: {os.path.basename(image_path)}, 描述长度: {len(description)}"
        else:
            msg = f"响应异常: code={data.get('code')}, message={data.get('message')}"
        
        self._record_result("test_analyze_single_image", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    def test_analyze_multi_images(self) -> bool:
        """测试 /v1/vision/analyze/multi 接口（多图像分析）"""
        self._log("测试多图像分析接口...")
        
        if len(self.local_images) < 2:
            self._record_result("test_analyze_multi_images", False, "需要至少2张本地测试图片")
            return False
        
        # 使用前两张图片
        images_to_use = self.local_images[:2]
        self._log_image_info(images_to_use)
        images_base64 = [self._image_to_base64(img) for img in images_to_use]
        
        request_data = {
            "images": images_base64,
            "prompt": self._add_thinking_control("请比较这两张图片有什么相同和不同之处"),
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/analyze/multi", request_data, timeout=240)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_analyze_multi_images", False, result.get("error", ""), elapsed_ms)
            return False
        
        data = result.get("data", {}) or {}
        response_data = data.get("data") or {}
        description = response_data.get("description", "") if isinstance(response_data, dict) else ""
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(description) > 0
        )
        
        if passed:
            msg = f"分析结果长度: {len(description)}"
        else:
            msg = f"响应异常: code={data.get('code')}, message={data.get('message')}"
        
        self._record_result("test_analyze_multi_images", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    # ==================== 视觉对话测试 ====================
    
    def test_vision_completions_simple(self) -> bool:
        """测试 /v1/vision/completions 接口（简单视觉对话）"""
        self._log("测试视觉对话接口（简单请求）...")
        
        if not self.local_images:
            self._record_result("test_vision_completions_simple", False, "未找到本地测试图片")
            return False
        
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._add_thinking_control("请描述这张图片")},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ],
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/completions", request_data, timeout=180)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_vision_completions_simple", False, result.get("error", ""), elapsed_ms)
            return False
        
        data = result.get("data", {}) or {}
        response_data = data.get("data") or {}
        choices = response_data.get("choices", []) if isinstance(response_data, dict) else []
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(choices) > 0
        )
        
        if passed and choices:
            message = choices[0].get("message", {})
            content = message.get("content", "") if isinstance(message.get("content"), str) else ""
            msg = f"回复长度: {len(content)}"
        else:
            msg = f"响应异常: code={data.get('code')}, message={data.get('message')}"
        
        self._record_result("test_vision_completions_simple", passed, msg, elapsed_ms, request_data, data)
        return passed
    
    def test_vision_completions_text_only(self) -> bool:
        """测试 /v1/vision/completions 接口（纯文本对话）"""
        self._log("测试视觉对话接口（纯文本）...")
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "你好，请介绍一下你自己"
                }
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/completions", request_data, timeout=120)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_vision_completions_text_only", False, result.get("error", ""), elapsed_ms)
            return False
        
        data = result.get("data", {}) or {}
        response_data = data.get("data") or {}
        choices = response_data.get("choices", []) if isinstance(response_data, dict) else []
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(choices) > 0
        )
        
        content = ""
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "") if isinstance(message.get("content"), str) else ""
        
        self._record_result("test_vision_completions_text_only", passed, f"回复长度: {len(content)}", elapsed_ms, request_data, data)
        return passed
    
    def test_vision_completions_multi_turn(self) -> bool:
        """测试 /v1/vision/completions 接口（多轮对话）"""
        self._log("测试视觉对话接口（多轮对话）...")
        
        if not self.local_images:
            self._record_result("test_vision_completions_multi_turn", False, "未找到本地测试图片")
            return False
        
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        request_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的停车场图像分析助手"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这张图片里有什么？"},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                },
                {
                    "role": "assistant",
                    "content": "这是一张停车场的监控图片。"
                },
                {
                    "role": "user",
                    "content": self._add_thinking_control("图中有多少辆车？")
                }
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/completions", request_data, timeout=180)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result["success"]:
            self._record_result("test_vision_completions_multi_turn", False, result.get("error", ""), elapsed_ms)
            return False
        
        data = result.get("data", {}) or {}
        response_data = data.get("data") or {}
        choices = response_data.get("choices", []) if isinstance(response_data, dict) else []
        
        passed = (
            result["status_code"] == 200 and
            data.get("code") == 0 and
            len(choices) > 0
        )
        
        content = ""
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "") if isinstance(message.get("content"), str) else ""
        
        self._record_result("test_vision_completions_multi_turn", passed, f"回复长度: {len(content)}", elapsed_ms, request_data, data)
        return passed
    
    def test_vision_completions_stream(self) -> bool:
        """测试 /v1/vision/completions 接口（流式响应）"""
        self._log("测试视觉对话接口（流式响应）...")
        
        if not self.local_images:
            self._record_result("test_vision_completions_stream", False, "未找到本地测试图片")
            return False
        
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._add_thinking_control("详细描述这张图片的内容")},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ],
            "max_tokens": 200,
            "temperature": 0.7,
            "stream": True
        }
        
        start_time = time.time()
        response, _ = self._post_stream("/v1/vision/completions", request_data)
        
        if response is None:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_vision_completions_stream", False, "连接失败", elapsed_ms)
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
            self._record_result("test_vision_completions_stream", False, f"解析错误: {e}", elapsed_ms)
            return False
        
        elapsed_ms = (time.time() - start_time) * 1000
        passed = len(chunks) > 0 and len(full_content) > 0
        
        # 打印流式输入输出
        self._print_request_data(request_data)
        if full_content:
            thinking, answer = self._extract_thinking_content(full_content)
            if thinking:
                self._print_thinking_content(thinking)
            print(f"    ┌─ 流式输出 (Stream Response) ──────────────────────────")
            lines = answer.split('\n') if answer else []
            for line in lines[:20]:
                print(f"    │ {line}")
            if len(lines) > 20:
                print(f"    │ ... (省略 {len(lines) - 20} 行) ...")
            print(f"    │ [数据块: {len(chunks)}, 输出长度: {len(full_content)} 字符]")
            print(f"    └────────────────────────────────────────────────────────")
        
        self._record_result(
            "test_vision_completions_stream",
            passed,
            f"收到 {len(chunks)} 个数据块, 内容长度: {len(full_content)}",
            elapsed_ms
        )
        return passed
    
    def test_vision_stream_token_mode(self) -> bool:
        """测试 Token 级流式输出（请求 token 模式）"""
        # 获取服务端引擎信息
        engine_info = self._get_server_engine_info()
        engine_type = engine_info.get("engine_type", "unknown")
        token_available = engine_info.get("token_stream_available", False)
        
        if token_available:
            self._log("测试 Token 级流式输出（服务端支持真正的 Token 流式）...")
        else:
            self._log("测试 Token 级流式输出（服务端将降级为 Chunk 模式）...")
        
        if not self.local_images:
            self._record_result("test_vision_stream_token_mode", False, "未找到本地测试图片")
            return False
        
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._add_thinking_control("简要描述这张图片")},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ],
            "max_tokens": 150,
            "temperature": 0.7,
            "stream": True,
            "stream_options": {
                "mode": "token",  # 使用 token 级流式
                "include_usage": True
            }
        }
        
        start_time = time.time()
        first_chunk_time = None
        response, _ = self._post_stream("/v1/vision/completions", request_data)
        
        if response is None:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_vision_stream_token_mode", False, "连接失败", elapsed_ms)
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
                            
                            # 检查是否有错误
                            if "error" in chunk:
                                error_info = chunk["error"]
                                continue
                            
                            # 记录首个内容块的时间
                            if first_chunk_time is None:
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if delta.get("content"):
                                    first_chunk_time = time.time()
                            
                            # 提取内容
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                            
                            # 提取 usage 信息
                            if "usage" in chunk:
                                usage_info = chunk["usage"]
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_vision_stream_token_mode", False, f"解析错误: {e}", elapsed_ms)
            return False
        
        elapsed_ms = (time.time() - start_time) * 1000
        first_token_latency = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0
        passed = len(chunks) > 0 and len(full_content) > 0 and error_info is None
        
        # 根据引擎类型显示不同标题
        if token_available:
            mode_title = "Token 级流式测试结果（真正的 Token 流式）"
            mode_desc = f"Token 流式（{engine_type} 引擎）"
        else:
            mode_title = "Token 级流式测试结果（降级为 Chunk 模式）"
            mode_desc = f"Token 请求 → Chunk 实际（{engine_type} 引擎）"
        
        # 打印结果
        print(f"\n    ┌─ {mode_title} ────────")
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
        # 显示引擎信息
        print(f"    │   ℹ️ 服务端引擎: {engine_type}, Token流式: {'可用' if token_available else '不可用'}")
        print(f"    ├────────────────────────────────────────────────────────")
        print(f"    │ 📝 输出内容:")
        if full_content:
            thinking, answer = self._extract_thinking_content(full_content)
            if thinking:
                self._print_thinking_content(thinking)
            lines = answer.split('\n') if answer else []
            for line in lines[:10]:
                print(f"    │ {line}")
            if len(lines) > 10:
                print(f"    │ ... (省略 {len(lines) - 10} 行) ...")
        else:
            print(f"    │ (无内容)")
        print(f"    └────────────────────────────────────────────────────────\n")
        
        self._record_result(
            "test_vision_stream_token_mode",
            passed,
            f"{mode_desc}: 首内容 {first_token_latency:.0f}ms, 共 {len(chunks)} 块",
            elapsed_ms,
            request_data
        )
        return passed
    
    def test_vision_stream_chunk_mode(self) -> bool:
        """测试 Chunk 级流式输出（分块流式）"""
        self._log("测试 Chunk 级流式输出...")
        
        if not self.local_images:
            self._record_result("test_vision_stream_chunk_mode", False, "未找到本地测试图片")
            return False
        
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        chunk_size = 20  # 每块 20 个字符
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._add_thinking_control("简要描述这张图片")},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ],
            "max_tokens": 150,
            "temperature": 0.7,
            "stream": True,
            "stream_options": {
                "mode": "chunk",  # 使用分块流式
                "chunk_size": chunk_size,
                "include_usage": True
            }
        }
        
        start_time = time.time()
        first_chunk_time = None
        response, _ = self._post_stream("/v1/vision/completions", request_data)
        
        if response is None:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_vision_stream_chunk_mode", False, "连接失败", elapsed_ms)
            return False
        
        chunks = []
        full_content = ""
        usage_info = None
        chunk_sizes = []  # 记录每个块的大小
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
                            
                            # 检查是否有错误
                            if "error" in chunk:
                                error_info = chunk["error"]
                                continue
                            
                            # 记录首个内容块的时间
                            if first_chunk_time is None:
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if delta.get("content"):
                                    first_chunk_time = time.time()
                            
                            # 提取内容
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                                chunk_sizes.append(len(content))
                            
                            # 提取 usage 信息
                            if "usage" in chunk:
                                usage_info = chunk["usage"]
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_vision_stream_chunk_mode", False, f"解析错误: {e}", elapsed_ms)
            return False
        
        elapsed_ms = (time.time() - start_time) * 1000
        first_token_latency = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
        passed = len(chunks) > 0 and len(full_content) > 0 and error_info is None
        
        # 打印结果
        print(f"\n    ┌─ Chunk 级流式测试结果 ────────────────────────────────")
        print(f"    │ 📊 性能指标:")
        print(f"    │   • 总耗时: {elapsed_ms:.0f} ms")
        print(f"    │   • 首块延迟: {first_token_latency:.0f} ms")
        print(f"    │   • 数据块数量: {len(chunks)}")
        print(f"    │   • 设定块大小: {chunk_size} 字符")
        print(f"    │   • 平均块大小: {avg_chunk_size:.1f} 字符")
        print(f"    │   • 输出长度: {len(full_content)} 字符")
        if usage_info:
            print(f"    │   • Token 统计: prompt={usage_info.get('prompt_tokens', 0)}, "
                  f"completion={usage_info.get('completion_tokens', 0)}")
        if error_info:
            print(f"    │   ⚠️ 服务端错误: {error_info.get('message', error_info)}")
        print(f"    ├────────────────────────────────────────────────────────")
        print(f"    │ 📝 输出内容:")
        if full_content:
            thinking, answer = self._extract_thinking_content(full_content)
            if thinking:
                self._print_thinking_content(thinking)
            lines = answer.split('\n') if answer else []
            for line in lines[:10]:
                print(f"    │ {line}")
            if len(lines) > 10:
                print(f"    │ ... (省略 {len(lines) - 10} 行) ...")
        else:
            print(f"    │ (无内容)")
        print(f"    └────────────────────────────────────────────────────────\n")
        
        self._record_result(
            "test_vision_stream_chunk_mode",
            passed,
            f"Chunk流式: 首块 {first_token_latency:.0f}ms, {len(chunks)} 块, 平均 {avg_chunk_size:.1f} 字符/块",
            elapsed_ms,
            request_data
        )
        return passed
    
    def test_vision_stream_auto_mode(self) -> bool:
        """测试 Auto 模式流式输出（自动选择最佳模式）"""
        # 获取服务端引擎信息
        engine_info = self._get_server_engine_info()
        engine_type = engine_info.get("engine_type", "unknown")
        token_available = engine_info.get("token_stream_available", False)
        
        auto_mode = "Token" if token_available else "Chunk"
        self._log(f"测试 Auto 模式流式输出（服务端将自动选择 {auto_mode} 模式）...")
        
        if not self.local_images:
            self._record_result("test_vision_stream_auto_mode", False, "未找到本地测试图片")
            return False
        
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._add_thinking_control("这张图片展示了什么？")},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ],
            "max_tokens": 100,
            "temperature": 0.7,
            "stream": True,
            "stream_options": {
                "mode": "auto"  # 自动选择模式
            }
        }
        
        start_time = time.time()
        first_chunk_time = None
        response, _ = self._post_stream("/v1/vision/completions", request_data)
        
        if response is None:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_result("test_vision_stream_auto_mode", False, "连接失败", elapsed_ms)
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
                            
                            # 检查是否有错误
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
            self._record_result("test_vision_stream_auto_mode", False, f"解析错误: {e}", elapsed_ms)
            return False
        
        elapsed_ms = (time.time() - start_time) * 1000
        first_token_latency = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0
        passed = len(chunks) > 0 and len(full_content) > 0 and error_info is None
        
        # 打印结果
        print(f"\n    ┌─ Auto 模式流式测试结果 ───────────────────────────────")
        print(f"    │ 📊 性能指标:")
        print(f"    │   • 实际模式: {auto_mode} 模式（服务端自动选择）")
        print(f"    │   • 服务端引擎: {engine_type}")
        print(f"    │   • 总耗时: {elapsed_ms:.0f} ms")
        print(f"    │   • 首内容延迟: {first_token_latency:.0f} ms")
        print(f"    │   • 数据块数量: {len(chunks)}")
        print(f"    │   • 输出长度: {len(full_content)} 字符")
        if error_info:
            print(f"    │   ⚠️ 服务端错误: {error_info.get('message', error_info)}")
        print(f"    ├────────────────────────────────────────────────────────")
        print(f"    │ 📝 输出内容 (前 200 字符):")
        if full_content:
            thinking, answer = self._extract_thinking_content(full_content)
            preview = answer[:200] if answer else ""
            print(f"    │ {preview}...")
        else:
            print(f"    │ (无内容)")
        print(f"    └────────────────────────────────────────────────────────\n")
        
        self._record_result(
            "test_vision_stream_auto_mode",
            passed,
            f"Auto→{auto_mode}({engine_type}): 首内容 {first_token_latency:.0f}ms, {len(chunks)} 块",
            elapsed_ms,
            request_data
        )
        return passed
    
    # ==================== 城市道路路侧车辆管理测试 ====================
    
    def test_vehicle_detection(self) -> bool:
        """测试车辆检测识别"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试车辆检测识别（思考模式: {thinking_mode}）...")
        
        if not self.local_images:
            self._record_result("test_vehicle_detection", False, "未找到本地测试图片")
            return False
        
        # 使用第一张图片
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        prompt = self._add_thinking_control(
            "请仔细分析这张停车场监控图片，识别图中的所有车辆。"
            "对于每辆车，请描述：1. 车辆类型（轿车/SUV/货车等）2. 车辆颜色 3. 车辆位置 4. 车辆朝向"
        )
        
        request_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的停车场智能监控系统，负责识别和分析停车场中的车辆信息。"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/completions", request_data, timeout=180)
        success, response_data, content, error_msg, elapsed_ms = self._parse_response(result, "test_vehicle_detection")
        
        if not success:
            self._record_result("test_vehicle_detection", False, error_msg, elapsed_ms)
            return False
        
        choices = (response_data or {}).get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        
        keywords = ["车", "轿车", "SUV", "颜色", "位置", "停"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = (
            result["status_code"] == 200 and
            (response_data or {}).get("code") == 0 and
            len(content) > 50 and
            has_relevant_content
        )
        
        msg = f"图片: {os.path.basename(image_path)}, 回复长度: {len(content)}"
        self._record_result("test_vehicle_detection", passed, msg, elapsed_ms, request_data, response_data)
        return passed
    
    def test_parking_status_detection(self) -> bool:
        """测试停车状态检测"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试停车状态检测（思考模式: {thinking_mode}）...")
        
        if not self.local_images:
            self._record_result("test_parking_status_detection", False, "未找到本地测试图片")
            return False
        
        # 使用第一张图片
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        prompt = self._add_thinking_control(
            "分析这张停车场监控图片中的停车位状态。请回答以下问题：\n"
            "1. 图中有多少个停车位？\n"
            "2. 哪些停车位是空闲的？\n"
            "3. 哪些停车位已被占用？\n"
            "4. 是否有车辆正在进行停车或离开的动作？\n"
            "5. 停车场的整体占用率大约是多少？"
        )
        
        request_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个智能停车管理系统，专门分析停车场的停车位占用情况。"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/completions", request_data, timeout=180)
        success, response_data, content, error_msg, elapsed_ms = self._parse_response(result, "test_parking_status_detection")
        
        if not success:
            self._record_result("test_parking_status_detection", False, error_msg, elapsed_ms)
            return False
        
        keywords = ["停车位", "空闲", "占用", "停车", "车辆"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = len(content) > 50 and has_relevant_content
        
        msg = f"图片: {os.path.basename(image_path)}, 回复长度: {len(content)}"
        self._record_result("test_parking_status_detection", passed, msg, elapsed_ms, request_data, result.get("data", {}))
        return passed
    
    def test_license_plate_recognition(self) -> bool:
        """测试车牌识别"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试车牌识别（思考模式: {thinking_mode}）...")
        
        if not self.local_images:
            self._record_result("test_license_plate_recognition", False, "未找到本地测试图片")
            return False
        
        # 使用第一张图片
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        prompt = self._add_thinking_control(
            "请仔细分析这张停车场监控图片，尝试识别图中所有可见的车牌号码。\n"
            "对于每个识别到的车牌，请提供：\n"
            "1. 车牌号码（如果清晰可见）\n"
            "2. 车牌类型（蓝牌/绿牌/黄牌等）\n"
            "3. 对应车辆的位置\n"
            "4. 识别置信度（高/中/低）\n"
            "如果车牌不清晰，请说明原因（距离远、角度问题、遮挡等）。"
        )
        
        request_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的车牌识别系统，能够从监控图像中识别车辆车牌信息。"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/completions", request_data, timeout=180)
        success, response_data, content, error_msg, elapsed_ms = self._parse_response(result, "test_license_plate_recognition")
        
        if not success:
            self._record_result("test_license_plate_recognition", False, error_msg, elapsed_ms)
            return False
        
        passed = len(content) > 30
        
        msg = f"图片: {os.path.basename(image_path)}, 回复长度: {len(content)}"
        self._record_result("test_license_plate_recognition", passed, msg, elapsed_ms, request_data, result.get("data", {}))
        return passed
    
    def test_vehicle_behavior_analysis(self) -> bool:
        """测试车辆行为分析"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试车辆行为分析（思考模式: {thinking_mode}）...")
        
        if len(self.local_images) < 2:
            self._record_result("test_vehicle_behavior_analysis", False, "需要至少2张图片进行行为分析")
            return False
        
        # 使用两张连续的图片进行对比分析
        image1_path = self.local_images[0]
        image2_path = self.local_images[1]
        self._log_image_info([image1_path, image2_path])
        image1_base64 = self._image_to_base64(image1_path)
        image2_base64 = self._image_to_base64(image2_path)
        
        prompt = self._add_thinking_control(
            "这是同一停车场在不同时间拍摄的两张监控图片。请分析车辆的行为变化：\n"
            "1. 对比两张图片，有哪些车辆是新进入的？\n"
            "2. 有哪些车辆已经离开？\n"
            "3. 有哪些车辆位置发生了变化？\n"
            "4. 是否有车辆正在执行停车或倒车动作？\n"
            "5. 总结停车场在这段时间内的车辆流动情况。"
        )
        
        request_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个智能交通监控分析系统，专门分析停车场车辆的行为和流动情况。"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image1_base64}},
                        {"type": "image_url", "image_url": {"url": image2_base64}}
                    ]
                }
            ],
            "max_tokens": 600,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/completions", request_data, timeout=240)
        success, response_data, content, error_msg, elapsed_ms = self._parse_response(result, "test_vehicle_behavior_analysis")
        
        if not success:
            self._record_result("test_vehicle_behavior_analysis", False, error_msg, elapsed_ms)
            return False
        
        keywords = ["车辆", "进入", "离开", "变化", "停车", "移动"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = len(content) > 50 and has_relevant_content
        
        msg = f"对比图片: {os.path.basename(image1_path)} vs {os.path.basename(image2_path)}, 回复长度: {len(content)}"
        self._record_result("test_vehicle_behavior_analysis", passed, msg, elapsed_ms, request_data, result.get("data", {}))
        return passed
    
    def test_violation_detection(self) -> bool:
        """测试违规停车检测"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试违规停车检测（思考模式: {thinking_mode}）...")
        
        if not self.local_images:
            self._record_result("test_violation_detection", False, "未找到本地测试图片")
            return False
        
        # 使用第一张图片
        image_path = self.local_images[0]
        self._log_image_info(image_path)
        image_base64 = self._image_to_base64(image_path)
        
        prompt = self._add_thinking_control(
            "作为停车场违规检测系统，请分析这张监控图片，检查是否存在以下违规行为：\n"
            "1. 是否有车辆占用多个停车位？\n"
            "2. 是否有车辆停在非停车区域（如通道、消防通道）？\n"
            "3. 是否有车辆停放角度不正确？\n"
            "4. 是否有车辆压线停放？\n"
            "5. 是否有其他违规停车行为？\n"
            "如果发现违规，请详细描述违规车辆的特征和位置。"
        )
        
        request_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个停车场违规检测AI系统，负责识别各类违规停车行为并生成报告。"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/completions", request_data, timeout=180)
        success, response_data, content, error_msg, elapsed_ms = self._parse_response(result, "test_violation_detection")
        
        if not success:
            self._record_result("test_violation_detection", False, error_msg, elapsed_ms)
            return False
        
        keywords = ["违规", "停车", "车辆", "位置", "区域", "正常"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = len(content) > 50 and has_relevant_content
        
        msg = f"图片: {os.path.basename(image_path)}, 回复长度: {len(content)}"
        self._record_result("test_violation_detection", passed, msg, elapsed_ms, request_data, result.get("data", {}))
        return passed
    
    def test_parking_time_series_analysis(self) -> bool:
        """测试停车时序分析（多图对比）"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log(f"测试停车时序分析（思考模式: {thinking_mode}）...")
        
        if len(self.local_images) < 3:
            self._record_result("test_parking_time_series_analysis", False, "需要至少3张图片进行时序分析")
            return False
        
        # 选择3张不同时间的图片
        selected_images = self.local_images[:3]
        self._log_image_info(selected_images)
        image_contents = []
        
        prompt_text = self._add_thinking_control(
            "这是同一停车场在三个不同时间点拍摄的监控图片（按时间顺序排列）。请进行时序分析：\n"
            "1. 描述每个时间点的停车场状态\n"
            "2. 分析停车位占用率的变化趋势\n"
            "3. 识别频繁进出的车辆\n"
            "4. 预测下一时段的停车场状态\n"
            "5. 给出停车场运营建议"
        )
        
        image_contents.append({"type": "text", "text": prompt_text})
        for img_path in selected_images:
            img_base64 = self._image_to_base64(img_path)
            image_contents.append({"type": "image_url", "image_url": {"url": img_base64}})
        
        request_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个智能停车场运营分析系统，擅长从多时间点图像中分析停车场的使用规律和趋势。"
                },
                {
                    "role": "user",
                    "content": image_contents
                }
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        result = self._post("/v1/vision/completions", request_data, timeout=300)
        success, response_data, content, error_msg, elapsed_ms = self._parse_response(result, "test_parking_time_series_analysis")
        
        if not success:
            self._record_result("test_parking_time_series_analysis", False, error_msg, elapsed_ms)
            return False
        
        keywords = ["变化", "趋势", "占用", "分析", "时间", "车辆"]
        has_relevant_content = any(kw in content for kw in keywords)
        
        passed = len(content) > 100 and has_relevant_content
        
        msg = f"分析图片: {len(selected_images)}张, 回复长度: {len(content)}"
        self._record_result("test_parking_time_series_analysis", passed, msg, elapsed_ms, request_data, result.get("data", {}))
        return passed
    
    # ==================== 错误处理测试 ====================
    
    def test_invalid_image_url(self) -> bool:
        """测试无效图像 URL 处理"""
        self._log("测试无效图像 URL 处理...")
        
        request_data = {
            "image": "https://invalid-url-that-does-not-exist.com/image.jpg",
            "prompt": "描述图片",
            "max_tokens": 100
        }
        
        result = self._post("/v1/vision/analyze", request_data, timeout=60)
        
        # 应该返回错误
        passed = result["status_code"] != 200 or result["data"].get("code") != 0
        self._record_result("test_invalid_image_url", passed, f"错误处理正确: {result.get('status_code')}")
        return passed
    
    def test_empty_messages(self) -> bool:
        """测试空消息列表"""
        self._log("测试空消息列表处理...")
        
        request_data = {
            "messages": [],
            "max_tokens": 100
        }
        
        result = self._post("/v1/vision/completions", request_data)
        
        # 应该返回验证错误
        passed = result["status_code"] in [400, 422] or result["data"].get("code") != 0
        self._record_result("test_empty_messages", passed, f"状态码: {result.get('status_code')}")
        return passed
    
    # ==================== 并发测试 ====================
    
    def _single_image_analysis_task(self, task_id: int, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        单个图片分析任务（用于并发测试）
        
        Args:
            task_id: 任务ID
            image_path: 图片路径
            prompt: 分析提示词
            
        Returns:
            包含任务结果的字典
        """
        thread_name = threading.current_thread().name
        image_name = os.path.basename(image_path)
        start_time = time.time()
        
        try:
            image_base64 = self._image_to_base64(image_path)
            
            request_data = {
                "image": image_base64,
                "prompt": self._add_thinking_control(prompt),
                "max_tokens": 300,
                "temperature": 0.7
            }
            
            # 使用新的 session 避免线程冲突
            response = requests.post(
                f"{self.base_url}/v1/vision/analyze",
                json=request_data,
                timeout=180,
                headers={"Content-Type": "application/json"}
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                response_data = data.get("data") or {}
                description = response_data.get("description", "") if isinstance(response_data, dict) else ""
                success = data.get("code") == 0 and len(description) > 0
                
                return {
                    "task_id": task_id,
                    "thread_name": thread_name,
                    "image_name": image_name,
                    "success": success,
                    "elapsed_ms": elapsed_ms,
                    "description_length": len(description),
                    "error": None
                }
            else:
                return {
                    "task_id": task_id,
                    "thread_name": thread_name,
                    "image_name": image_name,
                    "success": False,
                    "elapsed_ms": elapsed_ms,
                    "description_length": 0,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "task_id": task_id,
                "thread_name": thread_name,
                "image_name": image_name,
                "success": False,
                "elapsed_ms": elapsed_ms,
                "description_length": 0,
                "error": str(e)
            }
    
    def test_concurrent_image_analysis(self, num_threads: int = 3) -> bool:
        """
        测试并发图片分析
        
        Args:
            num_threads: 并发线程数，默认3个
            
        Returns:
            测试是否通过
        """
        self._log(f"测试并发图片分析（{num_threads} 个线程）...")
        
        if len(self.local_images) < num_threads:
            self._record_result(
                "test_concurrent_image_analysis", 
                False, 
                f"需要至少 {num_threads} 张本地测试图片，当前只有 {len(self.local_images)} 张"
            )
            return False
        
        # 选择图片
        selected_images = self.local_images[:num_threads]
        self._log_image_info(selected_images)
        
        # 为每个线程准备不同的提示词
        prompts = [
            "请详细描述这张图片中的内容，包括场景、物体和环境",
            "分析这张图片中的主要元素，描述它们的位置和特征",
            "请识别并描述图片中的所有可见对象及其关系"
        ]
        
        # 如果线程数超过预设提示词数量，循环使用
        while len(prompts) < num_threads:
            prompts.extend(prompts[:num_threads - len(prompts)])
        
        print(f"\n    ┌─ 并发测试开始 ──────────────────────────────────────────")
        print(f"    │ 线程数: {num_threads}")
        print(f"    │ 图片列表:")
        for i, img in enumerate(selected_images, 1):
            print(f"    │   [{i}] {os.path.basename(img)}")
        print(f"    └────────────────────────────────────────────────────────\n")
        
        total_start_time = time.time()
        results = []
        
        # 使用线程池并发执行
        with ThreadPoolExecutor(max_workers=num_threads, thread_name_prefix="VLM-Worker") as executor:
            # 提交所有任务
            futures = {
                executor.submit(
                    self._single_image_analysis_task, 
                    i, 
                    selected_images[i], 
                    prompts[i]
                ): i for i in range(num_threads)
            }
            
            # 收集结果
            for future in as_completed(futures):
                task_result = future.result()
                results.append(task_result)
                
                # 实时打印每个任务完成情况
                status = "✓" if task_result["success"] else "✗"
                print(f"    {status} 任务 {task_result['task_id'] + 1} 完成 | "
                      f"线程: {task_result['thread_name']} | "
                      f"图片: {task_result['image_name']} | "
                      f"耗时: {task_result['elapsed_ms']:.0f}ms")
        
        total_elapsed_ms = (time.time() - total_start_time) * 1000
        
        # 按任务ID排序
        results.sort(key=lambda x: x["task_id"])
        
        # 统计结果
        success_count = sum(1 for r in results if r["success"])
        total_individual_time = sum(r["elapsed_ms"] for r in results)
        avg_time = total_individual_time / len(results) if results else 0
        min_time = min(r["elapsed_ms"] for r in results) if results else 0
        max_time = max(r["elapsed_ms"] for r in results) if results else 0
        
        # 计算并发加速比（如果串行执行需要的时间 vs 实际并发时间）
        speedup = total_individual_time / total_elapsed_ms if total_elapsed_ms > 0 else 1
        
        # 打印性能统计
        print(f"\n    ┌─ 并发测试性能统计 ────────────────────────────────────────")
        print(f"    │ 总任务数: {num_threads}")
        print(f"    │ 成功任务: {success_count}")
        print(f"    │ 失败任务: {num_threads - success_count}")
        print(f"    ├────────────────────────────────────────────────────────")
        print(f"    │ 📊 时间统计:")
        print(f"    │   • 并发总耗时: {total_elapsed_ms:.0f} ms")
        print(f"    │   • 单任务累计: {total_individual_time:.0f} ms")
        print(f"    │   • 平均单任务: {avg_time:.0f} ms")
        print(f"    │   • 最快任务: {min_time:.0f} ms")
        print(f"    │   • 最慢任务: {max_time:.0f} ms")
        print(f"    │   • 并发加速比: {speedup:.2f}x")
        print(f"    ├────────────────────────────────────────────────────────")
        print(f"    │ 📋 各任务详情:")
        for r in results:
            status = "✓" if r["success"] else "✗"
            error_info = f" | 错误: {r['error']}" if r["error"] else ""
            print(f"    │   {status} 任务{r['task_id'] + 1}: {r['image_name']} | "
                  f"{r['elapsed_ms']:.0f}ms | 描述长度: {r['description_length']}{error_info}")
        print(f"    └────────────────────────────────────────────────────────\n")
        
        # 判断测试是否通过
        passed = success_count == num_threads
        
        msg = (f"并发数: {num_threads}, 成功: {success_count}/{num_threads}, "
               f"总耗时: {total_elapsed_ms:.0f}ms, 加速比: {speedup:.2f}x")
        
        self._record_result("test_concurrent_image_analysis", passed, msg, total_elapsed_ms)
        return passed
    
    # ==================== 运行所有测试 ====================
    
    def run_all_tests(self, skip_inference: bool = False, skip_vehicle: bool = False):
        """运行所有测试"""
        thinking_mode = "启用" if self.enable_thinking else "禁用"
        self._log("=" * 60)
        self._log("开始 VLM 服务接口测试")
        self._log(f"服务地址: {self.base_url}")
        self._log(f"思考模式: {thinking_mode}")
        self._log(f"本地测试图片: {len(self.local_images)} 张")
        self._log("=" * 60)
        
        start_time = time.time()
        
        # 1. 健康检查测试
        self._log("\n--- VLM 健康检查测试 ---")
        self.test_vlm_health()
        self.test_vlm_metrics()
        self.test_vlm_gpu_resources()
        
        if not skip_inference:
            # 2. 图像分析测试
            self._log("\n--- 图像分析测试 ---")
            self.test_analyze_single_image()
            self.test_analyze_multi_images()
            
            # 3. 视觉对话测试
            self._log("\n--- 视觉对话测试 ---")
            self.test_vision_completions_simple()
            self.test_vision_completions_text_only()
            self.test_vision_completions_multi_turn()
            self.test_vision_completions_stream()
            
            # 4. 流式模式测试
            self._log("\n--- 流式模式测试 ---")
            self._print_engine_info()
            self.test_vision_stream_token_mode()
            self.test_vision_stream_chunk_mode()
            self.test_vision_stream_auto_mode()
        
        if not skip_vehicle and self.local_images:
            # 5. 城市道路路侧车辆管理测试
            self._log("\n--- 城市道路路侧车辆管理测试 ---")
            self.test_vehicle_detection()
            self.test_parking_status_detection()
            self.test_license_plate_recognition()
            self.test_vehicle_behavior_analysis()
            self.test_violation_detection()
            self.test_parking_time_series_analysis()
        
        if not skip_inference:
            # 6. 错误处理测试
            self._log("\n--- 错误处理测试 ---")
            self.test_invalid_image_url()
            self.test_empty_messages()
        
        if not skip_inference and len(self.local_images) >= 3:
            # 7. 并发性能测试
            self._log("\n--- 并发性能测试 ---")
            self.test_concurrent_image_analysis(num_threads=3)
        
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
    parser = argparse.ArgumentParser(description="VLM 服务接口测试（含城市道路路侧车辆管理）")
    parser.add_argument(
        "--base-url",
        type=str,
        default=SERVER_URL,
        help=f"服务地址 (默认: {SERVER_URL})"
    )
    parser.add_argument(
        "--skip-inference",
        action="store_true",
        help="跳过推理接口测试（只测试健康检查）"
    )
    parser.add_argument(
        "--skip-vehicle",
        action="store_true",
        help="跳过车辆管理测试"
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        default=IS_THINKING,
        help="启用链式思考模式"
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="禁用链式思考模式"
    )
    parser.add_argument(
        "--concurrent-only",
        action="store_true",
        help="只运行并发测试"
    )
    parser.add_argument(
        "--concurrent-threads",
        type=int,
        default=3,
        help="并发测试线程数 (默认: 3)"
    )
    parser.add_argument(
        "--stream-only",
        action="store_true",
        help="只运行流式模式测试"
    )
    parser.add_argument(
        "--stream-mode",
        type=str,
        choices=["token", "chunk", "auto", "all"],
        default="all",
        help="流式测试模式: token/chunk/auto/all (默认: all)"
    )
    
    args = parser.parse_args()
    
    # 处理思考模式参数
    enable_thinking = IS_THINKING
    if args.thinking:
        enable_thinking = True
    if args.no_thinking:
        enable_thinking = False
    
    tester = VLMServiceTest(base_url=args.base_url, enable_thinking=enable_thinking)
    
    # 只运行流式测试
    if args.stream_only:
        tester._log("=" * 60)
        tester._log("单独运行流式模式测试")
        tester._log(f"服务地址: {tester.base_url}")
        tester._log(f"测试模式: {args.stream_mode}")
        tester._log(f"本地测试图片: {len(tester.local_images)} 张")
        tester._print_engine_info()
        tester._log("=" * 60)
        
        results = []
        if args.stream_mode in ["token", "all"]:
            results.append(("Token模式", tester.test_vision_stream_token_mode()))
        if args.stream_mode in ["chunk", "all"]:
            results.append(("Chunk模式", tester.test_vision_stream_chunk_mode()))
        if args.stream_mode in ["auto", "all"]:
            results.append(("Auto模式", tester.test_vision_stream_auto_mode()))
        
        # 打印结果
        tester._log("\n" + "=" * 60)
        tester._log("流式测试结果汇总")
        tester._log("=" * 60)
        all_passed = True
        for name, passed in results:
            status = "✓ 通过" if passed else "✗ 失败"
            tester._log(f"  {status}: {name}")
            if not passed:
                all_passed = False
        tester._log("=" * 60)
        exit(0 if all_passed else 1)
    
    # 只运行并发测试
    if args.concurrent_only:
        tester._log("=" * 60)
        tester._log("单独运行并发性能测试")
        tester._log(f"服务地址: {tester.base_url}")
        tester._log(f"并发线程数: {args.concurrent_threads}")
        tester._log(f"本地测试图片: {len(tester.local_images)} 张")
        tester._log("=" * 60)
        success = tester.test_concurrent_image_analysis(num_threads=args.concurrent_threads)
        exit(0 if success else 1)
    
    success = tester.run_all_tests(
        skip_inference=args.skip_inference,
        skip_vehicle=args.skip_vehicle
    )
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()

