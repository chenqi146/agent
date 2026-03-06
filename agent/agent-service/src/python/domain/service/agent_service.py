from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime
import uuid
import json
import asyncio
import time
import random
import re
from fastapi.responses import StreamingResponse

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.config.sys_config import SysConfig
from infrastructure.persistences.mysql_persistence import MysqlPersistence
from infrastructure.repositories.agent_repository import AgentRepository
from interfaces.dto.chat_dto import (
    ChatConversationDTO, ChatMessageDTO, MessageRole, ContentType,
    ChatStreamRequest, ChatHistoryResponse, ChatConversationResponse,
    ChatMessageAttachmentDTO
)
from interfaces.dto.role_dto import ApplicationRoleIdRequest
from interfaces.dto.prompt_dto import PromptTemplateIdRequest
from domain.service.agent_coordinator import AgentCoordinator
from domain.service.memory_service import MemoryService
from domain.service.rag_service import RagService
from domain.service.application_role_service import ApplicationRoleService
from domain.service.prompt_service import PromptService
from openai import AsyncOpenAI
from infrastructure.client.mcp_client import McpClient

@logger()
class AgentService:
    def __init__(self,memory_service:MemoryService = None, rag_service: RagService = None):
        self.config = SysConfig()
        self.agent_config = self.config.get_agent_config()
        self.mysql_config = self.config.get_system_config().get('persistence', {}).get('mysql', {})
        
        self.persistence = MysqlPersistence(
            host=self.mysql_config.get('host'),
            port=self.mysql_config.get('port'),
            username=self.mysql_config.get('username'),
            password=self.mysql_config.get('password'),
            database=self.mysql_config.get('database')
        )
        self.repository = AgentRepository(self.persistence)
        self.memory_service = memory_service
        self.rag_service = rag_service
        self.role_service = ApplicationRoleService(self.config, self.persistence)
        self.prompt_service = PromptService(self.config, self.persistence)
        
        # Initialize LLM Client
        system_config = self.config.get_system_config()
        vllm_config = system_config.get('vllm', {})
        llm_root_config = vllm_config.get('llm', {})
        
        llm_type = llm_root_config.get('type', 'hsyq')
        llm_config = llm_root_config.get(llm_type, {})
        
        self.llm_client = AsyncOpenAI(
            api_key=llm_config.get('key'),
            base_url=llm_config.get('base_url')
        )
        self.model = llm_config.get('model', 'doubao-seed-1-8-251228')
        
        # Track running generation tasks
        self._running_tasks: Dict[str, bool] = {}
        self.mcp_client = McpClient(self.config, self.persistence)
        
        # Initialize Coordinator
        self.coordinator = AgentCoordinator(
            llm_client=self.llm_client, 
            model=self.model, 
            config=self.config,
            memory_service=self.memory_service, 
            rag_service=self.rag_service,
            mcp_client=self.mcp_client,
            prompt_service=self.prompt_service,
            neo4j_client=None,  # 可从config初始化
            mysql_client=self.persistence  # MysqlPersistence对象本身
        )

    def _build_time_vars(self) -> Dict[str, str]:
        now = datetime.now()
        return {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "current_date": now.strftime("%Y-%m-%d"),
            "current_hhmm": now.strftime("%H:%M"),
            "current_hour": now.strftime("%H"),
        }

    def _render_prompt_template(self, content: str, variables: Dict[str, str]) -> str:
        if not content or not variables:
            return content or ""
        rendered = content
        for key, value in variables.items():
            if value is None:
                continue
            pattern = r"\{\{\s*" + re.escape(str(key)) + r"\s*\}\}"
            rendered = re.sub(pattern, str(value), rendered)
        return rendered

    def _build_template_vars_for_time(self, template) -> Dict[str, str]:
        time_vars = self._build_time_vars()
        if not template or not getattr(template, "variables", None):
            return time_vars

        out: Dict[str, str] = {}
        for v in template.variables:
            key = (getattr(v, "key", None) or "").strip()
            if not key:
                continue
            lowered = key.lower()
            if lowered in {"current_time", "now", "datetime", "time"}:
                out[key] = time_vars["current_time"]
            elif lowered in {"current_date", "date", "today"}:
                out[key] = time_vars["current_date"]
            elif lowered in {"current_hhmm", "hhmm"}:
                out[key] = time_vars["current_hhmm"]
            elif getattr(v, "defaultValue", None):
                out[key] = str(v.defaultValue)

        out.setdefault("current_time", time_vars["current_time"])
        out.setdefault("current_date", time_vars["current_date"])
        out.setdefault("current_hhmm", time_vars["current_hhmm"])
        out.setdefault("current_hour", time_vars["current_hour"])
        return out

    async def _route_prompt_id_with_llm(
        self,
        user_input: str,
        current_time: str,
        candidates: List[Dict[str, Any]],
    ) -> Optional[int]:
        if not candidates:
            return None

        candidate_ids = [int(c["id"]) for c in candidates if c.get("id") is not None]
        if len(candidate_ids) <= 1:
            return candidate_ids[0] if candidate_ids else None

        candidates_payload = []
        for c in candidates:
            cid = c.get("id")
            if cid is None:
                continue
            content = (c.get("content") or "").strip()
            if len(content) > 1200:
                content = content[:1200] + "…"
            candidates_payload.append({
                "id": int(cid),
                "name": c.get("name") or "",
                "content": content,
            })
        try:
            self.log.info(f"[PromptRouter] 候选数量: {len(candidates_payload)}, 当前时间: {current_time}")
            self.log.info(f"[PromptRouter] 候选IDs: {candidate_ids}")
        except Exception:
            pass

        default_router_prompt = (
            "你是一个prompt路由器。你的任务是：根据用户输入与当前时间，从候选prompt中选择最合适的一个作为对话上下文。"
            "只输出JSON，格式严格为：{\"prompt_id\": <number>}。不要输出任何多余文字。"
        )
        system_prompt = default_router_prompt
        try:
            sys_cfg = getattr(self, "config", None).get_system_config() if getattr(self, "config", None) else None
            router_cfg = sys_cfg.get("prompt_router", {}) if sys_cfg else {}
            cfg_prompt = router_cfg.get("system_prompt")
            if isinstance(cfg_prompt, str) and cfg_prompt.strip():
                system_prompt = cfg_prompt.strip()
        except Exception:
            system_prompt = default_router_prompt
        user_prompt = json.dumps(
            {
                "current_time": current_time,
                "user_input": user_input or "",
                "candidates": candidates_payload,
            },
            ensure_ascii=False,
        )

        try:
            resp = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False,
            )
            text = (resp.choices[0].message.content or "").strip()
            self.log.info(f"[PromptRouter] LLM返回: {text[:200]}")
        except Exception as e:
            self.log.warning(f"Prompt routing LLM call failed: {e}")
            return None

        try:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                obj = json.loads(text[start : end + 1])
                pid = obj.get("prompt_id")
                if pid is not None:
                    pid_int = int(pid)
                    if pid_int in candidate_ids:
                        self.log.info(f"[PromptRouter] 路由选择: {pid_int}")
                        return pid_int
        except Exception:
            pass

        m = re.search(r"(\d+)", text)
        if m:
            pid_int = int(m.group(1))
            if pid_int in candidate_ids:
                self.log.info(f"[PromptRouter] 正则回退选择: {pid_int}")
                return pid_int

        return None

    async def _resolve_system_prompt(self, user_id: int, role_id: int, user_input: str = "") -> Optional[str]:
        try:
            # 1. Get Role
            role_req = ApplicationRoleIdRequest(id=role_id)
            err, role = await asyncio.to_thread(self.role_service.get_role, user_id, role_req)
            if err != ErrorCode.SUCCESS or not role:
                return None

            time_vars = self._build_time_vars()
            current_hhmm = time_vars["current_hhmm"]
            current_time = time_vars["current_time"]

            candidate_prompt_ids: List[int] = []
            if role.mode == "dynamic":
                for pid in role.dynamicPrompts or []:
                    try:
                        candidate_prompt_ids.append(int(pid))
                    except Exception:
                        continue
                if not candidate_prompt_ids and role.promptId:
                    candidate_prompt_ids = [int(role.promptId)]
            else:
                if role.fixedPrompts:
                    for rule in role.fixedPrompts:
                        start = rule.get("startTime")
                        end = rule.get("endTime")
                        pid = rule.get("promptId")
                        if start and end and pid and start <= current_hhmm <= end:
                            try:
                                candidate_prompt_ids.append(int(pid))
                            except Exception:
                                continue
                if not candidate_prompt_ids and role.promptId:
                    candidate_prompt_ids = [int(role.promptId)]

            seen = set()
            candidate_prompt_ids = [pid for pid in candidate_prompt_ids if not (pid in seen or seen.add(pid))]

            if not candidate_prompt_ids:
                return role.customPrompt

            selected_prompt_id = candidate_prompt_ids[0]
            candidates_info: List[Dict[str, Any]] = []
            try:
                self.log.info(f"[PromptRouter] 模式: {role.mode}, 候选PromptIDs: {candidate_prompt_ids}")
            except Exception:
                pass

            if len(candidate_prompt_ids) > 1:
                for pid in candidate_prompt_ids:
                    prompt_req = PromptTemplateIdRequest(id=pid)
                    err_p, prompt = await asyncio.to_thread(self.prompt_service.get_template, prompt_req, user_id)
                    if err_p == ErrorCode.SUCCESS and prompt:
                        vars_map = self._build_template_vars_for_time(prompt)
                        rendered = self._render_prompt_template(prompt.content, vars_map)
                        candidates_info.append({"id": pid, "name": prompt.name, "content": rendered})

                if candidates_info:
                    routed = await self._route_prompt_id_with_llm(user_input, current_time, candidates_info)
                    if routed:
                        selected_prompt_id = routed
            try:
                self.log.info(f"[PromptRouter] 最终选用PromptID: {selected_prompt_id}")
            except Exception:
                pass

            prompt_req = PromptTemplateIdRequest(id=selected_prompt_id)
            err, prompt = await asyncio.to_thread(self.prompt_service.get_template, prompt_req, user_id)
            if err == ErrorCode.SUCCESS and prompt:
                vars_map = self._build_template_vars_for_time(prompt)
                rendered = self._render_prompt_template(prompt.content, vars_map)
                try:
                    self.log.info(f"[SystemPrompt] 注入长度: {len(rendered)}")
                except Exception:
                    pass
                return rendered

            return role.customPrompt
            
        except Exception as e:
            self.log.error(f"Failed to resolve system prompt: {e}")
            return None

    async def generate_content(self, request: ChatStreamRequest) -> Tuple[ErrorCode, Optional[Dict]]:
        """
        Directly generate content using LLM without saving history
        """
        try:
            self.log.info(f"[Input] 直接生成 - message_len={len(request.message or '')}, attachments={len(request.attachments or [])}")
            messages = [{"role": "user", "content": request.message}]
            
            # Debug: Print prompt being sent to LLM
            self.log.debug(f"[LLM_PROMPT] generate_content - Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
            
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            
            content = response.choices[0].message.content
            self.log.info(f"[Output] 直接生成 - content_len={len(content or '')}")
            return ErrorCode.SUCCESS, {"content": content}
            
        except Exception as e:
            self.log.error(f"Generate content error: {e}")
            return ErrorCode.INTERNAL_ERROR, None

    async def generate_content_stream(self, request: ChatStreamRequest) -> AsyncGenerator[str, None]:
        """
        Directly generate content using LLM without saving history (Streaming)
        """
        try:
            self.log.info(f"[Input] 流式生成 - message_len={len(request.message or '')}, attachments={len(request.attachments or [])}")
            messages = [{"role": "user", "content": request.message}]
            
            # Debug: Print prompt being sent to LLM
            self.log.debug(f"[LLM_PROMPT] generate_content_stream - Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
            
            stream = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # Format as SSE
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            self.log.error(f"Generate content stream error: {e}")
            error_data = {"code": ErrorCode.INTERNAL_ERROR, "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    def stop_generation(self, conversation_id: str):
        """Stop generation for a specific conversation"""
        if conversation_id in self._running_tasks:
            self._running_tasks[conversation_id] = False
            self.log.info(f"Stop signal received for conversation {conversation_id}")
            return True
        return False

    def _format_time(self, dt):
        if not dt:
            return None
        if isinstance(dt, str):
            return dt
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    async def _save_long_term_memory(self, user_id: int, query: str, response: str, attachments: List[Dict] = None):
        if not self.memory_service:
            return
            
        try:
            # Determine effective query
            effective_query = query
            if not effective_query and attachments:
                file_names = ", ".join([att.get("fileName", "unknown") for att in attachments])
                effective_query = f"User uploaded files: {file_names}"
                
            if not effective_query or not response:
                return

            self.log.info(f"Saving long-term memory for user {user_id}...")
            # Ensure user_id is int
            uid = int(user_id) if str(user_id).isdigit() else 0
            
            err, doc_id = await asyncio.to_thread(
                self.memory_service.add_memory,
                uid,
                effective_query,
                response
            )
            
            if err == ErrorCode.SUCCESS:
                self.log.info(f"Long-term memory saved, DocID: {doc_id}")
            else:
                self.log.warning(f"Failed to save long-term memory: {err}")
        except Exception as e:
            self.log.warning(f"Exception saving long-term memory: {e}")

    def _update_history_index(self, user_id: int, conversation_id: str, message: str, attachments: List[Dict] = None):
        try:
            # 1. Get conversation title
            err, conv = self.repository.get_conversation_by_id(conversation_id)
            if err != ErrorCode.SUCCESS or not conv:
                if message:
                    title = message[:20]
                elif attachments:
                    title = f"File: {attachments[0].get('fileName', 'Attachment')}"
                else:
                    title = "New Conversation"
            else:
                title = conv['title']
                
            # 2. Construct preview
            if message:
                preview = message[:500] # truncate
            elif attachments:
                file_names = [att.get('fileName', 'file') for att in attachments]
                preview = f"[Attachments: {', '.join(file_names)}]"
            else:
                preview = ""
            
            # 3. Save index
            self.repository.save_history_index({
                "user_id": user_id,
                "conversation_id": conversation_id,
                "search_content": f"{title} {preview}",
                "last_message_preview": preview,
                "created_at": datetime.now()
            })
        except Exception as e:
            self.log.error(f"Failed to update history index: {e}")

    async def get_history(self, user_id: int) -> Tuple[ErrorCode, Optional[ChatHistoryResponse]]:
        err, conversations = self.repository.get_conversations(user_id)
        if err != ErrorCode.SUCCESS:
            return err, None
            
        dtos = []
        for conv in conversations:
            dtos.append(ChatConversationDTO(
                id=conv['id'],
                conversationId=conv['conversation_id'],
                userId=conv['user_id'],
                title=conv['title'],
                modelName=conv['model_name'],
                isPinned=bool(conv['is_pinned']),
                messageCount=conv['message_count'],
                tokenCount=conv['token_count'],
                lastMessageTime=self._format_time(conv['last_message_time']),
                isDeleted=bool(conv['is_deleted']),
                createdAt=self._format_time(conv['created_at']),
                updatedAt=self._format_time(conv['updated_at'])
            ))
            
        return ErrorCode.SUCCESS, ChatHistoryResponse(conversations=dtos)

    async def get_conversation(self, conversation_id: str) -> Tuple[ErrorCode, Optional[ChatConversationResponse]]:
        err, conv = self.repository.get_conversation_by_id(conversation_id)
        if err != ErrorCode.SUCCESS or not conv:
            return ErrorCode.RESOURCE_NOT_FOUND, None
            
        err, messages = self.repository.get_messages(conversation_id)
        if err != ErrorCode.SUCCESS:
            return err, None
            
        # Get attachments
        message_ids = [msg['message_id'] for msg in messages]
        _, attachments = self.repository.get_attachments_by_message_ids(message_ids)
        att_map = {}
        if attachments:
            for att in attachments:
                mid = att['message_id']
                if mid not in att_map:
                    att_map[mid] = []
                att_map[mid].append(ChatMessageAttachmentDTO(
                    id=att['id'],
                    messageId=att['message_id'],
                    fileName=att['file_name'],
                    fileType=att['file_type'],
                    fileSize=att['file_size'],
                    fileUrl=att['file_url'],
                    thumbnailUrl=att['thumbnail_url'],
                    storageType=att['storage_type'],
                    metadata=json.loads(att['metadata']) if att['metadata'] and isinstance(att['metadata'], str) else att.get('metadata')
                ))

        msg_dtos = []
        for msg in messages:
            mid = msg['message_id']
            msg_dtos.append(ChatMessageDTO(
                id=str(msg['id']),
                messageId=msg['message_id'],
                conversationId=msg['conversation_id'],
                parentMessageId=msg['parent_message_id'],
                role=MessageRole(msg['role']),
                content=msg['content'],
                contentType=ContentType(msg['content_type']),
                modelName=msg['model_name'],
                tokenCount=msg['token_count'],
                isContext=bool(msg['is_context']),
                metadata=msg['metadata'] if isinstance(msg['metadata'], dict) else None,
                createdAt=self._format_time(msg['created_at']),
                seqNo=msg['seq_no'],
                attachments=att_map.get(mid, [])
            ))
        
        conv_dto = ChatConversationDTO(
            id=conv['id'],
            conversationId=conv['conversation_id'],
            userId=conv['user_id'],
            title=conv['title'],
            modelName=conv['model_name'],
            isPinned=bool(conv['is_pinned']),
            messageCount=conv['message_count'],
            tokenCount=conv['token_count'],
            lastMessageTime=self._format_time(conv['last_message_time']),
            isDeleted=bool(conv['is_deleted']),
            createdAt=self._format_time(conv['created_at']),
            updatedAt=self._format_time(conv['updated_at'])
        )

        return ErrorCode.SUCCESS, ChatConversationResponse(
            conversation=conv_dto,
            messages=msg_dtos
        )

    async def delete_conversation(self, conversation_id: str) -> Tuple[ErrorCode, Any]:
        return self.repository.delete_conversation(conversation_id)

    async def clear_history(self, user_id: int) -> Tuple[ErrorCode, Any]:
        return self.repository.clear_history(user_id)

    async def stream_chat(self, request: ChatStreamRequest, user_id: int) -> AsyncGenerator[str, None]:
        conversation_id = request.conversationId
        
        # 1. Create conversation if not exists
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            title = request.message[:20] if request.message else "New Conversation"
            if not request.message and request.attachments:
                title = f"File: {request.attachments[0].get('fileName')}"
                
            err, _ = await asyncio.to_thread(self.repository.create_conversation, {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "title": title,
                "model_name": self.model,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "last_message_time": datetime.now()
            })
            if err != ErrorCode.SUCCESS:
                yield f"data: {json.dumps({'error': 'Failed to create conversation'})}\n\n"
                return

        # 2. Save user message
        user_msg_id = request.messageId or str(uuid.uuid4())
        
        # Mark conversation as running
        self._running_tasks[conversation_id] = True
        
        await asyncio.to_thread(self.repository.save_message, {
            "message_id": user_msg_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": MessageRole.USER,
            "content": request.message or "",
            "model_name": self.model,
            "seq_no": (await asyncio.to_thread(self.repository.get_last_seq_no, conversation_id)) + 1,
            "created_at": datetime.now()
        })
        
        if request.attachments:
            for att in request.attachments:
                await asyncio.to_thread(self.repository.save_attachment, {
                    "message_id": user_msg_id,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "file_name": att.get("fileName"),
                    "file_type": att.get("fileType"),
                    "file_size": att.get("fileSize"),
                    "file_url": att.get("fileUrl"),
                    "thumbnail_url": att.get("thumbnailUrl"),
                    "storage_type": att.get("storageType", "local"),
                    "metadata": json.dumps(att.get("metadata")) if att.get("metadata") else None,
                    "created_at": datetime.now()
                })
        
        # Update history index for user message
        await asyncio.to_thread(self._update_history_index, user_id, conversation_id, request.message, request.attachments)
        
        # 3. Get context (last N messages)
        _, history_msgs = await asyncio.to_thread(self.repository.get_messages, conversation_id)
        
        context_max_count = 20
        if self.memory_service:
            err, cfg = await asyncio.to_thread(self.memory_service.get_memory_config, user_id)
            if err == ErrorCode.SUCCESS and cfg and cfg.context_max_count:
                context_max_count = int(cfg.context_max_count)
        if history_msgs and len(history_msgs) > context_max_count:
            history_msgs = history_msgs[-context_max_count:]
            
        messages_context = []
        for msg in history_msgs:
            msg_content = msg['content']
            
            # If current message (user) has attachments and empty content, let's inject a prompt
            if msg['message_id'] == user_msg_id and not msg['content'] and request.attachments:
                file_names = ", ".join([att.get("fileName") for att in request.attachments])
                msg_content = f"I have uploaded files: {file_names}. Please analyze them."

            if msg_content:
                messages_context.append({
                    "role": msg['role'],
                    "content": msg_content
                })
        
        # Inject System Prompt if roleId is present
        if request.roleId:
            system_prompt = await self._resolve_system_prompt(user_id, request.roleId, request.message or "")
            if system_prompt:
                # Insert at the beginning or as system message
                messages_context.insert(0, {
                    "role": "system",
                    "content": system_prompt
                })

        # 4. Call LLM Stream
        try:
            self.log.info(f"[Coordination] 开始协调流程 - user_id={user_id}, roleId={request.roleId}, thinking={request.thinking}")
            # Yield conversation ID immediately so frontend knows it
            yield f"data: {json.dumps({'conversationId': conversation_id})}\n\n"

            # 3.5. Coordination (Intent Recognition & Routing)
            coordination_response = ""
            async for chunk_type, chunk_content in self.coordinator.run_coordination(request.message, user_id, thinking=request.thinking):
                if chunk_type == "thinking":
                     yield f"data: {json.dumps({'thinking': chunk_content})}\n\n"
                else:
                    coordination_response += chunk_content
                    # Stream the coordination/planning output
                    yield f"data: {json.dumps({'content': chunk_content})}\n\n"

            if coordination_response:
                    self.log.info(f"[Coordination] 完成，响应长度={len(coordination_response)}")
                    # Save assistant message
                    await asyncio.to_thread(self.repository.save_message, {
                        "message_id": str(uuid.uuid4()),
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "role": MessageRole.ASSISTANT,
                        "content": coordination_response,
                        "model_name": self.model,
                        "seq_no": (await asyncio.to_thread(self.repository.get_last_seq_no, conversation_id)) + 1,
                        "created_at": datetime.now()
                    })
                    await asyncio.to_thread(self.repository.update_conversation, conversation_id, {
                        "last_message_time": datetime.now()
                    })
                    await asyncio.to_thread(self._update_history_index, user_id, conversation_id, coordination_response)
                    await self._save_long_term_memory(user_id, request.message, coordination_response, request.attachments)
                    yield "data: [DONE]\n\n"
                    return

            # Debug: Print prompt being sent to LLM
            self.log.debug(f"[LLM_PROMPT] stream_chat - Conversation ID: {conversation_id}, Messages: {json.dumps(messages_context, ensure_ascii=False, indent=2)}")
            
            # Retrieve memory context for general chat if coordinator didn't handle it
            if self.coordinator:
                try:
                    memory_context = await self.coordinator.get_memory_context(request.message, user_id)
                    if memory_context:
                        # Append to system prompt or insert as a system message
                        system_msg_index = -1
                        for i, msg in enumerate(messages_context):
                            if msg['role'] == 'system':
                                system_msg_index = i
                                break
                        
                        memory_prompt = f"\n\nRelevant Memory:\n{memory_context}\n"
                        
                        if system_msg_index >= 0:
                            messages_context[system_msg_index]['content'] += memory_prompt
                        else:
                            messages_context.insert(0, {
                                "role": "system",
                                "content": f"You are a helpful assistant.{memory_prompt}"
                            })
                        
                        self.log.info(f"Injected memory context into prompt: {len(memory_context)} chars")
                except Exception as e:
                    self.log.warning(f"Failed to inject memory context: {e}")

            stream = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages_context,
                stream=True
            )
            
            assistant_response = ""
            
            async for chunk in stream:
                # Check stop flag
                if not self._running_tasks.get(conversation_id, False):
                    self.log.info(f"Generation stopped for {conversation_id}")
                    # yield f"data: {json.dumps({'error': 'Stopped by user', 'code': 'STOPPED'})}\n\n"
                    # Don't yield error, just stop. Frontend handles it.
                    break

                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    assistant_response += content
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            # 5. Save assistant message (even if stopped)
            await asyncio.to_thread(self.repository.save_message, {
                "message_id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": MessageRole.ASSISTANT,
                "content": assistant_response,
                "model_name": self.model,
                "seq_no": (await asyncio.to_thread(self.repository.get_last_seq_no, conversation_id)) + 1,
                "created_at": datetime.now()
            })
            
            # Update conversation last message time
            await asyncio.to_thread(self.repository.update_conversation, conversation_id, {
                "last_message_time": datetime.now()
            })
            
            # Update history index for assistant message
            await asyncio.to_thread(self._update_history_index, user_id, conversation_id, assistant_response)
            await self._save_long_term_memory(user_id, request.message, assistant_response, request.attachments)
            
            # Signal done if not stopped (or always?)
            # If stopped, we might not want to send [DONE] if frontend uses it to close.
            # But here we just break.
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            self.log.error(f"Stream chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            if conversation_id in self._running_tasks:
                del self._running_tasks[conversation_id]

    async def chat_message(self, request: ChatStreamRequest, user_id: int) -> Tuple[ErrorCode, Optional[Dict]]:
        conversation_id = request.conversationId
        
        # 1. Create conversation if not exists
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            title = request.message[:20] if request.message else "New Conversation"
            if not request.message and request.attachments:
                title = f"File: {request.attachments[0].get('fileName')}"
                
            err, _ = await asyncio.to_thread(self.repository.create_conversation, {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "title": title,
                "model_name": self.model,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "last_message_time": datetime.now()
            })
            if err != ErrorCode.SUCCESS:
                return err, None

        # 2. Save user message
        user_msg_id = request.messageId or str(uuid.uuid4())
        await asyncio.to_thread(self.repository.save_message, {
            "message_id": user_msg_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": MessageRole.USER,
            "content": request.message or "",
            "model_name": self.model,
            "seq_no": (await asyncio.to_thread(self.repository.get_last_seq_no, conversation_id)) + 1,
            "created_at": datetime.now()
        })
        
        if request.attachments:
            for att in request.attachments:
                await asyncio.to_thread(self.repository.save_attachment, {
                    "message_id": user_msg_id,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "file_name": att.get("fileName"),
                    "file_type": att.get("fileType"),
                    "file_size": att.get("fileSize"),
                    "file_url": att.get("fileUrl"),
                    "thumbnail_url": att.get("thumbnailUrl"),
                    "storage_type": att.get("storageType", "local"),
                    "metadata": json.dumps(att.get("metadata")) if att.get("metadata") else None,
                    "created_at": datetime.now()
                })

        # Update history index for user message
        await asyncio.to_thread(self._update_history_index, user_id, conversation_id, request.message, request.attachments)
        
        # 3. Get context
        _, history_msgs = await asyncio.to_thread(self.repository.get_messages, conversation_id)
        
        context_max_count = 20
        if self.memory_service:
            err, cfg = await asyncio.to_thread(self.memory_service.get_memory_config, user_id)
            if err == ErrorCode.SUCCESS and cfg and cfg.context_max_count:
                context_max_count = int(cfg.context_max_count)
        if history_msgs and len(history_msgs) > context_max_count:
            history_msgs = history_msgs[-context_max_count:]
            
        messages_context = []
        for msg in history_msgs:
            msg_content = msg['content']
            if msg['message_id'] == user_msg_id and not msg['content'] and request.attachments:
                 file_names = ", ".join([att.get("fileName") for att in request.attachments])
                 msg_content = f"I have uploaded files: {file_names}. Please analyze them."
            
            if msg_content:
                messages_context.append({
                    "role": msg['role'],
                    "content": msg_content
                })

        # Inject System Prompt if roleId is present
        if request.roleId:
            system_prompt = await self._resolve_system_prompt(user_id, request.roleId, request.message or "")
            if system_prompt:
                # Insert at the beginning or as system message
                messages_context.insert(0, {
                    "role": "system",
                    "content": system_prompt
                })
            
        # 3.5. Coordination (Intent Recognition & Routing)
        coordination_response = ""
        async for chunk_type, chunk_content in self.coordinator.run_coordination(request.message, user_id, thinking=request.thinking):
            if chunk_type == "content":
                coordination_response += chunk_content

        if coordination_response:
            await asyncio.to_thread(self.repository.save_message, {
                "message_id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": MessageRole.ASSISTANT,
                "content": coordination_response,
                "model_name": self.model,
                "seq_no": (await asyncio.to_thread(self.repository.get_last_seq_no, conversation_id)) + 1,
                "created_at": datetime.now()
            })
            await asyncio.to_thread(self.repository.update_conversation, conversation_id, {
                "last_message_time": datetime.now()
            })
            await asyncio.to_thread(self._update_history_index, user_id, conversation_id, coordination_response)
            await self._save_long_term_memory(user_id, request.message, coordination_response, request.attachments)
            return ErrorCode.SUCCESS, {
                "conversationId": conversation_id,
                "content": coordination_response
            }

        # 4. Call LLM
        try:
            # Debug: Print prompt being sent to LLM
            self.log.debug(f"[LLM_PROMPT] chat_message - Conversation ID: {conversation_id}, Messages: {json.dumps(messages_context, ensure_ascii=False, indent=2)}")
            self.log.info(f"[Input] 普通生成 - context_len={len(messages_context)}, roleId={request.roleId}, attachments={len(request.attachments or [])}")
            
            # Retrieve memory context for general chat if coordinator didn't handle it
            if self.coordinator:
                try:
                    memory_context = await self.coordinator.get_memory_context(request.message, user_id)
                    if memory_context:
                        # Append to system prompt or insert as a system message
                        system_msg_index = -1
                        for i, msg in enumerate(messages_context):
                            if msg['role'] == 'system':
                                system_msg_index = i
                                break
                        
                        memory_prompt = f"\n\nRelevant Memory:\n{memory_context}\n"
                        
                        if system_msg_index >= 0:
                            messages_context[system_msg_index]['content'] += memory_prompt
                        else:
                            messages_context.insert(0, {
                                "role": "system",
                                "content": f"You are a helpful assistant.{memory_prompt}"
                            })
                        
                        self.log.info(f"Injected memory context into prompt: {len(memory_context)} chars")
                except Exception as e:
                    self.log.warning(f"Failed to inject memory context: {e}")

            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages_context,
                stream=False
            )
            
            assistant_response = response.choices[0].message.content
            self.log.info(f"[Output] 普通生成 - content_len={len(assistant_response or '')}")
            
            # 5. Save assistant message
            await asyncio.to_thread(self.repository.save_message, {
                "message_id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": MessageRole.ASSISTANT,
                "content": assistant_response,
                "model_name": self.model,
                "seq_no": (await asyncio.to_thread(self.repository.get_last_seq_no, conversation_id)) + 1,
                "created_at": datetime.now()
            })
            
            # Update conversation last message time
            await asyncio.to_thread(self.repository.update_conversation, conversation_id, {
                "last_message_time": datetime.now()
            })
            
            # Update history index for assistant message
            await asyncio.to_thread(self._update_history_index, user_id, conversation_id, assistant_response)
            await self._save_long_term_memory(user_id, request.message, assistant_response, request.attachments)
            
            return ErrorCode.SUCCESS, {
                "conversationId": conversation_id,
                "content": assistant_response
            }
            
        except Exception as e:
            self.log.error(f"LLM Error: {e}")
            return ErrorCode.INTERNAL_ERROR, None

    async def handle_ping(self):
        return ErrorCode.SUCCESS, {"status": "ok"}

    async def list_mcp_tools(self, page: int, page_size: int) -> Tuple[ErrorCode, Any]:
        """List MCP tools"""
        return await asyncio.to_thread(self.mcp_client.list_tools, page, page_size)
