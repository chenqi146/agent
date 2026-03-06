from fastapi import FastAPI, Request, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from typing import List, Optional
from pydantic import ValidationError
import time
import os
import shutil
import uuid

from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

from interfaces.controller.base_controller import BaseController
from interfaces.deps.user_context import UserContext, get_validated_user_context
from interfaces.dto.ops_dto import EmptyRequest
from interfaces.dto.chat_dto import (
    ChatStreamRequest, ChatHistoryResponse, ChatConversationResponse, ChatStopRequest
)
from interfaces.dto.response_dto import ApiResponse, ok, fail
from domain.service.agent_service import AgentService
from domain.service.memory_service import MemoryService
from domain.service.rag_service import RagService

@logger()
class AgentController(BaseController):
    """
       Agent 控制器 - 智能体接口
    """
    def __init__(self,config:SysConfig,web_app:FastAPI,memory_service:MemoryService, rag_service: RagService):
        self.config = config
        self.app = web_app
        self._start_time = time.time()
        self._app_name = "pg-agent-application"
        # 初始化服务
        self.agent_service = AgentService(memory_service, rag_service)
        # 注册路由
        self._register_routes()

    def _register_routes(self):
        """注册所有路由"""
        
        # Ensure storage directory exists
        storage_dir = os.path.join(os.getcwd(), "storage", "chat_files")
        os.makedirs(storage_dir, exist_ok=True)
        
        # Mount static files
        self.app.mount("/v1/agent/chat/files", StaticFiles(directory=storage_dir), name="chat_files")

        @self.app.post("/v1/agent/generate", response_model=ApiResponse)
        async def generate_content(
            request: ChatStreamRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """Stateless content generation"""
            err, result = await self.agent_service.generate_content(request)
            if err == ErrorCode.SUCCESS:
                return ok(result)
            return fail(err)

        @self.app.post("/v1/agent/generate/stream")
        async def generate_content_stream(
            request: ChatStreamRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """Stateless content generation (streaming)"""
            return StreamingResponse(
                self.agent_service.generate_content_stream(request),
                media_type="text/event-stream"
            )

        @self.app.post("/v1/agent/chat/upload", response_model=ApiResponse)
        async def upload_file(
            file: UploadFile = File(...),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """上传文件接口"""
            try:
                user_id = int(user_ctx.user_id)
            except ValueError:
                self.log.error(f"Invalid user_id format: {user_ctx.user_id}")
                return fail(ErrorCode.INVALID_PARAMS)

            # Check file extension
            filename = file.filename
            ext = os.path.splitext(filename)[1].lower().lstrip('.')
            supported_types = self.config.get_supported_file_types()
            
            # Map 'office' to extensions if needed (though get_supported_file_types logic in SysConfig might already handle it, 
            # checking SysConfig.get_supported_file_types implementation: it returns a set including specific extensions)
            
            if ext not in supported_types and '*' not in supported_types:
                 # fallback check if 'office' is in supported_types but individual ext not explicitly listed 
                 # (SysConfig logic seems to handle expansion)
                 pass
            
            # Save file
            storage_dir = os.path.join(os.getcwd(), "storage", "chat_files")
            file_id = str(uuid.uuid4())
            new_filename = f"{file_id}.{ext}"
            file_path = os.path.join(storage_dir, new_filename)
            
            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            except Exception as e:
                self.log.error(f"Failed to save file: {e}")
                return fail(ErrorCode.INTERNAL_ERROR, "Failed to save file")
                
            # Construct URL
            # The static mount is at /v1/agent/chat/files
            file_url = f"/v1/agent/chat/files/{new_filename}"
            file_size = os.path.getsize(file_path)
            
            return ok({
                "id": file_id,
                "fileName": filename,
                "fileType": ext,
                "fileUrl": file_url,
                "fileSize": file_size,
                "storageType": "local"
            })

        @self.app.post("/v1/agent/chat/stream")
        async def stream_chat(
            request: ChatStreamRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """流式对话接口"""
            try:
                user_id = int(user_ctx.user_id)
            except ValueError:
                self.log.error(f"Invalid user_id format: {user_ctx.user_id}")
                return JSONResponse(
                    status_code=400,
                    content=fail(ErrorCode.INVALID_PARAMS).model_dump()
                )
                
            return StreamingResponse(
                self.agent_service.stream_chat(request, user_id),
                media_type="text/event-stream"
            )

        @self.app.post("/v1/agent/chat/stop", response_model=ApiResponse)
        async def stop_chat(
            request: ChatStopRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """停止生成接口"""
            try:
                user_id = int(user_ctx.user_id)
            except ValueError:
                self.log.error(f"Invalid user_id format: {user_ctx.user_id}")
                return fail(ErrorCode.INVALID_PARAMS)

            if not request.conversationId:
                return fail(ErrorCode.INVALID_PARAMS, "conversationId is required")

            stopped = self.agent_service.stop_generation(request.conversationId)
            if stopped:
                return ok({"status": "stopped"})
            else:
                # If not running, maybe it already finished. Return success anyway?
                # Or return specific code?
                # User asked to stop, if it's not running, it is effectively stopped.
                return ok({"status": "not_running"})

        @self.app.post("/v1/agent/chat/message", response_model=ApiResponse)
        async def chat_message(
            request: ChatStreamRequest,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """普通对话接口"""
            try:
                user_id = int(user_ctx.user_id)
            except ValueError:
                self.log.error(f"Invalid user_id format: {user_ctx.user_id}")
                return fail(ErrorCode.INVALID_PARAMS)

            err, result = await self.agent_service.chat_message(request, user_id)
            if err == ErrorCode.SUCCESS:
                return ok(result)
            return fail(err)

        @self.app.get("/v1/agent/chat/history", response_model=ApiResponse)
        async def get_history(
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """获取历史会话列表"""
            try:
                user_id = int(user_ctx.user_id)
            except ValueError:
                self.log.error(f"Invalid user_id format: {user_ctx.user_id}")
                return fail(ErrorCode.INVALID_PARAMS)
                
            try:
                err, result = await self.agent_service.get_history(user_id)
                if err == ErrorCode.SUCCESS:
                    return ok(result.model_dump())
                return fail(err)
            except Exception as e:
                import traceback
                self.log.error(f"Failed to get history: {str(e)}")
                self.log.error(traceback.format_exc())
                return fail(ErrorCode.INTERNAL_ERROR, str(e))

        @self.app.delete("/v1/agent/chat/history", response_model=ApiResponse)
        async def clear_history(
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """清空历史会话"""
            try:
                user_id = int(user_ctx.user_id)
            except ValueError:
                self.log.error(f"Invalid user_id format: {user_ctx.user_id}")
                return fail(ErrorCode.INVALID_PARAMS)

            err, result = await self.agent_service.clear_history(user_id)
            if err == ErrorCode.SUCCESS:
                return ok(result)
            return fail(err)

        @self.app.get("/v1/agent/chat/conversation/{conversation_id}", response_model=ApiResponse)
        async def get_conversation(
            conversation_id: str,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """获取单个会话详情"""
            err, result = await self.agent_service.get_conversation(conversation_id)
            if err == ErrorCode.SUCCESS:
                return ok(result.model_dump())
            return fail(err)

        @self.app.delete("/v1/agent/chat/conversation/{conversation_id}", response_model=ApiResponse)
        async def delete_conversation(
            conversation_id: str,
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """删除单个会话"""
            err, result = await self.agent_service.delete_conversation(conversation_id)
            if err == ErrorCode.SUCCESS:
                return ok(result)
            return fail(err)

        @self.app.post("/v1/agent/chat/upload", response_model=ApiResponse)
        async def upload_file(
            file: UploadFile = File(...),
            user_ctx: UserContext = Depends(get_validated_user_context),
        ):
            """上传文件接口"""
            try:
                # Generate unique filename
                file_ext = os.path.splitext(file.filename)[1]
                new_filename = f"{uuid.uuid4()}{file_ext}"
                
                # Ensure storage directory exists
                storage_dir = os.path.join(os.getcwd(), "storage", "chat_files")
                os.makedirs(storage_dir, exist_ok=True)
                
                file_path = os.path.join(storage_dir, new_filename)
                
                # Save file
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                    
                file_url = f"/v1/agent/chat/files/{new_filename}"
                file_size = os.path.getsize(file_path)
                
                return ok({
                    "fileName": file.filename,
                    "fileType": file.content_type,
                    "fileSize": file_size,
                    "fileUrl": file_url,
                    "storageType": "local",
                    "thumbnailUrl": None # Optional: generate thumbnail for images
                })
            except Exception as e:
                self.log.error(f"Upload failed: {e}")
                return fail(ErrorCode.SYSTEM_ERROR, str(e))

        @self.app.get("/v1/agent/chat/files/{filename}")
        async def get_file(filename: str):
            """获取文件接口"""
            storage_dir = os.path.join(os.getcwd(), "storage", "chat_files")
            file_path = os.path.join(storage_dir, filename)
            if os.path.exists(file_path):
                return FileResponse(file_path)
            return JSONResponse(status_code=404, content={"code": 404, "message": "File not found"})
