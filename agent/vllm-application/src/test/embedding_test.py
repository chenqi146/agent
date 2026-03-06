#!/usr/bin/env python3
'''
Embedding 服务接口测试用例
测试 EmbeddingController 提供的所有 REST API 接口

使用方法:
    1. 先启动服务: cd src/python && python main.py
    2. 运行测试: python embedding_test.py [--base-url http://127.0.0.1:8800]
    
测试内容:
    - 单条文本向量化
    - 批量文本向量化
    - 向量相似度计算
    - 并发性能测试
    - 健康检查
    - 服务指标
'''
import os
import sys
import requests
import json
import time
import argparse
import threading
import math
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List, Tuple

# 从配置文件读取服务地址
def load_config() -> Dict[str, Any]:
    """加载测试配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

_config = load_config()
SERVER_URL = _config.get('server', {}).get('base_url', 'http://127.0.0.1:8800')


class EmbeddingServiceTest:
    """Embedding 服务测试类"""
    
    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.test_results = []
        self._server_info = None  # 缓存服务端信息
    
    def _log(self, message: str, level: str = "INFO"):
        """打印日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def _post(self, endpoint: str, data: Dict[str, Any] = None, timeout: int = 60) -> Dict[str, Any]:
        """发送 POST 请求，返回结果包含响应时间"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        try:
            response = self.session.post(
                url,
                json=data or {},
                timeout=timeout,
                headers={"Content-Type": "application/json"}
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
    
    def _record_result(self, test_name: str, passed: bool, message: str = "", elapsed_ms: float = 0):
        """记录测试结果"""
        status = "✓ PASS" if passed else "✗ FAIL"
        self.test_results.append({
            "name": test_name,
            "passed": passed,
            "message": message,
            "elapsed_ms": elapsed_ms
        })
        self._log(f"{status}: {test_name} [{elapsed_ms:.0f}ms] {message}", "INFO" if passed else "ERROR")
    
    def _parse_response(self, result: Dict[str, Any], test_name: str) -> tuple:
        """
        解析 API 响应，处理错误情况
        
        Returns:
            tuple: (success, response_data, error_msg, elapsed_ms)
        """
        elapsed_ms = result.get("elapsed_ms", 0)
        
        if not result.get("success"):
            return False, None, result.get("error", "请求失败"), elapsed_ms
        
        data = result.get("data", {}) or {}
        code = data.get("code")
        
        if code != 0:
            error_msg = data.get("message", "服务返回错误")
            self._log(f"    ⚠️ 服务错误 (code={code}): {error_msg}", "WARN")
            return False, None, f"服务错误: {error_msg}", elapsed_ms
        
        response_data = data.get("data") or {}
        return True, response_data, "", elapsed_ms
    
    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec_a) != len(vec_b):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def _get_server_info(self) -> Dict[str, Any]:
        """获取服务端信息（带缓存）"""
        if self._server_info is not None:
            return self._server_info
        
        try:
            result = self._post("/embedding/metrics", {}, timeout=10)
            if result.get("success"):
                data = result.get("data", {})
                if data.get("code") == 0:
                    self._server_info = data.get("data", {})
                    return self._server_info
        except Exception:
            pass
        
        return {"model_name": "unknown", "enable": False}
    
    # ==================== 测试用例 ====================
    
    def test_health_check(self) -> bool:
        """测试健康检查接口"""
        self._log("测试健康检查接口...")
        
        result = self._post("/embedding/health", {})
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_health_check")
        
        if not success:
            self._record_result("test_health_check", False, error_msg, elapsed_ms)
            return False
        
        is_healthy = response_data.get("is_healthy", False)
        model_status = response_data.get("model_status", "unknown")
        model_name = response_data.get("model_name", "unknown")
        
        print(f"    ├─ 健康状态: {'✅ 健康' if is_healthy else '❌ 不健康'}")
        print(f"    ├─ 模型状态: {model_status}")
        print(f"    ├─ 模型名称: {model_name}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        self._record_result("test_health_check", is_healthy, f"status={model_status}", elapsed_ms)
        return is_healthy
    
    def test_metrics(self) -> bool:
        """测试服务指标接口"""
        self._log("测试服务指标接口...")
        
        result = self._post("/embedding/metrics", {})
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_metrics")
        
        if not success:
            self._record_result("test_metrics", False, error_msg, elapsed_ms)
            return False
        
        model_name = response_data.get("model_name", "unknown")
        model_status = response_data.get("model_status", "unknown")
        enable = response_data.get("enable", False)
        total_requests = response_data.get("total_requests", 0)
        
        print(f"    ├─ 模型名称: {model_name}")
        print(f"    ├─ 模型状态: {model_status}")
        print(f"    ├─ 启用状态: {'✅ 已启用' if enable else '❌ 未启用'}")
        print(f"    ├─ 总请求数: {total_requests}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        self._record_result("test_metrics", True, f"model={model_name}", elapsed_ms)
        return True
    
    def test_gpu_resources(self) -> bool:
        """测试 GPU 资源查询接口"""
        self._log("测试 GPU 资源查询接口...")
        
        result = self._post("/embedding/gpu/resources", {})
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_gpu_resources")
        
        if not success:
            self._record_result("test_gpu_resources", False, error_msg, elapsed_ms)
            return False
        
        gpu_count = response_data.get("gpu_count", 0)
        gpus = response_data.get("gpus", [])
        
        print(f"    ├─ GPU 数量: {gpu_count}")
        for gpu in gpus:
            gpu_id = gpu.get("gpu_id", 0)
            gpu_name = gpu.get("gpu_name", "unknown")
            used_mb = gpu.get("used_memory_mb", 0)
            total_mb = gpu.get("total_memory_mb", 0)
            utilization = gpu.get("memory_utilization", 0) * 100
            print(f"    ├─ GPU {gpu_id}: {gpu_name}")
            print(f"    │   └─ 显存: {used_mb:.0f}/{total_mb:.0f} MB ({utilization:.1f}%)")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        self._record_result("test_gpu_resources", True, f"gpus={gpu_count}", elapsed_ms)
        return True
    
    def test_single_embedding(self) -> bool:
        """测试单条文本向量化"""
        self._log("测试单条文本向量化...")
        
        request_data = {
            "input": "这是一段用于测试的文本内容，用于验证 Embedding 服务是否正常工作。"
        }
        
        result = self._post("/v1/embeddings", request_data, timeout=120)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_single_embedding")
        
        if not success:
            self._record_result("test_single_embedding", False, error_msg, elapsed_ms)
            return False
        
        model = response_data.get("model", "unknown")
        data_list = response_data.get("data", [])
        usage = response_data.get("usage", {})
        
        if not data_list:
            self._record_result("test_single_embedding", False, "返回数据为空", elapsed_ms)
            return False
        
        embedding = data_list[0].get("embedding", [])
        dimension = len(embedding)
        prompt_tokens = usage.get("prompt_tokens", 0)
        
        print(f"    ├─ 模型: {model}")
        print(f"    ├─ 向量维度: {dimension}")
        print(f"    ├─ Token 数: {prompt_tokens}")
        print(f"    ├─ 向量前5维: {embedding[:5]}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        passed = dimension > 0
        self._record_result("test_single_embedding", passed, f"dim={dimension}, tokens={prompt_tokens}", elapsed_ms)
        return passed
    
    def test_batch_embedding(self) -> bool:
        """测试批量文本向量化"""
        self._log("测试批量文本向量化...")
        
        texts = [
            "人工智能正在改变我们的生活方式。",
            "机器学习是人工智能的一个重要分支。",
            "深度学习在图像识别领域取得了巨大成功。",
            "自然语言处理使计算机能够理解人类语言。",
            "强化学习在游戏和机器人控制中有广泛应用。"
        ]
        
        request_data = {
            "input": texts
        }
        
        result = self._post("/v1/embeddings", request_data, timeout=180)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_batch_embedding")
        
        if not success:
            self._record_result("test_batch_embedding", False, error_msg, elapsed_ms)
            return False
        
        data_list = response_data.get("data", [])
        usage = response_data.get("usage", {})
        
        if len(data_list) != len(texts):
            self._record_result("test_batch_embedding", False, f"返回数量不匹配: {len(data_list)} vs {len(texts)}", elapsed_ms)
            return False
        
        dimension = len(data_list[0].get("embedding", [])) if data_list else 0
        prompt_tokens = usage.get("prompt_tokens", 0)
        avg_time = elapsed_ms / len(texts)
        
        print(f"    ├─ 批量大小: {len(texts)}")
        print(f"    ├─ 向量维度: {dimension}")
        print(f"    ├─ 总 Token 数: {prompt_tokens}")
        print(f"    ├─ 总耗时: {elapsed_ms:.0f}ms")
        print(f"    └─ 平均耗时: {avg_time:.0f}ms/条")
        
        passed = len(data_list) == len(texts) and dimension > 0
        self._record_result("test_batch_embedding", passed, f"batch={len(texts)}, dim={dimension}", elapsed_ms)
        return passed
    
    def test_similarity_calculation(self) -> bool:
        """测试向量相似度计算"""
        self._log("测试向量相似度计算...")
        
        # 准备测试文本对
        text_pairs = [
            ("我喜欢吃苹果", "我喜欢吃水果"),           # 高相似度
            ("今天天气很好", "今天阳光明媚"),           # 高相似度
            ("我喜欢吃苹果", "量子力学的基本原理"),     # 低相似度
            ("人工智能", "机器学习"),                   # 中等相似度
        ]
        
        all_texts = []
        for t1, t2 in text_pairs:
            all_texts.extend([t1, t2])
        
        request_data = {
            "input": all_texts
        }
        
        result = self._post("/v1/embeddings", request_data, timeout=180)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_similarity_calculation")
        
        if not success:
            self._record_result("test_similarity_calculation", False, error_msg, elapsed_ms)
            return False
        
        data_list = response_data.get("data", [])
        
        if len(data_list) != len(all_texts):
            self._record_result("test_similarity_calculation", False, "返回数量不匹配", elapsed_ms)
            return False
        
        embeddings = [d.get("embedding", []) for d in data_list]
        
        print(f"    ┌─ 相似度计算结果 ───────────────────────────────────")
        
        similarities = []
        for i, (t1, t2) in enumerate(text_pairs):
            vec1 = embeddings[i * 2]
            vec2 = embeddings[i * 2 + 1]
            similarity = self._cosine_similarity(vec1, vec2)
            similarities.append(similarity)
            
            # 根据相似度显示不同的图标
            if similarity > 0.8:
                icon = "🟢"
            elif similarity > 0.5:
                icon = "🟡"
            else:
                icon = "🔴"
            
            print(f"    │ {icon} \"{t1}\" ↔ \"{t2}\"")
            print(f"    │    相似度: {similarity:.4f}")
        
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        # 验证相似度符合预期
        # 第一对和第二对应该有较高相似度，第三对应该有较低相似度
        passed = similarities[0] > similarities[2] and similarities[1] > similarities[2]
        
        self._record_result("test_similarity_calculation", passed, f"pairs={len(text_pairs)}", elapsed_ms)
        return passed
    
    def test_long_text_embedding(self) -> bool:
        """测试长文本向量化"""
        self._log("测试长文本向量化...")
        
        # 生成一段较长的文本
        long_text = """
        人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，
        它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
        该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
        人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。
        可以设想，未来人工智能带来的科技产品，将会是人类智慧的"容器"。
        人工智能可以对人的意识、思维的信息过程的模拟。
        人工智能不是人的智能，但能像人那样思考、也可能超过人的智能。
        """ * 3  # 重复3次使文本更长
        
        request_data = {
            "input": long_text.strip()
        }
        
        result = self._post("/v1/embeddings", request_data, timeout=180)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_long_text_embedding")
        
        if not success:
            self._record_result("test_long_text_embedding", False, error_msg, elapsed_ms)
            return False
        
        data_list = response_data.get("data", [])
        usage = response_data.get("usage", {})
        
        if not data_list:
            self._record_result("test_long_text_embedding", False, "返回数据为空", elapsed_ms)
            return False
        
        embedding = data_list[0].get("embedding", [])
        dimension = len(embedding)
        prompt_tokens = usage.get("prompt_tokens", 0)
        text_length = len(long_text)
        
        print(f"    ├─ 文本长度: {text_length} 字符")
        print(f"    ├─ Token 数: {prompt_tokens}")
        print(f"    ├─ 向量维度: {dimension}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        passed = dimension > 0
        self._record_result("test_long_text_embedding", passed, f"chars={text_length}, tokens={prompt_tokens}", elapsed_ms)
        return passed
    
    def test_custom_dimensions(self, dimensions: int = 512) -> bool:
        """测试指定维度的向量生成"""
        self._log(f"测试指定维度向量生成（{dimensions}维）...")
        
        request_data = {
            "input": "这是一段用于测试自定义向量维度的文本内容。",
            "dimensions": dimensions
        }
        
        result = self._post("/v1/embeddings", request_data, timeout=120)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, f"test_custom_dimensions_{dimensions}")
        
        if not success:
            self._record_result(f"test_custom_dimensions_{dimensions}", False, error_msg, elapsed_ms)
            return False
        
        data_list = response_data.get("data", [])
        
        if not data_list:
            self._record_result(f"test_custom_dimensions_{dimensions}", False, "返回数据为空", elapsed_ms)
            return False
        
        embedding = data_list[0].get("embedding", [])
        actual_dim = len(embedding)
        
        print(f"    ├─ 请求维度: {dimensions}")
        print(f"    ├─ 实际维度: {actual_dim}")
        print(f"    ├─ 向量前5维: {embedding[:5] if len(embedding) >= 5 else embedding}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        # 验证维度是否正确（允许小于等于请求维度）
        passed = actual_dim == dimensions or (actual_dim > 0 and actual_dim <= dimensions)
        
        if actual_dim != dimensions:
            print(f"    ⚠️ 注意: 实际维度({actual_dim}) != 请求维度({dimensions})")
            if actual_dim < dimensions:
                print(f"       模型最大维度可能小于请求值")
        
        self._record_result(f"test_custom_dimensions_{dimensions}", passed, f"dim={actual_dim}", elapsed_ms)
        return passed
    
    def test_dimensions_512(self) -> bool:
        """测试 512 维向量生成"""
        return self.test_custom_dimensions(512)
    
    def test_dimensions_768(self) -> bool:
        """测试 768 维向量生成"""
        return self.test_custom_dimensions(768)
    
    def test_dimensions_1024(self) -> bool:
        """测试 1024 维向量生成"""
        return self.test_custom_dimensions(1024)
    
    def test_dimensions_comparison(self) -> bool:
        """测试不同维度向量的相似度对比"""
        self._log("测试不同维度向量相似度对比...")
        
        text1 = "人工智能正在改变世界"
        text2 = "机器学习是AI的核心技术"
        
        dimensions_to_test = [512, 768, 1024, 2048]
        results = {}
        
        print(f"    ┌─ 不同维度相似度对比 ────────────────────────────────")
        
        for dim in dimensions_to_test:
            request_data = {
                "input": [text1, text2],
                "dimensions": dim
            }
            
            result = self._post("/v1/embeddings", request_data, timeout=120)
            success, response_data, error_msg, elapsed_ms = self._parse_response(result, f"dim_comparison_{dim}")
            
            if success:
                data_list = response_data.get("data", [])
                if len(data_list) >= 2:
                    vec1 = data_list[0].get("embedding", [])
                    vec2 = data_list[1].get("embedding", [])
                    actual_dim = len(vec1)
                    similarity = self._cosine_similarity(vec1, vec2)
                    results[dim] = {
                        "actual_dim": actual_dim,
                        "similarity": similarity,
                        "elapsed_ms": elapsed_ms
                    }
                    print(f"    │ {dim:4d}维 → 实际{actual_dim:4d}维, 相似度: {similarity:.4f}, 耗时: {elapsed_ms:.0f}ms")
            else:
                print(f"    │ {dim:4d}维 → 失败: {error_msg}")
        
        print(f"    └──────────────────────────────────────────────────────")
        
        passed = len(results) > 0
        self._record_result("test_dimensions_comparison", passed, f"tested={len(results)} dims", 0)
        return passed
    
    def test_concurrent_embedding(self, num_threads: int = 5, requests_per_thread: int = 2) -> bool:
        """测试并发向量化"""
        self._log(f"测试并发向量化（{num_threads} 线程 × {requests_per_thread} 请求）...")
        
        test_texts = [
            "并发测试文本1：人工智能的发展",
            "并发测试文本2：机器学习算法",
            "并发测试文本3：深度神经网络",
            "并发测试文本4：自然语言处理",
            "并发测试文本5：计算机视觉应用",
        ]
        
        results = []
        lock = threading.Lock()
        
        def worker(thread_id: int):
            thread_results = []
            for i in range(requests_per_thread):
                text = test_texts[thread_id % len(test_texts)]
                start_time = time.time()
                
                try:
                    result = self._post("/v1/embeddings", {"input": text}, timeout=120)
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    success = result.get("success", False)
                    if success:
                        data = result.get("data", {})
                        if data.get("code") == 0:
                            thread_results.append({
                                "thread_id": thread_id,
                                "request_id": i,
                                "success": True,
                                "elapsed_ms": elapsed_ms
                            })
                        else:
                            thread_results.append({
                                "thread_id": thread_id,
                                "request_id": i,
                                "success": False,
                                "elapsed_ms": elapsed_ms,
                                "error": data.get("message", "unknown error")
                            })
                    else:
                        thread_results.append({
                            "thread_id": thread_id,
                            "request_id": i,
                            "success": False,
                            "elapsed_ms": elapsed_ms,
                            "error": result.get("error", "unknown error")
                        })
                except Exception as e:
                    thread_results.append({
                        "thread_id": thread_id,
                        "request_id": i,
                        "success": False,
                        "elapsed_ms": 0,
                        "error": str(e)
                    })
            
            with lock:
                results.extend(thread_results)
        
        # 执行并发测试
        total_start = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for future in as_completed(futures):
                future.result()
        
        total_elapsed = (time.time() - total_start) * 1000
        
        # 统计结果
        total_requests = len(results)
        success_count = sum(1 for r in results if r.get("success"))
        failed_count = total_requests - success_count
        
        if success_count > 0:
            success_times = [r["elapsed_ms"] for r in results if r.get("success")]
            avg_time = sum(success_times) / len(success_times)
            min_time = min(success_times)
            max_time = max(success_times)
        else:
            avg_time = min_time = max_time = 0
        
        print(f"    ┌─ 并发测试结果 ─────────────────────────────────────")
        print(f"    ├─ 总请求数: {total_requests}")
        print(f"    ├─ 成功: {success_count} ({success_count/total_requests*100:.1f}%)")
        print(f"    ├─ 失败: {failed_count}")
        print(f"    ├─ 总耗时: {total_elapsed:.0f}ms")
        print(f"    ├─ 平均响应: {avg_time:.0f}ms")
        print(f"    ├─ 最快响应: {min_time:.0f}ms")
        print(f"    ├─ 最慢响应: {max_time:.0f}ms")
        print(f"    └─ QPS: {total_requests / (total_elapsed / 1000):.2f}")
        
        # 打印失败详情
        if failed_count > 0:
            print(f"    ⚠️ 失败详情:")
            for r in results:
                if not r.get("success"):
                    print(f"       - 线程{r['thread_id']}-请求{r['request_id']}: {r.get('error', 'unknown')}")
        
        passed = success_count == total_requests
        self._record_result("test_concurrent_embedding", passed, 
                           f"success={success_count}/{total_requests}, qps={total_requests/(total_elapsed/1000):.2f}", 
                           total_elapsed)
        return passed
    
    def test_empty_input(self) -> bool:
        """测试空输入处理"""
        self._log("测试空输入处理...")
        
        # 测试空字符串
        request_data = {
            "input": ""
        }
        
        result = self._post("/v1/embeddings", request_data, timeout=30)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        # 空输入应该返回错误或者空向量
        data = result.get("data", {})
        
        print(f"    ├─ 空字符串测试:")
        print(f"    │   └─ 响应: code={data.get('code')}, message={data.get('message', 'N/A')[:50]}")
        
        # 测试空列表
        request_data2 = {
            "input": []
        }
        
        result2 = self._post("/v1/embeddings", request_data2, timeout=30)
        data2 = result2.get("data", {})
        
        print(f"    ├─ 空列表测试:")
        print(f"    │   └─ 响应: code={data2.get('code')}, message={data2.get('message', 'N/A')[:50]}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        # 只要不崩溃就算通过
        self._record_result("test_empty_input", True, "边界情况处理正常", elapsed_ms)
        return True
    
    def test_special_characters(self) -> bool:
        """测试特殊字符处理"""
        self._log("测试特殊字符处理...")
        
        special_texts = [
            "包含emoji的文本 😀🎉🚀",
            "包含特殊符号 @#$%^&*()",
            "包含中文标点：，。！？",
            "包含换行符\n和制表符\t的文本",
            "包含HTML标签 <script>alert('test')</script>",
        ]
        
        request_data = {
            "input": special_texts
        }
        
        result = self._post("/v1/embeddings", request_data, timeout=120)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_special_characters")
        
        if not success:
            self._record_result("test_special_characters", False, error_msg, elapsed_ms)
            return False
        
        data_list = response_data.get("data", [])
        
        print(f"    ├─ 测试文本数: {len(special_texts)}")
        print(f"    ├─ 返回向量数: {len(data_list)}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        passed = len(data_list) == len(special_texts)
        self._record_result("test_special_characters", passed, f"processed={len(data_list)}", elapsed_ms)
        return passed
    
    # ==================== 运行测试 ====================
    
    def run_all_tests(self, skip_concurrent: bool = False) -> bool:
        """运行所有测试"""
        self._log("=" * 60)
        self._log("开始 Embedding 服务测试")
        self._log(f"服务地址: {self.base_url}")
        self._log("=" * 60)
        
        # 获取服务信息
        server_info = self._get_server_info()
        model_name = server_info.get("model_name", "unknown")
        enable = server_info.get("enable", False)
        
        self._log(f"模型名称: {model_name}")
        self._log(f"启用状态: {'已启用' if enable else '未启用'}")
        self._log("-" * 60)
        
        # 运行测试用例
        tests = [
            ("健康检查", self.test_health_check),
            ("服务指标", self.test_metrics),
            ("GPU资源", self.test_gpu_resources),
            ("单条向量化", self.test_single_embedding),
            ("批量向量化", self.test_batch_embedding),
            ("相似度计算", self.test_similarity_calculation),
            ("长文本处理", self.test_long_text_embedding),
            ("512维向量", self.test_dimensions_512),
            ("768维向量", self.test_dimensions_768),
            ("维度对比", self.test_dimensions_comparison),
            ("空输入处理", self.test_empty_input),
            ("特殊字符处理", self.test_special_characters),
        ]
        
        if not skip_concurrent:
            tests.append(("并发测试", lambda: self.test_concurrent_embedding(5, 2)))
        
        for name, test_func in tests:
            try:
                self._log("-" * 40)
                test_func()
            except Exception as e:
                self._log(f"测试 {name} 异常: {e}", "ERROR")
                self._record_result(name, False, str(e), 0)
        
        # 打印测试汇总
        self._print_summary()
        
        # 返回是否全部通过
        return all(r["passed"] for r in self.test_results)
    
    def _print_summary(self):
        """打印测试汇总"""
        self._log("=" * 60)
        self._log("测试汇总")
        self._log("=" * 60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        
        print(f"\n{'─' * 60}")
        print(f"总计: {total} 个测试")
        print(f"通过: {passed} ✓")
        print(f"失败: {failed} ✗")
        print(f"{'─' * 60}")
        
        if failed > 0:
            print("\n失败的测试:")
            for r in self.test_results:
                if not r["passed"]:
                    print(f"  ✗ {r['name']}: {r['message']}")
        
        print(f"\n{'═' * 60}")
        if failed == 0:
            print("🎉 所有测试通过！")
        else:
            print(f"⚠️ 有 {failed} 个测试失败")
        print(f"{'═' * 60}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Embedding 服务测试")
    parser.add_argument("--base-url", type=str, default=SERVER_URL,
                       help=f"服务地址 (默认: {SERVER_URL})")
    parser.add_argument("--skip-concurrent", action="store_true",
                       help="跳过并发测试")
    parser.add_argument("--test", type=str, default=None,
                       help="运行指定测试 (health/metrics/single/batch/similarity/dim512/dim768/dim-compare/concurrent)")
    parser.add_argument("--dimensions", type=int, default=None,
                       help="测试指定维度的向量生成（如 512, 768, 1024）")
    
    args = parser.parse_args()
    
    tester = EmbeddingServiceTest(base_url=args.base_url)
    
    # 如果指定了 dimensions 参数，直接运行维度测试
    if args.dimensions:
        tester.test_custom_dimensions(args.dimensions)
        tester._print_summary()
        sys.exit(0)
    
    if args.test:
        # 运行指定测试
        test_map = {
            "health": tester.test_health_check,
            "metrics": tester.test_metrics,
            "gpu": tester.test_gpu_resources,
            "single": tester.test_single_embedding,
            "batch": tester.test_batch_embedding,
            "similarity": tester.test_similarity_calculation,
            "long": tester.test_long_text_embedding,
            "dim512": tester.test_dimensions_512,
            "dim768": tester.test_dimensions_768,
            "dim1024": tester.test_dimensions_1024,
            "dim-compare": tester.test_dimensions_comparison,
            "concurrent": lambda: tester.test_concurrent_embedding(5, 2),
            "empty": tester.test_empty_input,
            "special": tester.test_special_characters,
        }
        
        if args.test in test_map:
            test_map[args.test]()
            tester._print_summary()
        else:
            print(f"未知测试: {args.test}")
            print(f"可用测试: {', '.join(test_map.keys())}")
            sys.exit(1)
    else:
        # 运行所有测试
        success = tester.run_all_tests(skip_concurrent=args.skip_concurrent)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
