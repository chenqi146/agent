'''
@File    :   main.py
@Time    :   2025/08/31 17:23:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   主函数
'''
import asyncio
import os
import sys
import argparse
from pathlib import Path
import threading
import time
import signal
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import requests
from datetime import datetime

from interfaces.controller.llm_controller import LLMController
from interfaces.controller.vlm_controller import VLMController
from interfaces.controller.embedding_controller import EmbeddingController
from interfaces.controller.reranker_controller import RerankerController
from interfaces.controller.ops_controller import OpsController


# 添加当前目录到Python路径，确保能正确导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from infrastructure.common.logging.logging import logger,init_logging
from infrastructure.common.error.errcode import (
    ErrorCode, create_error, success, is_success,
    ErrorCode as EC
)
from infrastructure.common.path.path_utils import PathUtils

from infrastructure.persistences.mysql_persistence import MysqlPersistence # pyright: ignore[reportMissingImports, reportUndefinedVariable]
from infrastructure.config.sys_config import SysConfig


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key 认证中间件
    - 如果配置了 api_key 且不为空，则验证请求中的 API Key
    - 如果 api_key 为空或未配置，则不进行验证
    - 健康检查等运维接口不需要验证
    """
    
    # 不需要验证的路径前缀
    EXCLUDE_PATHS = [
        "/ops/",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]
    
    def __init__(self, app, api_key: str = None):
        super().__init__(app)
        self.api_key = api_key if api_key and api_key.strip() else None
    
    async def dispatch(self, request: Request, call_next):
        # 如果没有配置 api_key，直接放行
        if not self.api_key:
            return await call_next(request)
        
        # 检查是否是排除的路径
        path = request.url.path
        for exclude_path in self.EXCLUDE_PATHS:
            if path.startswith(exclude_path):
                return await call_next(request)
        
        # 获取请求中的 API Key
        request_api_key = None
        
        # 方式1: Authorization: Bearer <api_key>
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            request_api_key = auth_header[7:]  # 去掉 "Bearer " 前缀
        
        # 方式2: X-API-Key 头
        if not request_api_key:
            request_api_key = request.headers.get("X-API-Key")
        
        # 验证 API Key
        if request_api_key != self.api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "code": 401,
                    "message": "Invalid or missing API Key",
                    "data": None
                }
            )
        
        return await call_next(request)


@logger()
class Main:
    def __init__(self):
        # 资源清理标志
        self._cleanup_done = False
        self._shutdown_requested = False
        self._setup_signal_handlers()

        #fastapi app
        self.fastapi_app = None

        #llm controller
        self.llm_controller = None
        
        #vlm controller
        self.vlm_controller = None
        
        #embedding controller
        self.embedding_controller = None
        
        #reranker controller
        self.reranker_controller = None
        
        #ops controller
        self.ops_controller = None
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            if self._shutdown_requested:
                self.log.warn("已经收到过退出信号，强制退出...")
                sys.exit(1)
            
            self.log.info(f"接收到信号 {signum}，请求程序退出...")
            self._shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def cleanup(self):
        """清理所有资源"""
        if self._cleanup_done:
            return
        
        self.log.info("开始清理系统资源...")
        
        try:
            # 关闭 LLM 服务，释放 GPU 资源
            if self.llm_controller is not None:
                try:
                    self.llm_controller.llm_service.shutdown()
                    self.log.info("LLM service shutdown complete")
                except Exception as e:
                    self.log.warning(f"Error shutting down LLM service: {e}")
            
            # 关闭 VLM 服务，释放 GPU 资源
            if self.vlm_controller is not None:
                try:
                    self.vlm_controller.shutdown()
                    self.log.info("VLM service shutdown complete")
                except Exception as e:
                    self.log.warning(f"Error shutting down VLM service: {e}")
            
            # 关闭 Embedding 服务，释放 GPU 资源
            if self.embedding_controller is not None:
                try:
                    self.embedding_controller.embedding_service.unload_model()
                    self.log.info("Embedding service shutdown complete")
                except Exception as e:
                    self.log.warning(f"Error shutting down Embedding service: {e}")
            
            # 关闭 Reranker 服务，释放 GPU 资源
            if self.reranker_controller is not None:
                try:
                    self.reranker_controller.reranker_service.unload_model()
                    self.log.info("Reranker service shutdown complete")
                except Exception as e:
                    self.log.warning(f"Error shutting down Reranker service: {e}")
            
            self._cleanup_done = True
            self.log.info("系统资源清理完成")
            
        except Exception as e:
            self.log.error(f"资源清理过程中发生错误: {e}")
    
    def __del__(self):
        """析构函数 - 作为最后的清理保障"""
        if not self._cleanup_done:
            pass

    def parse_arguments(self):
        """
        解析命令行参数

        Returns:
            argparse.Namespace: 解析后的参数对象
        """
        parser = argparse.ArgumentParser(
            description='Parking Space Management System',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
    示例用法:
      python main.py                                    # 使用默认配置文件
      python main.py -c /path/to/application.yaml      # 指定配置文件路径
      python main.py --config /path/to/application.yaml # 指定配置文件路径
      python main.py -h                                 # 显示帮助信息
            """
        )
        parser.add_argument(
            '-c', '--config',
            type=str,
            default=None,
            help='配置文件路径 (默认: resources/application.yaml)'
        )
        parser.add_argument(
            '--version',
            action='version',
            version='agent v1.0.0'
        )

        return parser.parse_args()
    def validate_config_file(self,config_path: str) -> tuple:
        """
        验证配置文件是否存在且可读

        Args:
            config_path: 配置文件路径

        Returns:
            tuple: (是否有效, 错误对象)
        """
        if not os.path.exists(config_path):
            error = create_error(EC.CONFIG_NOT_FOUND, f"配置文件不存在: {config_path}")
            return False, error

        if not os.path.isfile(config_path):
            error = create_error(EC.CONFIG_INVALID, f"配置文件路径不是文件: {config_path}")
            return False, error

        if not os.access(config_path, os.R_OK):
            error = create_error(EC.PERMISSION_DENIED, f"配置文件无法读取: {config_path}")
            return False, error

        return True, success()
    
    def load_configuration(self,args):
        if args.config:
            config_path = args.config
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, 'resources', 'application.yaml')
        # 验证配置文件
        print(f"load config file: {config_path}")
        is_valid, error = self.validate_config_file(config_path)
        if not is_valid:
            return None, error
        print("configure file is valid")
        try:
            # 加载配置
            config = SysConfig(config_path)
            print(f"load config success, file: {config_path}")
            
            return config, success()
        except Exception as e:
            error = create_error(EC.CONFIG_PARSE_ERROR, f"配置文件加载失败: {e}")
            return None, error

    async def command_line_runner(self,config:SysConfig):
        self.log.info("|--------------------------------command line runner--------------------------------|")
       
        self.log.info("|--------------------------------command line runner end----------------------------|")
        return success()
    
    async def init_fastapi_controller(self,config:SysConfig):
        try:
            self.fastapi_app = FastAPI(
                title="qjzh vllm web service",
                version=config.get_system_config().get("version", "1.0.0")
            )
            self.log.info("fastapi app initialized")
            
            # 添加 API Key 认证中间件
            api_key = config.get_system_config().get("api_key", "")
            if api_key and api_key.strip():
                self.fastapi_app.add_middleware(ApiKeyAuthMiddleware, api_key=api_key)
                self.log.info("API Key authentication enabled")
            else:
                self.log.info("API Key authentication disabled (api_key not configured)")
            
            # 初始化 Ops 控制器（系统运维接口）
            self.ops_controller = OpsController(config, self.fastapi_app)
            self.log.info("ops controller initialized")
            
            # 初始化 LLM 控制器（文本模型推理接口）
            #self.llm_controller = LLMController(config, self.fastapi_app)
            self.log.info("llm controller initialized")
            
            # 初始化 VLM 控制器（视觉语言模型推理接口）
            self.vlm_controller = VLMController(config, self.fastapi_app)
            self.log.info("vlm controller initialized")
            
            # 初始化 Embedding 控制器（文本向量化接口）
            self.embedding_controller = EmbeddingController(config, self.fastapi_app)
            self.log.info("embedding controller initialized")
            
            # 初始化 Reranker 控制器（文档重排序接口）
            self.reranker_controller = RerankerController(config, self.fastapi_app)
            self.log.info("reranker controller initialized")
            
            return success()
        except Exception as e:
            import traceback
            self.log.error(f"启动fastapi controller失败: {e}")
            self.log.error(traceback.format_exc())
            return create_error(EC.SYSTEM_ERROR, f"启动fastapi controller失败: {e}")
    
    def _run_uvicorn_server(self, host: str, port: int, workers: int = 1):
        """
        在独立线程中运行 uvicorn 服务器
        
        Args:
            host: 监听地址
            port: 监听端口
            workers: 工作线程数（注意：在线程中启动时，workers 作为并发限制参考）
        """
        try:
            # 创建 uvicorn 配置
            config = uvicorn.Config(
                self.fastapi_app,
                host=host,
                port=port,
                log_level="warning",
                # 注意: workers 参数在嵌入式运行时不生效
                # 但可以通过 limit_concurrency 控制并发
                limit_concurrency=workers * 10,  # 并发连接限制
                limit_max_requests=workers * 1000,  # 最大请求数限制
            )
            server = uvicorn.Server(config)
            
            self.log.info(f"Uvicorn server configured with concurrency limit: {workers * 10}")
            
            # 运行服务器
            asyncio.run(server.serve())
        except Exception as e:
            self.log.error(f"Uvicorn server error: {e}")
    
    async def start_fastapi_server(self, config: SysConfig):
        """
        启动 FastAPI 服务器（异步线程启动 + 自检）
        
        Args:
            config: 系统配置
            
        Returns:
            SystemError: 启动结果
        """
        try:
            host = config.get_server_config().get("address", "0.0.0.0")
            port = config.get_server_config().get("port", 18096)
            workers = config.get_server_config().get("workers", 10)
            
            self.log.info(f"Starting FastAPI server on {host}:{port} with workers={workers}...")
            
            # 在独立线程中启动 uvicorn
            self._server_thread = threading.Thread(
                target=self._run_uvicorn_server,
                args=(host, port, workers),
                daemon=True,
                name="uvicorn-server"
            )
            self._server_thread.start()
            
            # 等待服务器启动并进行自检
            self.log.info("Waiting for server to start and performing health check...")
            health_check_result = await self._perform_startup_health_check(host, port)
            
            if not health_check_result:
                return create_error(EC.WEB_SERVER_START_FAILED, "服务启动自检失败")
            
            self.log.info(f"FastAPI server started successfully on http://{host}:{port}")
            return success()
            
        except Exception as e:
            self.log.error(f"Failed to start FastAPI server: {e}")
            return create_error(EC.WEB_SERVER_START_FAILED, f"启动FastAPI服务器失败: {e}")
    
    async def _perform_startup_health_check(
        self, 
        host: str, 
        port: int, 
        max_retries: int = 30, 
        retry_interval: float = 1.0
    ) -> bool:
        """
        执行启动自检 - 通过调用 /ops/ping 接口检测服务是否正常
        
        Args:
            host: 服务器地址
            port: 服务器端口
            max_retries: 最大重试次数
            retry_interval: 重试间隔（秒）
            
        Returns:
            bool: 自检是否通过
        """
        # 如果是 0.0.0.0，使用 127.0.0.1 进行本地检测
        check_host = "127.0.0.1" if host == "0.0.0.0" else host
        ping_url = f"http://{check_host}:{port}/ops/ping"
        health_url = f"http://{check_host}:{port}/ops/health"
        
        for attempt in range(1, max_retries + 1):
            try:
                # 首先尝试 ping
                response = requests.post(
                    ping_url,
                    json={},
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        self.log.info(f"Ping check passed (attempt {attempt}/{max_retries})")
                        
                        # ping 成功后，进行完整健康检查
                        health_response = requests.post(
                            health_url,
                            json={},
                            timeout=10
                        )
                        
                        if health_response.status_code == 200:
                            health_result = health_response.json()
                            if health_result.get("code") == 0:
                                health_data = health_result.get("data", {})
                                self.log.info(f"Health check passed: {health_data.get('status', 'unknown')}")
                                return True
                            else:
                                self.log.warning(f"Health check returned error: {health_result.get('message')}")
                        
                        # 即使健康检查有警告，ping 成功也算启动成功
                        return True
                    else:
                        self.log.warning(f"Ping returned error code: {result.get('code')}")
                else:
                    self.log.debug(f"Ping returned status {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                self.log.debug(f"Server not ready yet (attempt {attempt}/{max_retries})")
            except requests.exceptions.Timeout:
                self.log.warning(f"Health check timeout (attempt {attempt}/{max_retries})")
            except Exception as e:
                self.log.warning(f"Health check error (attempt {attempt}/{max_retries}): {e}")
            
            # 等待后重试
            if attempt < max_retries:
                await asyncio.sleep(retry_interval)
        
        self.log.error(f"Health check failed after {max_retries} attempts")
        return False


    async def loop(self):
        """
        主循环 - 保持程序运行直到收到退出信号
        """
        self.log.info("Entering main loop, press Ctrl+C to exit...")
        
        try:
            while not self._shutdown_requested:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.log.info("Main loop cancelled")
        
        self.log.info("Main loop exited")
    
    async def running(self):
        """
        主运行流程
        """
        print("=" * 60)
        print("  QJZH vLLM Application Service")
        print("=" * 60)
        
        # 1. 解析命令行参数
        args = self.parse_arguments()
        
        # 2. 加载配置
        config, config_error = self.load_configuration(args)
        if not is_success(config_error.error_code):
            print(f"Load config failure: {config_error.message}")
            sys.exit(1)
        
        # 保存配置引用
        self._config = config
        
        # 3. 初始化日志
        log_config = config.get_log_config()
        init_logging(log_config)
        self.log.info("Logging initialized")
        
        # 4. 启动命令行运行器
        result = await self.command_line_runner(config)
        if not is_success(result.error_code):
            self.log.error(f"Command line runner failure: {result.message}")
            sys.exit(1)
        
        # 5. 初始化 FastAPI 控制器
        result = await self.init_fastapi_controller(config)
        if not is_success(result.error_code):
            self.log.error(f"Init FastAPI controller failure: {result.error_code} - {result.message}")
            print(f"程序运行出错: {result.error_code} - {result.message}")
            sys.exit(1)
        
        # 6. 启动 FastAPI 服务器（异步线程 + 自检）
        result = await self.start_fastapi_server(config)
        if not is_success(result.error_code):
            self.log.error(f"Start FastAPI server failure: {result.message}")
            sys.exit(1)
        
        # 7. 打印启动信息
        server_config = config.get_server_config()
        host = server_config.get("address", "0.0.0.0")
        port = server_config.get("port", 18096)
        self.log.info("=" * 60)
        self.log.info("  Service started successfully!")
        self.log.info(f"  API Endpoint: http://{host}:{port}")
        self.log.info(f"  Health Check: http://{host}:{port}/ops/health")
        self.log.info(f"  LLM API: http://{host}:{port}/v1/chat/completions")
        self.log.info(f"  VLM API: http://{host}:{port}/v1/vision/completions")
        self.log.info(f"  Embedding API: http://{host}:{port}/v1/embeddings")
        self.log.info(f"  Reranker API: http://{host}:{port}/v1/rerank")
        self.log.info(f"  API Docs: http://{host}:{port}/docs")
        self.log.info("=" * 60)
        
        # 8. 进入主循环
        await self.loop()

if __name__ == "__main__":
    main = Main()
    try:
        asyncio.run(main.running())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        # 确保清理资源
        try:
            asyncio.run(main.cleanup())
        except Exception as cleanup_error:
            print(f"清理资源时发生错误: {cleanup_error}")
        sys.exit(0)
    except Exception as e:
        print(f"程序运行出错: {e}")
        # 确保清理资源
        try:
            asyncio.run(main.cleanup())
        except Exception as cleanup_error:
            print(f"清理资源时发生错误: {cleanup_error}")
        sys.exit(1)