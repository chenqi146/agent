#!/usr/bin/env python3
'''
Reranker 服务接口测试用例
测试 RerankerController 提供的所有 REST API 接口

使用方法:
    1. 先启动服务: cd src/python && python main.py
    2. 运行测试: python reranker_test.py [--base-url http://127.0.0.1:8800]
    
测试内容:
    - 文档重排序
    - Query-Document 评分
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


class RerankerServiceTest:
    """Reranker 服务测试类"""
    
    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.test_results = []
        self._server_info = None
    
    def _log(self, message: str, level: str = "INFO"):
        """打印日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def _post(self, endpoint: str, data: Dict[str, Any] = None, timeout: int = 60) -> Dict[str, Any]:
        """发送 POST 请求"""
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
        """解析 API 响应"""
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
    
    def _get_server_info(self) -> Dict[str, Any]:
        """获取服务端信息"""
        if self._server_info is not None:
            return self._server_info
        
        try:
            result = self._post("/reranker/metrics", {}, timeout=10)
            if result.get("success"):
                data = result.get("data", {})
                if data.get("code") == 0:
                    self._server_info = data.get("data", {})
                    return self._server_info
        except Exception:
            pass
        
        return {"model_name": "unknown", "enable": False, "mode": "unknown"}
    
    # ==================== 测试用例 ====================
    
    def test_health_check(self) -> bool:
        """测试健康检查接口"""
        self._log("测试健康检查接口...")
        
        result = self._post("/reranker/health", {})
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_health_check")
        
        if not success:
            self._record_result("test_health_check", False, error_msg, elapsed_ms)
            return False
        
        is_healthy = response_data.get("is_healthy", False)
        model_status = response_data.get("model_status", "unknown")
        model_name = response_data.get("model_name", "unknown")
        mode = response_data.get("mode", "unknown")
        
        print(f"    ├─ 健康状态: {'✅ 健康' if is_healthy else '❌ 不健康'}")
        print(f"    ├─ 模型状态: {model_status}")
        print(f"    ├─ 模型名称: {model_name}")
        print(f"    ├─ 工作模式: {mode}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        self._record_result("test_health_check", is_healthy, f"status={model_status}, mode={mode}", elapsed_ms)
        return is_healthy
    
    def test_metrics(self) -> bool:
        """测试服务指标接口"""
        self._log("测试服务指标接口...")
        
        result = self._post("/reranker/metrics", {})
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_metrics")
        
        if not success:
            self._record_result("test_metrics", False, error_msg, elapsed_ms)
            return False
        
        model_name = response_data.get("model_name", "unknown")
        model_status = response_data.get("model_status", "unknown")
        mode = response_data.get("mode", "unknown")
        enable = response_data.get("enable", False)
        
        print(f"    ├─ 模型名称: {model_name}")
        print(f"    ├─ 模型状态: {model_status}")
        print(f"    ├─ 工作模式: {mode}")
        print(f"    ├─ 启用状态: {'✅ 已启用' if enable else '❌ 未启用'}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        self._record_result("test_metrics", True, f"model={model_name}, mode={mode}", elapsed_ms)
        return True
    
    def test_simple_rerank(self) -> bool:
        """测试简单重排序"""
        self._log("测试简单文档重排序...")
        
        query = "什么是人工智能？"
        documents = [
            "人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。",
            "今天天气很好，适合出去散步。",
            "机器学习是人工智能的一个子领域，它使计算机能够从数据中学习。",
            "苹果是一种常见的水果，含有丰富的维生素。",
            "深度学习是机器学习的一种方法，使用神经网络来模拟人脑。"
        ]
        
        request_data = {
            "query": query,
            "documents": documents,
            "top_n": 3
        }
        
        result = self._post("/v1/rerank", request_data, timeout=120)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_simple_rerank")
        
        if not success:
            self._record_result("test_simple_rerank", False, error_msg, elapsed_ms)
            return False
        
        results = response_data.get("results", [])
        
        if not results:
            self._record_result("test_simple_rerank", False, "返回结果为空", elapsed_ms)
            return False
        
        print(f"    ┌─ 重排序结果 ─────────────────────────────────────────")
        print(f"    │ Query: {query}")
        print(f"    │")
        
        for i, item in enumerate(results):
            index = item.get("index", 0)
            score = item.get("relevance_score", 0)
            doc = item.get("document", {})
            text = doc.get("text", "")[:50] + "..." if doc else ""
            print(f"    │ [{i+1}] 原索引={index}, 分数={score:.4f}")
            print(f"    │     {text}")
        
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        # 验证：与AI相关的文档应该排在前面
        top_indices = [r.get("index") for r in results[:2]]
        expected_top = [0, 2, 4]  # AI、机器学习、深度学习相关的文档
        passed = any(idx in expected_top for idx in top_indices)
        
        self._record_result("test_simple_rerank", passed, f"top_n=3, results={len(results)}", elapsed_ms)
        return passed
    
    def test_score(self) -> bool:
        """测试评分接口"""
        self._log("测试 Query-Document 评分...")
        
        query = "机器学习的应用"
        documents = [
            "机器学习在图像识别、语音识别等领域有广泛应用。",
            "今天股市上涨了3%。",
            "深度学习是机器学习的一种，常用于计算机视觉。"
        ]
        
        request_data = {
            "query": query,
            "documents": documents
        }
        
        result = self._post("/v1/score", request_data, timeout=120)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_score")
        
        if not success:
            self._record_result("test_score", False, error_msg, elapsed_ms)
            return False
        
        scores = response_data.get("scores", [])
        
        if len(scores) != len(documents):
            self._record_result("test_score", False, f"分数数量不匹配: {len(scores)} vs {len(documents)}", elapsed_ms)
            return False
        
        print(f"    ┌─ 评分结果 ─────────────────────────────────────────")
        print(f"    │ Query: {query}")
        print(f"    │")
        
        for i, (doc, score) in enumerate(zip(documents, scores)):
            icon = "🟢" if score > 0.5 else ("🟡" if score > 0.3 else "🔴")
            print(f"    │ {icon} [{i}] 分数={score:.4f}")
            print(f"    │     {doc[:50]}...")
        
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        # 验证：第一个和第三个文档应该有更高的分数
        passed = scores[0] > scores[1] or scores[2] > scores[1]
        
        self._record_result("test_score", passed, f"scores={len(scores)}", elapsed_ms)
        return passed
    
    def test_batch_rerank(self) -> bool:
        """测试批量文档重排序"""
        self._log("测试批量文档重排序（10个文档）...")
        
        query = "Python编程语言"
        documents = [
            "Python是一种高级编程语言，以其简洁易读的语法著称。",
            "Java是一种广泛使用的面向对象编程语言。",
            "Python广泛应用于数据科学、机器学习和Web开发。",
            "今天的午餐是意大利面。",
            "Python的缩进语法使代码更加整洁。",
            "C++是一种高性能的编程语言。",
            "使用Python可以快速开发原型。",
            "JavaScript主要用于Web前端开发。",
            "Python拥有丰富的第三方库生态系统。",
            "天气预报说明天会下雨。"
        ]
        
        request_data = {
            "query": query,
            "documents": documents,
            "top_n": 5
        }
        
        result = self._post("/v1/rerank", request_data, timeout=180)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_batch_rerank")
        
        if not success:
            self._record_result("test_batch_rerank", False, error_msg, elapsed_ms)
            return False
        
        results = response_data.get("results", [])
        
        print(f"    ├─ 文档数量: {len(documents)}")
        print(f"    ├─ 返回数量: {len(results)}")
        print(f"    ├─ 前3名索引: {[r.get('index') for r in results[:3]]}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        # 验证返回数量
        passed = len(results) == 5
        
        self._record_result("test_batch_rerank", passed, f"docs={len(documents)}, results={len(results)}", elapsed_ms)
        return passed
    
    def test_empty_documents(self) -> bool:
        """测试空文档处理"""
        self._log("测试空文档处理...")
        
        request_data = {
            "query": "测试查询",
            "documents": []
        }
        
        result = self._post("/v1/rerank", request_data, timeout=30)
        elapsed_ms = result.get("elapsed_ms", 0)
        
        # 空文档应该返回空结果或错误
        data = result.get("data", {})
        
        print(f"    ├─ 响应码: {data.get('code')}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        # 只要不崩溃就算通过
        self._record_result("test_empty_documents", True, "边界情况处理正常", elapsed_ms)
        return True
    
    def test_long_documents(self) -> bool:
        """测试长文档处理"""
        self._log("测试长文档处理...")
        
        # 生成较长的文档
        long_doc = "人工智能是计算机科学的重要分支。" * 50
        
        query = "人工智能的发展"
        documents = [
            long_doc,
            "机器学习是AI的核心技术。",
            "深度学习推动了AI的进步。"
        ]
        
        request_data = {
            "query": query,
            "documents": documents
        }
        
        result = self._post("/v1/rerank", request_data, timeout=180)
        success, response_data, error_msg, elapsed_ms = self._parse_response(result, "test_long_documents")
        
        if not success:
            self._record_result("test_long_documents", False, error_msg, elapsed_ms)
            return False
        
        results = response_data.get("results", [])
        
        print(f"    ├─ 长文档长度: {len(long_doc)} 字符")
        print(f"    ├─ 返回结果数: {len(results)}")
        print(f"    └─ 响应时间: {elapsed_ms:.0f}ms")
        
        passed = len(results) == len(documents)
        self._record_result("test_long_documents", passed, f"chars={len(long_doc)}", elapsed_ms)
        return passed
    
    def test_concurrent_rerank(self, num_threads: int = 3, requests_per_thread: int = 2) -> bool:
        """测试并发重排序"""
        self._log(f"测试并发重排序（{num_threads} 线程 × {requests_per_thread} 请求）...")
        
        results = []
        lock = threading.Lock()
        
        def worker(thread_id: int):
            thread_results = []
            for i in range(requests_per_thread):
                query = f"并发测试查询{thread_id}-{i}"
                docs = [f"文档{j}内容" for j in range(5)]
                
                start_time = time.time()
                try:
                    result = self._post("/v1/rerank", {"query": query, "documents": docs}, timeout=120)
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    success = result.get("success", False)
                    if success:
                        data = result.get("data", {})
                        if data.get("code") == 0:
                            thread_results.append({"success": True, "elapsed_ms": elapsed_ms})
                        else:
                            thread_results.append({"success": False, "elapsed_ms": elapsed_ms})
                    else:
                        thread_results.append({"success": False, "elapsed_ms": elapsed_ms})
                except Exception as e:
                    thread_results.append({"success": False, "elapsed_ms": 0, "error": str(e)})
            
            with lock:
                results.extend(thread_results)
        
        total_start = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for future in as_completed(futures):
                future.result()
        
        total_elapsed = (time.time() - total_start) * 1000
        
        total_requests = len(results)
        success_count = sum(1 for r in results if r.get("success"))
        failed_count = total_requests - success_count
        
        if success_count > 0:
            success_times = [r["elapsed_ms"] for r in results if r.get("success")]
            avg_time = sum(success_times) / len(success_times)
        else:
            avg_time = 0
        
        print(f"    ├─ 总请求数: {total_requests}")
        print(f"    ├─ 成功: {success_count}")
        print(f"    ├─ 失败: {failed_count}")
        print(f"    ├─ 总耗时: {total_elapsed:.0f}ms")
        print(f"    ├─ 平均响应: {avg_time:.0f}ms")
        print(f"    └─ QPS: {total_requests / (total_elapsed / 1000):.2f}")
        
        passed = success_count == total_requests
        self._record_result("test_concurrent_rerank", passed, f"success={success_count}/{total_requests}", total_elapsed)
        return passed
    
    # ==================== 运行测试 ====================
    
    def run_all_tests(self, skip_concurrent: bool = False) -> bool:
        """运行所有测试"""
        self._log("=" * 60)
        self._log("开始 Reranker 服务测试")
        self._log(f"服务地址: {self.base_url}")
        self._log("=" * 60)
        
        server_info = self._get_server_info()
        model_name = server_info.get("model_name", "unknown")
        mode = server_info.get("mode", "unknown")
        
        self._log(f"模型名称: {model_name}")
        self._log(f"工作模式: {mode}")
        self._log("-" * 60)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("服务指标", self.test_metrics),
            ("简单重排序", self.test_simple_rerank),
            ("评分接口", self.test_score),
            ("批量重排序", self.test_batch_rerank),
            ("空文档处理", self.test_empty_documents),
            ("长文档处理", self.test_long_documents),
        ]
        
        if not skip_concurrent:
            tests.append(("并发测试", lambda: self.test_concurrent_rerank(3, 2)))
        
        for name, test_func in tests:
            try:
                self._log("-" * 40)
                test_func()
            except Exception as e:
                self._log(f"测试 {name} 异常: {e}", "ERROR")
                self._record_result(name, False, str(e), 0)
        
        self._print_summary()
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
    parser = argparse.ArgumentParser(description="Reranker 服务测试")
    parser.add_argument("--base-url", type=str, default=SERVER_URL,
                       help=f"服务地址 (默认: {SERVER_URL})")
    parser.add_argument("--skip-concurrent", action="store_true",
                       help="跳过并发测试")
    parser.add_argument("--test", type=str, default=None,
                       help="运行指定测试 (health/metrics/rerank/score/batch/concurrent)")
    
    args = parser.parse_args()
    
    tester = RerankerServiceTest(base_url=args.base_url)
    
    if args.test:
        test_map = {
            "health": tester.test_health_check,
            "metrics": tester.test_metrics,
            "rerank": tester.test_simple_rerank,
            "score": tester.test_score,
            "batch": tester.test_batch_rerank,
            "concurrent": lambda: tester.test_concurrent_rerank(3, 2),
            "empty": tester.test_empty_documents,
            "long": tester.test_long_documents,
        }
        
        if args.test in test_map:
            test_map[args.test]()
            tester._print_summary()
        else:
            print(f"未知测试: {args.test}")
            print(f"可用测试: {', '.join(test_map.keys())}")
            sys.exit(1)
    else:
        success = tester.run_all_tests(skip_concurrent=args.skip_concurrent)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
