import asyncio
import os
import sys
import argparse
import threading
import signal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import requests

# 添加当前目录到Python路径，确保能正确导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from infrastructure.common.logging.logging import logger,init_logging
from infrastructure.common.error.errcode import (
    ErrorCode, create_error, success, is_success,
    ErrorCode as EC
)

from infrastructure.persistences.mysql_persistence import MysqlPersistence # pyright: ignore[reportMissingImports, reportUndefinedVariable]
from infrastructure.persistences.elasticsearch_persistence import ElasticsearchPersistence
from infrastructure.config.sys_config import SysConfig
from interfaces.controller.ops_controller import OpsController
from interfaces.controller.rag_controller import RagController
from interfaces.controller.prompt_controller import PromptController
from interfaces.controller.memory_controller import MemoryController
from interfaces.controller.application_role_controller import ApplicationRoleController
from interfaces.controller.agent_controller import AgentController
from infrastructure.common.myfunc.myfile import MyFile
from infrastructure.client.redis_client import RedisTemplete
from domain.service.memory_service import MemoryService
from domain.service.rag_service import RagService
from infrastructure.client.neo4j_client import Neo4jClient


@logger()
class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key 认证中间件
    - 如果配置了 api_key 且不为空，则验证请求中的 API Key
    - 如果 api_key 为空或未配置，则不进行验证
    - 健康检查等运维接口不需要验证
    """

    # 不需要验证的路径前缀（健康检查 + 文档 + 聊天接口）
    EXCLUDE_PATHS = [
        "/ops/ping",
        "/ops/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/v1/agent/chat/ops/ping",
        "/v1/agent/chat/ops/health",
        "/v1/agent/chat/ops/metrics",
        "/v1/agent/chat/ops/version",
        "/v1/agent/chat/ops/process",
        "/v1/agent/chat/ops/system",
        "/v1/agent/chat/docs",
        "/v1/agent/chat/openapi.json",
        "/v1/agent/chat/redoc"
    ]

    def __init__(self, app, api_key: str = None):
        super().__init__(app)
        self.api_key = api_key if api_key and api_key.strip() else None

    async def dispatch(self, request: Request, call_next):
        # CORS 预检请求直接放行
        if request.method == "OPTIONS":
            return await call_next(request)

        # 如果没有配置 api_key，直接放行
        if not self.api_key:
            return await call_next(request)

        # 检查是否是排除的路径
        path = request.url.path
        for exclude_path in self.EXCLUDE_PATHS:
            if path.startswith(exclude_path):
                return await call_next(request)

        # 仅用于排查：打印请求携带的 header 名称（不打印值，避免泄露）
        try:
            header_names = sorted(list(request.headers.keys()))
            self.log.debug(
                "Request headers received - path: %s, header_names: %s, has_x_api_key: %s, has_authorization: %s",
                path,
                header_names,
                "X-API-Key" in request.headers,
                "Authorization" in request.headers,
            )
        except Exception:
            pass

        # 优先从 X-API-Key 读取；如果客户端使用了其它传递方式，做兼容
        request_api_key = request.headers.get("X-API-Key")
        api_key_source = "X-API-Key" if request_api_key else None

        if not request_api_key:
            request_api_key = request.headers.get("Api-Key")
            if request_api_key:
                api_key_source = "Api-Key"

        if not request_api_key:
            auth = request.headers.get("Authorization")
            if auth:
                parts = auth.split(" ", 1)
                if len(parts) == 2 and parts[0].lower() in ("bearer", "apikey"):
                    request_api_key = parts[1].strip()
                    api_key_source = "Authorization"

        if not request_api_key:
            request_api_key = request.query_params.get("api_key")
            if request_api_key:
                api_key_source = "query.api_key"

        # 调试日志（不打印 key 内容）
        self.log.debug(
            f"API Key validation - path: {path}, source: {api_key_source or 'missing'}, configured_key: {'present' if self.api_key else 'missing'}"
        )

        # 验证 API Key
        if request_api_key != self.api_key:
            self.log.warning(
                f"API Key validation failed - path: {path}, source: {api_key_source or 'missing'}"
            )
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
        # fastapi app
        self.fastapi_app = None

        #服务
        self.memory_service:MemoryService = None

        # llm controller
        self.llm_controller = None
        # ops controller
        self.ops_controller = None
        # rag controller
        self.rag_controller = None
        # devops runner
        self.devops_runner = None

    def __del__(self):
        """析构函数 - 作为最后的清理保障"""
        if not self._cleanup_done:
            pass

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

            # 停止 DevOps 心跳线程
            if self.devops_runner is not None:
                try:
                    self.devops_runner.stop_heartbeat()
                    self.log.info("DevOps heartbeat thread stopped")
                except Exception as e:
                    self.log.warning(f"Error stopping DevOps heartbeat: {e}")
            
            # 关闭 RedisTemplete
            if RedisTemplete.is_init:
                try:
                    RedisTemplete.deinit()
                    self.log.info("RedisTemplete deinit success")
                except Exception as e:
                    self.log.warning(f"Error shutting down RedisTemplete: {e}")

            self._cleanup_done = True
            self.log.info("系统资源清理完成")

        except Exception as e:
            self.log.error(f"资源清理过程中发生错误: {e}")

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

    def validate_config_file(self, config_path: str) -> tuple:
        """
        验证配置文件是否存在且可读

        Args:
            config_path: 配置文件路径

        Returns:
            tuple: (是否有效, 错误对象)
        """
        if not MyFile.is_file_exists(config_path):
            error = create_error(EC.CONFIG_NOT_FOUND, f"配置文件不存在: {config_path}")
            return False, error

        return True, success()

    def load_configuration(self, args):
        if args.config:
            config_path = args.config
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, 'resources', 'application.yaml')
        #如果是相对路径，补齐为绝对路径
        revalue,config_path = MyFile.safe_to_absolute(config_path)
        if revalue is False:
            return None, f"application file not exist,{config_path}"

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

    async def init_runner(self, config: SysConfig):
        """初始化 DevOps 运行器"""
        try:
            from interfaces.runner.devops_runner import DevOpsRunner
            self.devops_runner = DevOpsRunner(config)
            self.log.info("DevOps runner initialized")
            return ErrorCode.SUCCESS
        except Exception as e:
            import traceback
            self.log.error(f"Failed to initialize DevOps runner: {e}")
            self.log.error(traceback.format_exc())
            return ErrorCode.SYSTEM_ERROR

    async def init_component_client(self,config:SysConfig):
        """初始化所有组件客户端"""
        try:
            # 初始化MySQL客户端
            system_cfg = config.get_system_config() or {}
            mysql_config = system_cfg.get("persistence", {}).get("mysql", {})
            self.mysql_client = MysqlPersistence(
                host=mysql_config.get("host", "127.0.0.1"),
                port=mysql_config.get("port", 3306),
                username=mysql_config.get("username", "root"),
                password=mysql_config.get("password", ""),
                database=mysql_config.get("database", "pg-platform-db"),
                charset=mysql_config.get("charset", "utf8mb4"),
            )
            self.log.info("MySQL client initialized")
            
            # 初始化MinIO客户端
            system_cfg = config.get_system_config() or {}
            persistence_cfg = system_cfg.get("persistence", {}) or {}
            minio_cfg = persistence_cfg.get("minio", {}) or {}
            endpoint = minio_cfg.get("endpoint", "127.0.0.1:9000")
            access_key = minio_cfg.get("access_key", "admin")
            secret_key = minio_cfg.get("secret_key", "admin123")
            secure = bool(minio_cfg.get("secure", False))
            self.minio_bucket = minio_cfg.get("bucket", "rag-files")
            
            from minio import Minio
            self.minio_client = Minio(
                endpoint, access_key=access_key, secret_key=secret_key, secure=secure
            )
            
            # 确保MinIO桶存在
            try:
                if not self.minio_client.bucket_exists(self.minio_bucket):
                    self.minio_client.make_bucket(self.minio_bucket)
                    self.log.info(f"Created MinIO bucket: {self.minio_bucket}")
                else:
                    self.log.info(f"MinIO bucket exists: {self.minio_bucket}")
            except Exception as e:
                self.log.warning(f"MinIO bucket check failed: {e}")
            
            self.log.info("MinIO client initialized")
            
            # 初始化Redis客户端（用于 RAG 向量化进度，供前端轮询；使用 RedisTemplete，配置在 system.persistence.redis）
            redis_cfg = (persistence_cfg.get("redis") or system_cfg.get("redis")) or {}
            if not redis_cfg:
                self.log.info("Redis not configured (no system.persistence.redis), RAG progress via MySQL only")
            else:
                # RedisTemplete.init 需要 host, port, password, database
                pw = redis_cfg.get("password")
                pw_str = (pw if pw is not None else "").strip() if isinstance(pw, str) else (str(pw) if pw else "")
                rcfg = {
                    "host": redis_cfg.get("host", "127.0.0.1"),
                    "port": int(redis_cfg.get("port", 6379)),
                    "password": pw_str,
                    "database": int(redis_cfg.get("db", redis_cfg.get("database", 0))),
                }
                self.log.info(
                    "Redis config from system.persistence.redis: host=%s, port=%s, db=%s, password=%s, connecting..."
                    % (rcfg["host"], rcfg["port"], rcfg["database"], "configured" if rcfg["password"] else "empty")
                )
                if RedisTemplete.init(rcfg):
                    self.log.info("RedisTemplete initialized (RAG 向量化进度将写入 Redis)")
                else:
                    self.log.warning("RedisTemplete init failed (RAG 进度将仅通过 MySQL 更新)，请检查 Redis 是否启动及配置") # RAG 进度直接使用 RedisTemplete，不单独传 redis_client
                if not RedisTemplete.test():
                    self.log.warning("RedisTemplete test failed (RAG 进度将仅通过 MySQL 更新)，请检查 Redis 是否启动及配置")
                else:
                    self.log.info("RedisTemplete test passed (RAG 进度将写入 Redis)")
            # 初始化Qdrant客户端（如果配置了）
            qdrant_cfg = system_cfg.get("qdrant", {})
            if qdrant_cfg and qdrant_cfg.get("enabled", False):
                try:
                    from qdrant_client import QdrantClient
                    from qdrant_client.http.models import Distance, VectorParams
                    
                    self.qdrant_client = QdrantClient(
                        host=qdrant_cfg.get("host", "127.0.0.1"),
                        port=qdrant_cfg.get("port", 6333),
                        timeout=qdrant_cfg.get("timeout", 60)
                    )
                    
                    # 测试连接并创建集合（如果不存在）
                    collection_name = qdrant_cfg.get("collection_name", "rag_collection")
                    try:
                        collections = self.qdrant_client.get_collections().collections
                        collection_exists = any(c.name == collection_name for c in collections)
                        
                        if not collection_exists:
                            self.qdrant_client.create_collection(
                                collection_name=collection_name,
                                vectors_config=VectorParams(
                                    size=qdrant_cfg.get("vector_size", 512),
                                    distance=Distance.COSINE
                                )
                            )
                            self.log.info(f"Created Qdrant collection: {collection_name}")
                        else:
                            self.log.info(f"Qdrant collection exists: {collection_name}")
                    except Exception as e:
                        self.log.warning(f"Qdrant collection setup failed: {e}")
                    
                    self.log.info("Qdrant client initialized")
                except Exception as e:
                    self.log.warning(f"Qdrant client initialization failed: {e}")
                    self.qdrant_client = None
            else:
                self.qdrant_client = None
                self.log.info("Qdrant client disabled")
            #es
            es_cfg = (persistence_cfg.get("elasticsearch") or {})
            if es_cfg:
                try:
                    self.es_persistence = ElasticsearchPersistence(
                        host=es_cfg.get("host", "127.0.0.1"),
                        port=int(es_cfg.get("port", 9200)),
                        scheme=es_cfg.get("scheme", "http"),
                        username=es_cfg.get("username"),
                        password=es_cfg.get("password"),
                        index=es_cfg.get("index", "pg-agent-memory"),
                    )
                    self.log.info(
                        "Elasticsearch persistence initialized: host=%s, port=%s, index=%s",
                        self.es_persistence.host,
                        self.es_persistence.port,
                        self.es_persistence.index,
                    )
                except Exception as e:
                    self.es_persistence = None
                    self.log.warning("Elasticsearch persistence init failed: %s", e)
            else:
                self.es_persistence = None
                self.log.info("Elasticsearch persistence disabled")
            #初始化neo4j
            try:
                self.neo4j_client = Neo4jClient(config)
                self.log.info("Neo4j client initialized")
            except Exception as e:
                # 即使初始化失败也保留实例，以便后续重试
                self.neo4j_client = Neo4jClient(config)
                # 再次初始化肯定会失败（因为配置没变），但我们要的是实例引用
                # 实际上Neo4jClient.__init__内部已经捕获异常了，这里的try-catch是为了防止极端的初始化错误
                # 但如果Neo4jClient.__init__确实抛出异常，我们需要手动创建一个空壳或者确保rag_service能处理
                # 由于Neo4jClient内部捕获了异常，这里通常不会走到except
                self.log.warning("Neo4j client initialization threw exception: %s", e)
            
            return ErrorCode.SUCCESS
            
        except Exception as e:
            import traceback
            self.log.error(f"Component client initialization failed: {e}")
            self.log.error(traceback.format_exc())
            return ErrorCode.SYSTEM_ERROR


    async def init_fastapi_controller(self, config: SysConfig):
        try:
            self.fastapi_app = FastAPI(
                title="pg agent web service",
                version=config.get_system_config().get("version", "1.0.0")
            )
            self.fastapi_app.state.config = config
            self.log.info("fastapi app initialized")

            # 添加 API Key 认证中间件
            api_key = config.get_system_config().get("api_key", "")
            if api_key and api_key.strip():
                self.fastapi_app.add_middleware(ApiKeyAuthMiddleware, api_key=api_key)
                self.log.info("API Key authentication enabled")
            else:
                self.log.info("API Key authentication disabled (api_key not configured)")
            #初始化依赖
            self.memory_service = MemoryService(config, self.mysql_client, getattr(self, "es_persistence", None))
            self.rag_service = RagService(config, self.mysql_client, self.qdrant_client, self.minio_client, self.neo4j_client)

            # 初始化 controller
            self.ops_controller = OpsController(config, self.fastapi_app)
            self.rag_controller = RagController(
                config, self.fastapi_app, self.rag_service
            )
            
            self.memory_controller = MemoryController(
                config, self.fastapi_app, self.memory_service
            )
            self.prompt_controller = PromptController(
                config, self.fastapi_app, self.mysql_client
            )
            self.application_role_controller = ApplicationRoleController(
                config, self.fastapi_app, self.mysql_client
            )
            self.agent_controller = AgentController(
                config, self.fastapi_app,self.memory_service, self.rag_service
            )
            from interfaces.controller.tools_controller import ToolsController
            self.tools_controller = ToolsController(
                config, self.fastapi_app, self.mysql_client
            )

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
                timeout_keep_alive=120,  # 保持与网关的长连接，避免网关复用连接时被后端已关闭导致 Connection reset
            )
            server = uvicorn.Server(config)

            self.log.info(f"Uvicorn server configured with concurrency limit: {workers * 10}")

            # 运行服务器
            asyncio.run(server.serve())
        except Exception as e:
            self.log.error(f"Uvicorn server error: {e}")

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
        ping_url = f"http://{check_host}:{port}/v1/agent/chat/ops/ping"
        health_url = f"http://{check_host}:{port}/v1/agent/chat/ops/health"

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
            port = config.get_server_config().get("port", 19093)
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

    def register_to_nacos(self, config: SysConfig):
        """
        将当前服务注册到 Nacos
        """
        system_cfg = config.get_system_config() or {}
        nacos_cfg = system_cfg.get("nacos", {})

        if not nacos_cfg or not nacos_cfg.get("enabled", True):
            self.log.info("Nacos registration disabled or not configured")
            return

        server_addr = nacos_cfg.get("server_addr", "127.0.0.1:8848")
        namespace = nacos_cfg.get("namespace", "public")
        group = nacos_cfg.get("group", "DEFAULT_GROUP")
        service_name = nacos_cfg.get("service_name", system_cfg.get("name", "pg-agent-application"))
        weight = nacos_cfg.get("weight", 1.0)
        ephemeral = nacos_cfg.get("ephemeral", True)

        server_cfg = config.get_server_config() or {}
        ip = server_cfg.get("address", "127.0.0.1")
        port = server_cfg.get("port", 19093)
        # 如果是 0.0.0.0，注册时使用 127.0.0.1 或实际 IP
        if ip == "0.0.0.0":
            ip = "127.0.0.1"

        params = {
            "serviceName": service_name,
            "ip": ip,
            "port": port,
            "namespaceId": namespace,
            "groupName": group,
            "weight": weight,
            "healthy": "true",
            "enabled": "true",
            "ephemeral": "true" if ephemeral else "false",
        }

        url = f"http://{server_addr}/nacos/v1/ns/instance"
        try:
            resp = requests.post(url, params=params, timeout=5)
            if resp.status_code == 200:
                self.log.info(f"Registered to Nacos: {service_name} {ip}:{port} @ {server_addr}")
            else:
                self.log.error(f"Nacos register failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            self.log.error(f"Nacos register exception: {e}")

    async def running(self):
        """
        主运行流程
        """
        print("=" * 60)
        print("  pg agent Application Service")
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

        # 4. 初始化组件客户端
        result = await self.init_component_client(config)
        if result != ErrorCode.SUCCESS:
            self.log.error("Init component client failure")
            sys.exit(1)

        # 5. 初始化 FastAPI 控制器
        result = await self.init_fastapi_controller(config)
        if not is_success(result.error_code):
            self.log.error(f"Init FastAPI controller failure: {result.error_code} - {result.message}")
            print(f"程序运行出错: {result.error_code} - {result.message}")
            sys.exit(1)

        # 6. 初始化 DevOps 运行器
        result = await self.init_runner(config)
        if result != ErrorCode.SUCCESS:
            self.log.error("Init DevOps runner failure")
            sys.exit(1)

        # 6. 启动 FastAPI 服务器（异步线程 + 自检）
        result = await self.start_fastapi_server(config)
        if not is_success(result.error_code):
            self.log.error(f"Start FastAPI server failure: {result.message}")
            sys.exit(1)

        # 7. 将服务注册到 Nacos
        self.register_to_nacos(config)

        # 8. 启动心跳线程
        if self.devops_runner:
            self.devops_runner.start_heartbeat()
            self.log.info("DevOps heartbeat thread started")

        # 9. 打印启动信息
        server_config = config.get_server_config()
        host = server_config.get("address", "0.0.0.0")
        port = server_config.get("port", 18096)
        self.log.info("=" * 60)
        self.log.info("  Service started successfully!")
        self.log.info(f"  API Endpoint: http://{host}:{port}")
        self.log.info(f"  Health Check: http://{host}:{port}/ops/health")
        self.log.info(f"  API Docs: http://{host}:{port}/docs")
        self.log.info("=" * 60)

        # 10. 进入主循环
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
