import asyncio
import os
import sys
import argparse
import signal
import threading
import uvicorn
import requests

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from infrastructure.common.logging.logging import logger, init_logging
from infrastructure.common.error.errcode import (
    ErrorCode, create_error, success, is_success, ErrorCode as EC
)
from infrastructure.persistences.mysql_persistence import MysqlPersistence
from infrastructure.persistences.qdrant_persistence import QDrantPersistence
from infrastructure.client.embedding_client import EmbeddingClient
from infrastructure.config.sys_config import SysConfig
from infrastructure.common.myfunc.myfile import MyFile

from interfaces.controller.mcp_tool_controller import McpToolController
from domain.service.mcp_tool_service import McpToolService
from infrastructure.repositories.mcp_tool_repository import McpToolRepository
from interfaces.deps.user_context import UserContext # ensure deps is created

@logger()
class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    EXCLUDE_PATHS = [
        "/ops/ping",
        "/ops/health",
        "/docs",
        "/redoc",
        "/openapi.json"
    ]

    def __init__(self, app, api_key: str = None):
        super().__init__(app)
        self.api_key = api_key if api_key and api_key.strip() else None

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        if not self.api_key:
            return await call_next(request)

        path = request.url.path
        for exclude_path in self.EXCLUDE_PATHS:
            if path.startswith(exclude_path):
                return await call_next(request)

        request_api_key = request.headers.get("X-API-Key")
        if not request_api_key:
            auth = request.headers.get("Authorization")
            if auth:
                parts = auth.split(" ", 1)
                if len(parts) == 2 and parts[0].lower() in ("bearer", "apikey"):
                    request_api_key = parts[1].strip()

        if not request_api_key:
            request_api_key = request.query_params.get("api_key")

        if request_api_key != self.api_key:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "Invalid or missing API Key"}
            )

        return await call_next(request)

@logger()
class Main:
    def __init__(self):
        self._cleanup_done = False
        self._shutdown_requested = False
        self._setup_signal_handlers()
        self.fastapi_app = None
        self.mysql_client = None
        self.qdrant_client = None
        self.embedding_client = None

    def _setup_signal_handlers(self):
        def signal_handler(signum, frame):
            if self._shutdown_requested:
                sys.exit(1)
            self._shutdown_requested = True
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def parse_arguments(self):
        parser = argparse.ArgumentParser(description='MCP Service')
        parser.add_argument('-c', '--config', type=str, default=None, help='Config file path')
        return parser.parse_args()

    def load_configuration(self, args):
        if args.config:
            config_path = args.config
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, 'resources', 'application.yaml')
        
        revalue, config_path = MyFile.safe_to_absolute(config_path)
        if revalue is False:
            return None, f"Config file not exist: {config_path}"

        try:
            config = SysConfig(config_path)
            return config, success()
        except Exception as e:
            return None, create_error(EC.CONFIG_PARSE_ERROR, str(e))

    async def init_components(self, config: SysConfig):
        try:
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
            # Connect to verify
            if self.mysql_client.connect() != ErrorCode.SUCCESS:
                self.log.error("Failed to connect to MySQL")
                return ErrorCode.DATABASE_CONNECTION_ERROR
            
            self.log.info("MySQL initialized")
            
            # Qdrant
            persistence_cfg = system_cfg.get("persistence", {})
            qdrant_cfg = persistence_cfg.get("qdrant", {})
            
            qdrant_url = qdrant_cfg.get("url")
            if not qdrant_url and qdrant_cfg.get("host"):
                qdrant_url = f"http://{qdrant_cfg.get('host')}:{qdrant_cfg.get('port', 6333)}"
            
            self.qdrant_client = QDrantPersistence(
                url=qdrant_url or "http://localhost:6333",
                api_key=qdrant_cfg.get("api_key"),
                timeout=qdrant_cfg.get("timeout", 10.0),
                vector_size=qdrant_cfg.get("vector_dim", 512)
            )
            
            # Embedding
            embedding_base_url = config.get_vllm_embedding_base_url()
            embedding_api_key = config.get_vllm_embedding_api_key()
            self.embedding_client = EmbeddingClient(
                base_url=embedding_base_url,
                api_key=embedding_api_key
            )
            
            return ErrorCode.SUCCESS
        except Exception as e:
            self.log.error(f"Component init failed: {e}")
            return ErrorCode.SYSTEM_ERROR

    async def init_fastapi(self, config: SysConfig):
        self.fastapi_app = FastAPI(title="MCP Service", version="1.0.0")
        
        api_key = config.get_system_config().get("api_key", "")
        if api_key:
            self.fastapi_app.add_middleware(ApiKeyAuthMiddleware, api_key=api_key)

        # Initialize Repository, Service, Controller
        repo = McpToolRepository(self.mysql_client)
        service = McpToolService(repo, self.embedding_client, self.qdrant_client)
        controller = McpToolController(service)
        
        # Include Router
        self.fastapi_app.include_router(controller.router)
        
        # Health checks
        @self.fastapi_app.get("/ops/ping")
        def ping():
            return {"code": 0, "message": "pong"}

        return success()

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
        port = server_cfg.get("port", 19095)
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

    def run(self):
        """
        主运行流程
        """
        print("=" * 60)
        print("  pg agent MCP Service")
        print("=" * 60)
        args = self.parse_arguments()
        config, err = self.load_configuration(args)
        if not is_success(err):
            print(f"Failed to load config: {err}")
            return

        #注册到nacos
        self.register_to_nacos(config)
        self.log.info("register nacos complete")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.log.info("start init components")
        
        err = loop.run_until_complete(self.init_components(config))
        if err != ErrorCode.SUCCESS:
            print("Failed to init components")
            return
        self.log.info("init components complete")

        err = loop.run_until_complete(self.init_fastapi(config))
        if not is_success(err):
            print("Failed to init FastAPI")
            return
        self.log.info("init fastapi complete")

        server_cfg = config.get_server_config()
        host = server_cfg.get("host", "0.0.0.0")
        port = server_cfg.get("port", 19095) # Default to 8000, but likely different for mcp-service

        uvicorn.run(self.fastapi_app, host=host, port=port)

if __name__ == "__main__":
    main = Main()
    main.run()
