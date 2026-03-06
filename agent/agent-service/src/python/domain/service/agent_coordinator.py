from typing import AsyncGenerator, List, Dict, Any, Optional, Tuple
import json
import html
import asyncio
import uuid
import re
import os
from datetime import datetime
from openai import AsyncOpenAI

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.client.neo4j_client import Neo4jClient
from infrastructure.config.sys_config import SysConfig

from domain.service.planning_agents import (
    CityParkingAgent, StewardAgent,
    ParkingBillingAgent, ParkingOperationAgent, ArrearsCollectionAgent
)
from domain.service.rag_service import RagService
from domain.service.memory_service import MemoryService
from domain.service.prompt_service import PromptService
from domain.service.context_manager import ContextManager
from domain.service.task_manager import TaskManager
from infrastructure.client.fasttext_client import FastTextClient
from infrastructure.repositories.tools_repository import ToolsRepository

from interfaces.dto.rag_dto import RagQueryRequest, KnowledgeBaseListRequest
from interfaces.dto.memory_dto import MemoryContentSearchRequest
from interfaces.dto.coordinator_dto import (
    CoordinateRequest, CoordinateResponse, IntentRecognitionResult,
    SessionContext, TaskInfo, TaskStatus, FullContext
)

@logger()
class AgentCoordinator:
    """
    协调智能体（Coordinator Agent）
    
    核心功能：
    1. 意图识别：FastText + Neo4j双引擎
    2. 上下文构建：会话级（Redis）、业务级（MySQL/Neo4j）、领域知识级（Neo4j）
    3. 任务管理：创建、分配、监控、汇总
    4. 会话管理：状态维护、历史记录
    5. 任务分发：匹配规划智能体
    6. 结果汇总：多任务结果聚合
    """
    
    def __init__(
        self,
        llm_client: AsyncOpenAI,
        model: str,
        config: SysConfig = None,
        memory_service: MemoryService = None,
        rag_service: RagService = None,
        mcp_client = None,
        prompt_service: PromptService = None,
        neo4j_client: Neo4jClient = None,
        mysql_client = None
    ):
        self.llm_client = llm_client
        self.model = model
        self.config = config
        self.memory_service = memory_service
        self.rag_service = rag_service
        self.mcp_client = mcp_client
        self.prompt_service = prompt_service
        
        # 初始化FastText客户端（意图识别第一阶段）
        ft_config = config.get_system_config() if config else {}
        self.fasttext_client = FastTextClient(ft_config)
        
        # 初始化Neo4j客户端
        self._neo4j = neo4j_client
        if not self._neo4j and config:
            try:
                self._neo4j = Neo4jClient(config)
            except Exception as e:
                self.log.warning(f"Neo4j client init failed: {e}")
        
        # 初始化上下文管理器
        self.context_manager = ContextManager(
            config=ft_config,
            neo4j_client=self._neo4j,
            mysql_client=mysql_client
        )
        
        # 初始化工具仓库
        self.tools_repository = None
        if mysql_client:
            self.tools_repository = ToolsRepository(mysql_client)
        
        # 初始化任务管理器
        self.task_manager = TaskManager(ft_config)
        
        # 初始化规划智能体
        self.city_parking_agent = CityParkingAgent(llm_client, model)
        self.steward_agent = StewardAgent(llm_client, model)
        self.parking_billing_agent = ParkingBillingAgent(llm_client, model)
        self.parking_operation_agent = ParkingOperationAgent(llm_client, model)
        self.arrears_collection_agent = ArrearsCollectionAgent(llm_client, model)
        
        # 意图到智能体的映射
        self.intent_agent_map = {
            "city_parking": self.city_parking_agent,
            "steward": self.steward_agent,
            "vehicle_query": self.city_parking_agent,
            "parking_query": self.city_parking_agent,
            "monitor": self.steward_agent,
            "alert": self.steward_agent,
            "patrol": self.steward_agent,
            "parking_billing": self.parking_billing_agent,
            "parking_operation": self.parking_operation_agent,
            "arrears_collection": self.arrears_collection_agent
        }
        
        # 意图到工具的映射（处理别名）
        
        self.log.info("AgentCoordinator initialized with FastText+Neo4j dual-engine intent recognition")

    async def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Fetch available tools from MCP client."""
        if not self.mcp_client:
            return []
        try:
            # Assume 50 tools is enough for now
            err, result = await asyncio.to_thread(self.mcp_client.list_tools, 1, 50)
            if err != ErrorCode.SUCCESS:
                self.log.warning(f"Failed to list tools: {result}")
                return []
            
            if isinstance(result, dict):
                return result.get("items", [])
            elif isinstance(result, list):
                return result
            return []
        except Exception as e:
            self.log.error(f"Error fetching tools: {e}")
            return []

    async def analyze_intent(self, query: str, user_id: int) -> Dict[str, Any]:
        """
        Analyzes the user's request to determine intent and extract key parameters.
        Returns a JSON object with 'intent' (str) and 'parameters' (dict).
        Possible intents: 'city_parking', 'steward', 'general_chat', or tool names.
        """
        self.log.info("=" * 60)
        self.log.info("【意图识别】开始分析用户查询...")
        self.log.info(f"  原始查询: '{query[:50]}...' " if len(query) > 50 else f"  原始查询: '{query}'")
        
        # 1. Fetch available tools
        tools = await self._get_available_tools()
        self.log.info(f"【意图识别】加载了 {len(tools)} 个可用工具")
        
        # 2. Build tool descriptions for prompt
        tool_desc_list = []
        for t in tools:
            name = t.get("name")
            desc = t.get("description", "No description")
            schema = t.get("inputSchema") or t.get("parameters")
            tool_info = f"- '{name}': {desc}"
            if schema:
                tool_info += f" (Args: {json.dumps(schema, ensure_ascii=False)})"
            tool_desc_list.append(tool_info)
            self.log.info(f"  工具: {name}")
            
        tool_section = ""
        if tool_desc_list:
            tool_section = "Available Tools (use these as intents if applicable):\n" + "\n".join(tool_desc_list) + "\n"

        # 3. Fetch system prompt from DB or use default
        system_prompt = ""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.prompt_service:
            self.log.info(f"【意图识别】从MySQL获取用户 {user_id} 的prompt (时间: {current_time})...")
            err, prompt_val = await asyncio.to_thread(
                self.prompt_service.get_prompt_constant, 
                user_id, "agent-coordinator", "system_prompt", current_time
            )
            if err == ErrorCode.SUCCESS and prompt_val:
                system_prompt = prompt_val
                self.log.info("【意图识别】成功获取用户自定义系统提示词")
                
                # 动态补齐缺失的新增意图（兼容旧的数据库prompt配置）
                new_intents = []
                if "parking_billing" not in system_prompt:
                    new_intents.append('- "parking_billing"：与正常停车计费事件相关（计费计算、规则管理、支付处理、发票生成）。')
                if "parking_operation" not in system_prompt:
                    new_intents.append('- "parking_operation"：与停车运营规划相关（运营策略、资源分配、营收分析）。')
                if "arrears_collection" not in system_prompt:
                    new_intents.append('- "arrears_collection"：与欠费追缴相关（欠费分析、催缴策略、法务支持）。')
                
                if new_intents:
                    self.log.info(f"【意图识别】自动补齐 {len(new_intents)} 个缺失意图到系统提示词")
                    new_intents_str = "\n".join(new_intents) + "\n"
                    # 尝试插入到 general_chat 之前
                    if '- "general_chat"' in system_prompt:
                        system_prompt = system_prompt.replace('- "general_chat"', new_intents_str + '- "general_chat"')
                    elif "可能的意图：" in system_prompt:
                        system_prompt = system_prompt.replace("可能的意图：", "可能的意图：\n" + new_intents_str)
                    else:
                        system_prompt += "\n" + new_intents_str
                self.log.info(f"【意图识别】用户prompt长度: {len(system_prompt)} 字符")
            else:
                self.log.info(f"【意图识别】未获取到用户prompt (错误码: {err})，将使用默认提示词")

        if not system_prompt:
            self.log.info("【意图识别】使用默认系统提示词")
            # Fallback default prompt
            system_prompt = (
                "You are an Intent Recognition Agent. Analyze the user's request and determine the primary intent.\n"
                "Possible intents:\n"
                "- 'city_parking': Related to city parking management, tasks, analysis, or decision support.\n"
                "- 'steward': Related to steward functions (monitoring, alerting, auto license plate, evidence, patrol, external services).\n"
                "- 'parking_billing': Related to parking fee calculation, billing rules, payment, or invoices (正常停车计费事件).\n"
                "- 'parking_operation': Related to operation strategy, resource allocation, revenue analysis (停车运营规划).\n"
                "- 'arrears_collection': Related to debt analysis, collection strategy, legal process (欠费追缴).\n"
                "- 'general_chat': General conversation or other topics.\n"
                f"{tool_section}\n"
                "If the user's request matches a tool, output the tool name as the intent.\n"
                "Output ONLY a valid JSON object with the following structure:\n"
                "{\n"
                '  "intent": "intent_name",\n'
                '  "parameters": { "key": "value" },\n'
                '  "reasoning": "brief reason"\n'
                "}"
            )
        else:
            # 在用户自定义prompt基础上补齐上下文
            self.log.info("【意图识别】在用户prompt基础上补齐上下文...")
            # 追加工具信息
            if tool_section:
                if "Available Tools" not in system_prompt and "工具" not in system_prompt:
                    system_prompt += f"\n\n{tool_section}"
                    self.log.info("【意图识别】已追加工具信息到prompt")
            # 追加输出格式要求（如果用户prompt中没有）
            if "intent" not in system_prompt or "parameters" not in system_prompt:
                system_prompt += (
                    "\n\n输出要求：\n"
                    "Output ONLY a valid JSON object with the following structure:\n"
                    "{\n"
                    '  "intent": "intent_name",\n'
                    '  "parameters": { "key": "value" },\n'
                    '  "reasoning": "brief reason"\n'
                    "}"
                )
                self.log.info("【意图识别】已追加输出格式要求到prompt")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        # 打印最终发送给LLM的完整prompt
        self.log.info("=" * 80)
        self.log.info("【意图识别 - 最终发送给LLM的完整Prompt】")
        self.log.info("=" * 80)
        self.log.info("📍 [协调智能体] 意图识别阶段")
        self.log.info(f"👤 用户ID: {user_id}")
        self.log.info(f"💬 原始查询: '{query}'")
        self.log.info(f"🔧 可用工具数量: {len(tools)}")
        self.log.info("-" * 80)
        self.log.info("🤖 System Prompt:")
        # 分段打印系统提示词，避免过长
        if len(system_prompt) > 1000:
            self.log.info(system_prompt[:500])
            self.log.info(f"... (中间部分省略，总长 {len(system_prompt)} 字符) ...")
            self.log.info(system_prompt[-300:])
        else:
            self.log.info(system_prompt)
        self.log.info("-" * 80)
        self.log.info("👤 User Query:")
        self.log.info(query)
        self.log.info("-" * 80)
        self.log.info(f"📊 Messages 结构: 共 {len(messages)} 条消息")
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            preview = content[:100] + "..." if len(content) > 100 else content
            self.log.info(f"  Message {i}: role={role}, content={preview}")
        self.log.info("=" * 80)
        
        self.log.info("【意图识别】调用LLM进行意图分析...")

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            
            self.log.info("【意图识别】LLM返回结果:")
            self.log.info(f"  🎯 识别意图: {result.get('intent', 'unknown')}")
            self.log.info(f"  📋 提取参数: {result.get('parameters', {})}")
            self.log.info(f"  🧠 推理过程: {result.get('reasoning', 'N/A')}")
            
            # 检查槽位信息
            params = result.get('parameters', {})
            if params:
                self.log.info("📝 槽位信息详情:")
                for key, value in params.items():
                    self.log.info(f"  - {key}: {value}")
            else:
                self.log.info("📝 未提取到槽位信息")
            
            self.log.info("=" * 80)
            self.log.info("🎯 [协调智能体] 意图识别阶段完成")
            self.log.info("=" * 80)
            return result
        except Exception as e:
            self.log.error(f"【意图识别】失败: {e}")
            # Fallback to general chat if parsing fails
            return {"intent": "general_chat", "parameters": {}, "reasoning": f"Error: {str(e)}"}

    async def _get_rag_context(self, query: str, user_id: int) -> str:
        """获取RAG上下文"""
        self.log.info(f"    [知识库检索] 开始RAG检索...")
        self.log.info(f"    [知识库检索] 查询: '{query[:40]}...'")
        
        if not self.rag_service:
            self.log.warning("    [知识库检索] RagService 未初始化，跳过知识库检索")
            return ""
        
        try:
            # 1. Find a default KB (just pick the first one for now)
            self.log.info("    [知识库检索] 查询可用的知识库...")
            req = KnowledgeBaseListRequest(page_no=1, page_size=1)
            err, page = await self.rag_service.list_knowledge_bases(req, user_id)
            
            if err != ErrorCode.SUCCESS:
                self.log.warning(f"    [知识库检索] 知识库列表查询失败: {err}")
                return ""
            
            if not page.items:
                self.log.warning("    [知识库检索] 未找到可用的知识库")
                return ""
            
            kb_id = page.items[0].id
            kb_name = getattr(page.items[0], 'name', 'Unknown')
            self.log.info(f"    [知识库检索] 使用知识库: {kb_name} (ID: {kb_id})")
            
            # 2. Query RAG
            rag_req = RagQueryRequest(kb_id=kb_id, query=query, top_k=3)
            self.log.info("    [知识库检索] 执行向量检索 (top_k=3)...")
            err, result = await self.rag_service.rag_query(rag_req, user_id)
            
            if err != ErrorCode.SUCCESS:
                self.log.warning(f"    [知识库检索] RAG查询失败: {err}")
                return ""
            
            rag_text = ""
            if hasattr(result, 'source_documents'):
                docs = result.source_documents
                self.log.info(f"    [知识库检索] 检索到 {len(docs)} 个文档片段")
                for i, doc in enumerate(docs, 1):
                    preview = doc[:50] if isinstance(doc, str) else str(doc)[:50]
                    self.log.info(f"      片段{i}: {preview}...")
                rag_text = "\n".join(docs) if docs else ""
            elif isinstance(result, dict) and 'source_documents' in result:
                docs = result['source_documents']
                self.log.info(f"    [知识库检索] 检索到 {len(docs)} 个文档片段")
                rag_text = "\n".join(docs) if docs else ""
            else:
                self.log.info(f"    [知识库检索] 结果格式: {type(result)}, 无source_documents")
            
            self.log.info(f"    [知识库检索] RAG上下文总长度: {len(rag_text)} 字符")
            return rag_text
            
        except Exception as e:
            self.log.warning(f"    [知识库检索] RAG检索异常: {e}")
            return ""

    async def get_memory_context(self, query: str, user_id: int) -> str:
        self.log.info(f"    [记忆检索] 开始检索用户 {user_id} 的记忆，查询: '{query[:30]}...'")
        if not self.memory_service:
            self.log.warning("    [记忆检索] MemoryService 未初始化")
            return ""
        
        try:
            # Search recent and relevant memories
            req = MemoryContentSearchRequest(
                keyword=query,
                page=1,
                page_size=5,
                time_range="last30d"
            )
            
            err, result = await asyncio.to_thread(self.memory_service.search_memory_content, user_id, req)
            
            if err != ErrorCode.SUCCESS:
                self.log.warning(f"    [记忆检索] 记忆服务返回错误: {err}")
                return ""
            
            if not result:
                self.log.info("    [记忆检索] 未找到相关记忆")
                return ""
            
            items = result.get("items", [])
            if not items:
                self.log.info("    [记忆检索] 记忆结果为空")
                return ""
            
            self.log.info(f"    [记忆检索] 找到 {len(items)} 条相关记忆")
                
            memory_texts = []
            for i, item in enumerate(items, 1):
                # item is a dict here because of model_dump in service
                fact = item.get("fact", "")
                detail = item.get("detail", "")
                if fact or detail:
                    memory_texts.append(f"- {fact}: {detail}")
                    preview = fact[:30] if len(fact) > 30 else fact
                    self.log.info(f"      记忆{i}: {preview}...")
            
            result_text = "\n".join(memory_texts)
            self.log.info(f"    [记忆检索] 记忆上下文总长度: {len(result_text)} 字符")
            return result_text
            
        except Exception as e:
            self.log.warning(f"    [记忆检索] 记忆检索异常: {e}")
            return ""

    async def _get_memory_context(self, query: str, user_id: int) -> str:
        return await self.get_memory_context(query, user_id)

    async def run_coordination(self, query: str, user_id: int, thinking: bool = False) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Main entry point for coordination.
        """
        self.log.info("=" * 60)
        self.log.info(f"[协调入口] user_id={user_id}, thinking={thinking}")
        self.log.info(f"[协调入口] 用户输入: {query[:200]}{'...' if len(query) > 200 else ''}")
        start_ts = datetime.now()
        # 1. Intent Recognition
        intent_data = await self.analyze_intent(query, user_id)
        intent = intent_data.get("intent")
        reasoning = intent_data.get("reasoning", "")
        self.log.info(f"Intent recognized: {intent}")

        if intent in ["city_parking", "steward", "parking_billing", "parking_operation", "arrears_collection"]:
            yield ("content", f"Recognized intent: {intent}. Planning...\n")
            
            self.log.info("[协调] 开始构建上下文 (RAG + 记忆)")
            rag_context = await self._get_rag_context(query, user_id)
            memory_context = await self._get_memory_context(query, user_id)
            self.log.info(f"[协调] RAG上下文长度={len(rag_context)}, 记忆上下文长度={len(memory_context)}")
            
            full_context = f"RAG Knowledge:\n{rag_context}\n\nMemory Context:\n{memory_context}\n"

            # 3. Route to Specialized Agent
            agent = None
            prompt_app_type = None
            
            if intent == "city_parking":
                agent = self.city_parking_agent
                prompt_app_type = "agent-planning"
            elif intent == "steward":
                agent = self.steward_agent
                prompt_app_type = "steward-agent"
            elif intent == "parking_billing":
                agent = self.parking_billing_agent
                prompt_app_type = "parking-billing-agent"
            elif intent == "parking_operation":
                agent = self.parking_operation_agent
                prompt_app_type = "parking-operation-agent"
            elif intent == "arrears_collection":
                agent = self.arrears_collection_agent
                prompt_app_type = "arrears-collection-agent"
            
            # Fetch agent-specific prompt
            agent_system_prompt = None
            if self.prompt_service and prompt_app_type:
                err, prompt_val = await asyncio.to_thread(
                    self.prompt_service.get_prompt_constant, 
                    user_id, prompt_app_type, "system_prompt"
                )
                if err == ErrorCode.SUCCESS and prompt_val:
                    agent_system_prompt = prompt_val
                
            if agent:
                self.log.info(f"[协调] 路由到规划智能体: {agent.__class__.__name__}, prompt_app_type={prompt_app_type}")
                if thinking:
                    elapsed = (datetime.now() - start_ts).total_seconds()
                    rag_len = len(rag_context)
                    mem_len = len(memory_context)
                    lines = []
                    lines.append(f"已完成深度思考（用时约 {int(round(elapsed))} 秒）")
                    lines.append("")
                    lines.append("思考摘要：")
                    lines.append(f"- 意图识别：{intent or 'unknown'}")
                    if reasoning:
                        lines.append(f"- 识别依据：{reasoning}")
                    lines.append(f"- 上下文摘要：RAG {rag_len} 字符，记忆 {mem_len} 字符")
                    lines.append(f"- 规划路由：{agent.__class__.__name__}")
                    lines.append("")
                    lines.append("核心流程：")
                    lines.append("1. 意图识别：结合工具清单和领域标签确定处理路径")
                    lines.append("2. 上下文构建：检索知识库与用户记忆并整合")
                    lines.append("3. 规划路由：选择专用智能体并装载其系统提示词")
                    lines.append("4. 任务生成：分解目标、分析依赖、匹配工具、形成任务链")
                    lines.append("5. 执行与输出：按序调用工具与LLM，生成结构化结果")
                    lines.append("")
                    lines.append("回答策略：先给出清晰结构的说明，再补充细节与可操作步骤。")
                    yield ("thinking", "\n".join(lines) + "\n")
                async for chunk in agent.generate_plan(query, full_context, system_prompt=agent_system_prompt):
                    yield ("content", chunk)
            return

        if intent == "general_chat":
            return

        # 4. Generic Tool Execution
        if self.mcp_client:
            try:
                # 映射意图到工具名称
                tool_name = intent
                if self.tools_repository:
                    err, tool_info = self.tools_repository.find_tool_by_intent(intent)
                    if err == ErrorCode.SUCCESS and tool_info:
                        tool_name = tool_info.get("name", intent)
                
                if thinking:
                    elapsed = (datetime.now() - start_ts).total_seconds()
                    lines = []
                    lines.append(f"已完成深度思考（用时约 {int(round(elapsed))} 秒）")
                    lines.append("")
                    lines.append("思考摘要：")
                    lines.append(f"- 意图识别：{intent or 'unknown'}")
                    if reasoning:
                        lines.append(f"- 识别依据：{reasoning}")
                    lines.append(f"- 工具路由：{tool_name}")
                    lines.append("")
                    lines.append("核心流程：")
                    lines.append("1. 意图到工具映射：查询工具仓库并解析输入模式")
                    lines.append("2. 参数整备：抽取用户输入中的可用参数")
                    lines.append("3. 执行工具：调用后端 MCP 工具并捕获输出")
                    lines.append("4. 结果整形：按前端可视化协议包装（HTML/ECharts/文本）")
                    lines.append("5. 响应生成：输出规范化内容并流式传递到前端")
                    lines.append("")
                    lines.append("回答策略：先给出可执行结果，必要时附带解释与后续建议。")
                    yield ("thinking", "\n".join(lines) + "\n")
                
                arguments = intent_data.get("parameters", {})
                
                # Execute tool
                err, result = await asyncio.to_thread(self.mcp_client.execute_tool, tool_name, arguments)
                if err == ErrorCode.SUCCESS:
                    if isinstance(result, dict) and "html" in result:
                        # Wrap HTML in iframe for frontend rendering
                        escaped_html = html.escape(result["html"], quote=True)
                        content = f'<iframe srcdoc="{escaped_html}" width="100%" height="600px" style="border:none;"></iframe>'
                    elif isinstance(result, dict) and "echarts_html" in result:
                        # Direct ECharts snippet for frontend hydration
                        content = result["echarts_html"]
                    else:
                        content = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
                    yield ("content", content)
                else:
                    yield ("content", f"Tool execution failed: {result}")
            except Exception as e:
                yield ("content", f"Tool execution error: {str(e)}")
        else:
            yield ("content", "Tool service unavailable.")

    # ==================== 新增协调智能体核心方法 ====================

    async def coordinate(
        self, 
        request: CoordinateRequest
    ) -> Tuple[ErrorCode, CoordinateResponse]:
        """
        协调智能体主入口
        
        完整流程（深度思考模式）：
        1. 意图识别（FastText + Neo4j）
        2. 指代解析
        3. 上下文构建
        4. 任务创建
        5. 任务分发
        6. 执行与监控
        7. 结果汇总
        
        简化流程（非深度思考模式）：
        1. 意图识别
        2. 读取记忆
        3. RAG检索
        4. 直接LLM响应
        5. 保存记忆
        """
        try:
            # 检查是否启用深度思考
            if not request.thinking:
                self.log.info("深度思考已关闭，使用简化流程")
                return await self._simple_flow(request)
            
            self.log.info("=" * 60)
            self.log.info(f"【协调流程开始】用户ID: {request.user_id}, 查询: '{request.query[:50]}...'")
            self.log.info("=" * 60)
            
            # 1. 生成或获取会话ID
            session_id = request.session_id or f"sess_{uuid.uuid4().hex[:16]}"
            self.log.info(f"[1/10] 会话ID: {session_id} (新建: {not request.session_id})")
            
            # 2. 加载会话上下文
            self.log.info("[2/10] 正在加载会话上下文...")
            err, session_ctx = await self.context_manager.load_session_context(
                session_id, request.user_id
            )
            if err != ErrorCode.SUCCESS:
                self.log.error(f"[2/10] 加载会话上下文失败: {err}")
                return err, None
            
            self.log.info(f"[2/10] 会话上下文加载成功")
            self.log.info(f"      - 历史轮数: {len(session_ctx.dialogue_history)}")
            self.log.info(f"      - 意图栈: {session_ctx.intent_stack}")
            self.log.info(f"      - 已确认槽位: {list(session_ctx.confirmed_slots.keys())}")
            
            # 3. FastText第一阶段：快速意图分类
            self.log.info("[3/10] FastText第一阶段：快速意图分类...")
            ft_err, ft_candidates = await self.fasttext_client.classify_intent(
                request.query, top_k=3
            )
            
            if ft_err == ErrorCode.SUCCESS:
                self.log.info(f"[3/10] FastText分类完成")
                for i, cand in enumerate(ft_candidates, 1):
                    self.log.info(f"      Top-{i}: {cand['intent']} (置信度: {cand['confidence']:.3f})")
            else:
                self.log.warning(f"[3/10] FastText分类失败: {ft_err}")
            
            # 4. 指代解析
            self.log.info("[4/10] 指代解析...")
            ref_err, ref_result = await self.fasttext_client.resolve_reference(
                request.query,
                session_ctx.dialogue_history,
                session_ctx.confirmed_slots
            )
            
            self.log.info(f"[4/10] 指代解析结果: {ref_result}")
            
            # 合并指代解析结果到查询
            resolved_query = request.query
            if ref_result.get("resolved"):
                entity_info = ref_result.get("entity_value", {})
                if "plate_number" in entity_info:
                    resolved_query = f"{request.query} (车牌号: {entity_info['plate_number']})"
                    self.log.info(f"[4/10] 指代解析成功: 车牌号 = {entity_info['plate_number']}")
                    # 确认槽位
                    await self.context_manager.confirm_slot(
                        session_id, request.user_id, "vehicle", entity_info
                    )
            else:
                self.log.info("[4/10] 未解析到指代")
            
            # 5. Neo4j第二阶段：本体精确定位
            self.log.info("[5/10] Neo4j第二阶段：本体验证...")
            intent_result = await self._neo4j_intent_verification(
                ft_candidates, resolved_query, request.user_id
            )
            
            self.log.info(f"[5/10] 意图验证完成")
            self.log.info(f"      - 主意图: {intent_result.primary_intent}")
            self.log.info(f"      - 置信度: {intent_result.confidence:.3f}")
            self.log.info(f"      - 本体验证: {'通过' if intent_result.ontology_matched else '未通过'}")
            self.log.info(f"      - 提取参数: {intent_result.parameters}")
            
            # 6. 构建完整上下文
            self.log.info("[6/10] 构建完整上下文...")
            full_ctx = await self._build_full_context(
                session_id, request.user_id, intent_result, resolved_query
            )
            
            self.log.info(f"[6/10] 上下文构建完成")
            self.log.info(f"      - 业务实体: {list(full_ctx.business.entity_states.keys())}")
            self.log.info(f"      - 本体知识: {len(full_ctx.domain.ontology_context)}条")
            self.log.info(f"      - 业务约束: {len(full_ctx.domain.constraint_context)}条")
            self.log.info(f"      - RAG上下文长度: {len(full_ctx.rag_context)}字符")
            self.log.info(f"      - 记忆上下文长度: {len(full_ctx.memory_context)}字符")
            
            # 7. 创建任务
            self.log.info("[7/10] 创建任务...")
            tasks = await self._create_tasks(
                session_id, intent_result, full_ctx, request.user_id
            )
            
            self.log.info(f"[7/10] 任务创建完成: {len(tasks)}个任务")
            for task in tasks:
                self.log.info(f"      - {task.task_id}: {task.intent} ({task.task_type})")
            
            # 8. 执行任务（同步执行简化版）
            self.log.info("[8/10] 执行任务...")
            execution_result = await self._execute_tasks(
                tasks, resolved_query, full_ctx
            )
            
            self.log.info(f"[8/10] 任务执行完成")
            self.log.info(f"      - 响应长度: {len(execution_result.get('response', ''))}字符")
            self.log.info(f"      - 执行时间: {execution_result.get('execution_time_ms', 0)}ms")
            
            # 9. 更新对话历史
            self.log.info("[9/10] 更新对话历史...")
            await self.context_manager.update_dialogue_history(
                session_id, request.user_id,
                request.query, execution_result.get("response", ""),
                intent_result.primary_intent
            )
            self.log.info("[9/10] 对话历史更新完成")
            
            # 9.5 保存长期记忆
            self.log.info(f"[9.5/10] 保存长期记忆... UserID: {request.user_id} (Type: {type(request.user_id)})")
            if self.memory_service:
                try:
                    # Ensure user_id is int
                    uid = int(request.user_id) if str(request.user_id).isdigit() else 0
                    
                    err, doc_id = await asyncio.to_thread(
                        self.memory_service.add_memory,
                        uid,
                        request.query,
                        execution_result.get("response", "")
                    )
                    if err == ErrorCode.SUCCESS:
                        self.log.info(f"[9.5/10] 长期记忆保存成功, DocID: {doc_id}")
                    else:
                        self.log.warning(f"[9.5/10] 长期记忆保存失败: {err}")
                except Exception as e:
                    self.log.warning(f"[9.5/10] 长期记忆保存异常: {e}")
            else:
                self.log.warning("[9.5/10] MemoryService未初始化，跳过记忆保存")
            
            # 10. 构造响应
            self.log.info("[10/10] 构造响应...")
            response = CoordinateResponse(
                session_id=session_id,
                intent=intent_result,
                tasks=tasks,
                response=f"【深度思考模式】\n\n{execution_result.get('response', '')}",
                context_summary={
                    "has_business_context": bool(full_ctx.business.entity_states),
                    "has_domain_context": bool(full_ctx.domain.ontology_context),
                    "history_turns": len(session_ctx.dialogue_history),
                    "mode": "deep_thinking",
                    "thinking": True
                }
            )
            
            self.log.info("=" * 60)
            self.log.info("【协调流程完成】")
            self.log.info("=" * 60)
            
            return ErrorCode.SUCCESS, response
            
        except Exception as e:
            self.log.error(f"【协调流程异常】{e}", exc_info=True)
            return ErrorCode.SYSTEM_ERROR, None
    
    async def _neo4j_intent_verification(
        self,
        ft_candidates: List[Dict[str, Any]],
        query: str,
        user_id: int
    ) -> IntentRecognitionResult:
        """
        Neo4j第二阶段：本体验证意图
        
        流程：
        1. 验证FastText候选意图的可行性
        2. 提取关键参数
        3. 验证业务约束
        """
        try:
            if not ft_candidates:
                return IntentRecognitionResult(
                    primary_intent="general_chat",
                    confidence=0.5,
                    candidates=[],
                    parameters={},
                    reasoning="No candidates from FastText",
                    ontology_matched=False
                )
            
            primary_candidate = ft_candidates[0]
            intent = primary_candidate["intent"]
            confidence = primary_candidate["confidence"]
            
            # 验证意图在本体中的存在性
            ontology_valid = False
            extracted_params = {}
            
            if self._neo4j:
                try:
                    # 查询本体验证意图
                    cypher = """
                    MATCH (i:Intent {name: $intent})
                    OPTIONAL MATCH (i)-[:REQUIRES]->(p:Parameter)
                    RETURN i.name as intent, i.description as desc, 
                           collect(p.name) as required_params
                    """
                    err, result = await asyncio.to_thread(
                        self._neo4j.execute_query, cypher, {"intent": intent}
                    )
                    
                    if err == ErrorCode.SUCCESS and result:
                        ontology_valid = True
                        # 提取必需的参数
                        required_params = result[0].get("required_params", [])
                        
                        # 从查询中提取参数值
                        for param in required_params:
                            value = self._extract_parameter(query, param)
                            if value:
                                extracted_params[param] = value
                    
                except Exception as e:
                    self.log.warning(f"Neo4j intent verification failed: {e}")
            
            # 构建最终结果
            result = IntentRecognitionResult(
                primary_intent=intent,
                confidence=confidence if ontology_valid else confidence * 0.8,
                candidates=ft_candidates,
                parameters=extracted_params,
                reasoning=f"FastText分类+Neo4j验证" if ontology_valid else "FastText分类（本体验证失败）",
                ontology_matched=ontology_valid
            )
            
            return result
            
        except Exception as e:
            self.log.error(f"_neo4j_intent_verification failed: {e}")
            return IntentRecognitionResult(
                primary_intent=ft_candidates[0]["intent"] if ft_candidates else "general_chat",
                confidence=0.5,
                candidates=ft_candidates,
                parameters={},
                reasoning=f"Error: {str(e)}",
                ontology_matched=False
            )
    
    def _extract_parameter(self, query: str, param_name: str) -> Optional[str]:
        """从查询中提取参数值"""
        # 车牌号提取
        if param_name in ["plate_number", "license_plate", "车牌"]:
            pattern = r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]'
            matches = re.findall(pattern, query)
            return matches[0] if matches else None
        
        # 时间提取
        if param_name in ["time", "duration", "时间"]:
            patterns = [
                r'(\d+)\s*小时',
                r'(\d+)\s*分钟',
                r'(\d{1,2}:\d{2})'
            ]
            for pattern in patterns:
                match = re.search(pattern, query)
                if match:
                    return match.group(0)
        
        # 数字提取
        if param_name in ["spot_id", "count", "number"]:
            numbers = re.findall(r'\d+', query)
            return numbers[0] if numbers else None
        
        return None
    
    async def _build_full_context(
        self,
        session_id: str,
        user_id: int,
        intent_result: IntentRecognitionResult,
        query: str
    ) -> FullContext:
        """构建完整上下文（三级上下文）"""
        try:
            # 1. 会话级上下文（已加载）
            err, session_ctx = await self.context_manager.load_session_context(
                session_id, user_id
            )
            
            # 2. 业务级上下文
            err, business_ctx = await self.context_manager.get_business_context(
                user_id,
                intent_result.primary_intent,
                intent_result.parameters
            )
            
            # 3. 领域知识级上下文
            err, domain_ctx = await self.context_manager.get_domain_knowledge_context(
                intent_result.primary_intent,
                intent_result.parameters,
                query
            )
            
            # 4. RAG上下文
            rag_ctx = await self._get_rag_context(query, user_id)
            
            # 5. 记忆上下文
            memory_ctx = await self._get_memory_context(query, user_id)
            
            full_ctx = FullContext(
                session=session_ctx,
                business=business_ctx,
                domain=domain_ctx,
                rag_context=rag_ctx,
                memory_context=memory_ctx
            )
            
            return full_ctx
            
        except Exception as e:
            self.log.error(f"_build_full_context failed: {e}")
            return FullContext(
                session=SessionContext(session_id=session_id, user_id=user_id),
                business={},
                domain={}
            )
    
    async def _create_tasks(
        self,
        session_id: str,
        intent_result: IntentRecognitionResult,
        full_ctx: FullContext,
        user_id: int
    ) -> List[TaskInfo]:
        """根据意图创建任务"""
        tasks = []
        
        try:
            intent = intent_result.primary_intent
            
            # 主任务
            err, main_task = await self.task_manager.create_task(
                session_id=session_id,
                intent=intent,
                task_type="primary",
                parameters=intent_result.parameters,
                user_id=user_id
            )
            
            if err == ErrorCode.SUCCESS and main_task:
                tasks.append(main_task)
            
            # 根据意图创建子任务
            if intent == "city_parking" and "plate_number" in intent_result.parameters:
                err, sub_task = await self.task_manager.create_task(
                    session_id=session_id,
                    intent="vehicle_query",
                    task_type="sub",
                    parameters={"plate_number": intent_result.parameters["plate_number"]},
                    user_id=user_id
                )
                if err == ErrorCode.SUCCESS and sub_task:
                    tasks.append(sub_task)
            
            return tasks
            
        except Exception as e:
            self.log.error(f"_create_tasks failed: {e}")
            return tasks
    
    async def _execute_tasks(
        self,
        tasks: List[TaskInfo],
        query: str,
        full_ctx: FullContext
    ) -> Dict[str, Any]:
        """执行任务并返回结果"""
        try:
            if not tasks:
                return {"response": "未创建任何任务"}
            
            main_task = tasks[0]
            intent = main_task.intent
            
            agent = self.intent_agent_map.get(intent)
            
            if not agent:
                return {"response": f"未找到处理意图 '{intent}' 的智能体"}
            
            await self.task_manager.update_task_status(
                main_task.task_id, TaskStatus.RUNNING
            )
            
            context_text = self._format_context_for_agent(full_ctx)
            # 从上下文中获取用户ID
            user_id = full_ctx.session.user_id if full_ctx.session else 0
            system_prompt = await self._get_agent_system_prompt(intent, user_id)
            
            # 打印完整的Prompt
            self.log.info("=" * 60)
            self.log.info("【LLM Prompt - 系统提示词】")
            self.log.info("=" * 60)
            self.log.info(system_prompt[:500] if len(system_prompt) > 500 else system_prompt)
            if len(system_prompt) > 500:
                self.log.info(f"... (系统提示词总长: {len(system_prompt)} 字符)")
            
            self.log.info("=" * 60)
            self.log.info("【LLM Prompt - 上下文信息】")
            self.log.info("=" * 60)
            self.log.info(context_text[:800] if len(context_text) > 800 else context_text)
            if len(context_text) > 800:
                self.log.info(f"... (上下文总长: {len(context_text)} 字符)")
            
            self.log.info("=" * 60)
            self.log.info("【LLM Prompt - 用户查询】")
            self.log.info("=" * 60)
            self.log.info(query)
            self.log.info("=" * 60)
            
            start_time = datetime.now()
            response_chunks = []
            
            try:
                async for chunk in agent.generate_plan(query, context_text, system_prompt):
                    response_chunks.append(chunk)
                
                response = "".join(response_chunks)
                
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                await self.task_manager.update_task_status(
                    main_task.task_id,
                    TaskStatus.COMPLETED,
                    result={"response": response},
                    execution_time_ms=execution_time
                )
                
                return {
                    "response": response,
                    "execution_time_ms": execution_time,
                    "tasks_completed": 1
                }
                
            except Exception as e:
                await self.task_manager.update_task_status(
                    main_task.task_id,
                    TaskStatus.FAILED,
                    error_message=str(e)
                )
                
                return {
                    "response": f"任务执行失败: {str(e)}",
                    "error": str(e)
                }
            
        except Exception as e:
            self.log.error(f"_execute_tasks failed: {e}")
            return {"response": f"执行错误: {str(e)}"}
    
    def _format_context_for_agent(self, full_ctx: FullContext) -> str:
        """格式化上下文供智能体使用"""
        context_parts = []
        
        if full_ctx.business.entity_states:
            context_parts.append("【实体状态】")
            for entity_type, state in full_ctx.business.entity_states.items():
                context_parts.append(f"  {entity_type}: {state}")
        
        if full_ctx.domain.ontology_context:
            context_parts.append("\n【本体知识】")
            for ctx in full_ctx.domain.ontology_context[:3]:
                context_parts.append(f"  - {ctx.get('type')}: {ctx.get('data', {})}")
        
        if full_ctx.domain.constraint_context:
            context_parts.append("\n【业务约束】")
            for constraint in full_ctx.domain.constraint_context[:5]:
                context_parts.append(f"  - {constraint}")
        
        if full_ctx.rag_context:
            context_parts.append(f"\n【知识库参考】\n{full_ctx.rag_context}")
        
        if full_ctx.memory_context:
            context_parts.append(f"\n【历史记忆】\n{full_ctx.memory_context}")
        
        return "\n".join(context_parts)
    
    async def _get_agent_system_prompt(self, intent: str, user_id: int = 0) -> str:
        """
        获取智能体的系统提示词
        
        Args:
            intent: 意图类型
            user_id: 用户ID，用于获取用户自定义的prompt
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.prompt_service:
            try:
                app_type = "agent-planning"
                if intent in ["steward", "monitor", "alert", "patrol"]:
                    app_type = "steward-agent"
                
                self.log.info(f"【获取Agent Prompt】用户ID: {user_id}, 应用类型: {app_type}, 时间: {current_time}")
                
                err, prompt_val = await asyncio.to_thread(
                    self.prompt_service.get_prompt_constant,
                    user_id, app_type, "system_prompt", current_time
                )
                if err == ErrorCode.SUCCESS and prompt_val:
                    self.log.info(f"【获取Agent Prompt】成功获取用户自定义prompt，长度: {len(prompt_val)} 字符")
                    return prompt_val
                else:
                    self.log.info(f"【获取Agent Prompt】未找到用户自定义prompt，使用默认值")
            except Exception as e:
                self.log.warning(f"【获取Agent Prompt】获取失败: {e}")
        
        default_prompts = {
            "city_parking": (
                "你是城市停车管理智能体。基于用户请求和提供的上下文，"
                "生成详细的停车管理方案或分析。上下文包含实体状态、知识库信息和历史记忆。"
            ),
            "steward": (
                "你是管家功能模块智能体。基于用户请求和提供的上下文，"
                "提供监控、告警、巡逻等功能的执行方案。"
            )
        }
        
        return default_prompts.get(intent, "你是一个智能助手，请基于上下文回答用户问题。")
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取会话状态"""
        try:
            err, tasks = await self.task_manager.get_session_tasks(session_id)
            
            active = len([t for t in tasks if t.status == TaskStatus.RUNNING])
            completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
            failed = len([t for t in tasks if t.status == TaskStatus.FAILED])
            
            return {
                "session_id": session_id,
                "total_tasks": len(tasks),
                "active_tasks": active,
                "completed_tasks": completed,
                "failed_tasks": failed,
                "tasks": [t.model_dump() for t in tasks]
            }
            
        except Exception as e:
            self.log.error(f"get_session_status failed: {e}")
            return {"error": str(e)}

    async def aggregate_results(self, session_id: str) -> Dict[str, Any]:
        """汇总会话所有任务的结果"""
        try:
            err, aggregated = await self.task_manager.aggregate_results(session_id)
            if err != ErrorCode.SUCCESS:
                return {"error": "Failed to aggregate results"}
            return aggregated
        except Exception as e:
            self.log.error(f"aggregate_results failed: {e}")
            return {"error": str(e)}

    async def _simple_flow(
        self,
        request: CoordinateRequest
    ) -> Tuple[ErrorCode, CoordinateResponse]:
        """
        简化流程（非深度思考模式）：
        1. 意图识别
        2. 读取记忆
        3. RAG检索作为上下文
        4. 直接发送给LLM
        5. 保存记忆
        """
        try:
            self.log.info("=" * 60)
            self.log.info(f"【简化流程开始】用户ID: {request.user_id}, 查询: '{request.query[:50]}...'")
            self.log.info("=" * 60)
            
            # 1. 意图识别
            self.log.info("[简化流程 1/5] 意图识别...")
            intent_data = await self.analyze_intent(request.query, request.user_id)
            intent = intent_data.get("intent", "general_chat")
            intent_params = intent_data.get("parameters", {})
            
            self.log.info(f"[简化流程 1/5] 识别意图: {intent}")
            self.log.info(f"[简化流程 1/5] 槽位信息:")
            if intent_params:
                for key, value in intent_params.items():
                    self.log.info(f"  - {key}: {value}")
            else:
                self.log.info("  (无槽位信息)")
            
            # 构建意图识别结果
            intent_result = IntentRecognitionResult(
                primary_intent=intent,
                confidence=intent_data.get("confidence", 0.8),
                candidates=[],
                parameters=intent_params,
                reasoning=intent_data.get("reasoning", "简化流程意图识别"),
                ontology_matched=False
            )
            
            # 2. 读取记忆
            self.log.info("[简化流程 2/5] 读取记忆...")
            memory_context = await self._get_memory_context(request.query, request.user_id)
            
            # 3. RAG检索
            self.log.info("[简化流程 3/5] RAG检索...")
            rag_context = await self._get_rag_context(request.query, request.user_id)
            
            # 4. 构建上下文并直接调用LLM
            self.log.info("[简化流程 4/5] 调用LLM生成响应...")
            
            context_parts = []
            if rag_context:
                context_parts.append(f"【知识库信息】\n{rag_context}")
            if memory_context:
                context_parts.append(f"【历史记忆】\n{memory_context}")
            
            full_context = "\n\n".join(context_parts) if context_parts else ""
            
            # 构建系统提示词
            system_prompt = (
                "你是一个智能助手。基于以下上下文信息回答用户问题。\n\n"
                f"{full_context}\n\n"
                "请直接回答用户的问题，回答要简洁准确。"
            ) if full_context else "你是一个智能助手，请直接回答用户的问题。"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.query}
            ]
            
            try:
                response = await self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=False
                )
                llm_response = response.choices[0].message.content
                self.log.info(f"[简化流程 4/5] LLM响应生成完成，长度: {len(llm_response)} 字符")
            except Exception as e:
                self.log.error(f"[简化流程 4/5] LLM调用失败: {e}")
                llm_response = f"抱歉，处理您的请求时出现问题: {str(e)}"
            
            # 5. 保存记忆
            self.log.info(f"[简化流程 5/5] 保存记忆... UserID: {request.user_id} (Type: {type(request.user_id)})")
            
            # DEBUG: Write to file
            debug_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_debug.log")
            
            if self.memory_service:
                try:
                    # Ensure user_id is int
                    uid = int(request.user_id) if str(request.user_id).isdigit() else 0
                    
                    with open(debug_log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] Attempting to save memory for user {uid}\n")
                        f.write(f"Query: {request.query}\n")
                        f.write(f"Response: {llm_response[:50]}...\n")
                    
                    err, doc_id = await asyncio.to_thread(
                        self.memory_service.add_memory,
                        uid,
                        request.query,
                        llm_response
                    )
                    
                    with open(debug_log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] Save result: {err}, DocID: {doc_id}\n")
                        
                    if err == ErrorCode.SUCCESS:
                        self.log.info(f"[简化流程 5/5] 记忆保存成功, DocID: {doc_id}")
                    else:
                        self.log.warning(f"[简化流程 5/5] 记忆保存失败: {err}")
                except Exception as e:
                    self.log.warning(f"[简化流程 5/5] 记忆保存异常: {e}")
                    with open(debug_log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] Exception: {e}\n")
            else:
                self.log.warning("[简化流程 5/5] MemoryService未初始化，跳过记忆保存")
                with open(debug_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] MemoryService is None\n")
            
            # 生成会话ID
            session_id = request.session_id or f"sess_{uuid.uuid4().hex[:16]}"
            
            # 构造响应
            response = CoordinateResponse(
                session_id=session_id,
                intent=intent_result,
                tasks=[],  # 简化流程不创建任务
                response=f"【快速回复模式】\n\n{llm_response}",
                context_summary={
                    "has_rag_context": bool(rag_context),
                    "has_memory_context": bool(memory_context),
                    "mode": "simple",
                    "thinking": False
                }
            )
            
            self.log.info("=" * 60)
            self.log.info("【简化流程完成】")
            self.log.info("=" * 60)
            
            return ErrorCode.SUCCESS, response
            
        except Exception as e:
            self.log.error(f"【简化流程异常】{e}", exc_info=True)
            return ErrorCode.SYSTEM_ERROR, None
