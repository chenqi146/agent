#!/usr/bin/env python3
"""
智能体链路追踪工具
用于追踪从协调智能体到规划智能体的完整执行过程
包含所有prompt打印、状态转换、数据流转等详细信息
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import uuid

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from openai import AsyncOpenAI


@dataclass
class ChainTraceRecord:
    """链路追踪记录"""
    trace_id: str
    timestamp: str
    component: str  # coordinator, planning_agent, llm, etc.
    stage: str  # intent_recognition, context_building, task_creation, etc.
    action: str  # 具体动作
    data: Dict[str, Any]  # 相关数据
    prompt: Optional[str] = None  # 发送给LLM的prompt
    llm_response: Optional[str] = None  # LLM的响应
    execution_time_ms: Optional[int] = None  # 执行时间
    status: str = "success"  # success, error, warning
    error_message: Optional[str] = None


class ChainTracker:
    """智能体链路追踪器"""
    
    def __init__(self):
        self.trace_id = f"trace_{uuid.uuid4().hex[:16]}"
        self.records: List[ChainTraceRecord] = []
        self.start_time = time.time()
        self.current_stage = ""
        
    def add_record(
        self,
        component: str,
        stage: str,
        action: str,
        data: Dict[str, Any],
        prompt: Optional[str] = None,
        llm_response: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ):
        """添加追踪记录"""
        record = ChainTraceRecord(
            trace_id=self.trace_id,
            timestamp=datetime.now().isoformat(),
            component=component,
            stage=stage,
            action=action,
            data=data,
            prompt=prompt,
            llm_response=llm_response,
            execution_time_ms=execution_time_ms,
            status=status,
            error_message=error_message
        )
        self.records.append(record)
        
        # 实时打印
        self._print_record(record)
    
    def _print_record(self, record: ChainTraceRecord):
        """打印追踪记录"""
        print("\n" + "="*80)
        print(f"📍 [{record.timestamp}] {record.component.upper()} - {record.stage}")
        print(f"🔧 动作: {record.action}")
        print(f"📊 状态: {record.status.upper()}")
        
        if record.execution_time_ms:
            print(f"⏱️  执行时间: {record.execution_time_ms}ms")
        
        if record.data:
            print("📋 数据:")
            for key, value in record.data.items():
                if isinstance(value, (dict, list)):
                    print(f"   {key}: {json.dumps(value, ensure_ascii=False, indent=2)[:200]}...")
                else:
                    print(f"   {key}: {value}")
        
        if record.prompt:
            print("\n🤖 发送给LLM的Prompt:")
            print("-" * 60)
            if len(record.prompt) > 1000:
                print(record.prompt[:500])
                print(f"... (中间部分省略，总长 {len(record.prompt)} 字符) ...")
                print(record.prompt[-300:])
            else:
                print(record.prompt)
            print("-" * 60)
        
        if record.llm_response:
            print("\n💬 LLM响应:")
            print("-" * 60)
            if len(record.llm_response) > 1000:
                print(record.llm_response[:500])
                print(f"... (中间部分省略，总长 {len(record.llm_response)} 字符) ...")
                print(record.llm_response[-300:])
            else:
                print(record.llm_response)
            print("-" * 60)
        
        if record.error_message:
            print(f"❌ 错误信息: {record.error_message}")
        
        print("="*80)
    
    def print_summary(self):
        """打印追踪摘要"""
        total_time = int((time.time() - self.start_time) * 1000)
        
        print("\n" + "🎯" * 40)
        print(f"📊 链路追踪摘要 - Trace ID: {self.trace_id}")
        print(f"⏱️  总执行时间: {total_time}ms")
        print(f"📝 总记录数: {len(self.records)}")
        
        # 按组件统计
        component_stats = {}
        for record in self.records:
            component_stats[record.component] = component_stats.get(record.component, 0) + 1
        
        print("\n📈 组件调用统计:")
        for component, count in component_stats.items():
            print(f"   {component}: {count} 次")
        
        # 按阶段统计
        stage_stats = {}
        for record in self.records:
            stage_stats[record.stage] = stage_stats.get(record.stage, 0) + 1
        
        print("\n🔄 阶段执行统计:")
        for stage, count in stage_stats.items():
            print(f"   {stage}: {count} 次")
        
        # 错误统计
        error_count = sum(1 for r in self.records if r.status != "success")
        if error_count > 0:
            print(f"\n❌ 错误/警告: {error_count} 个")
        
        print("🎯" * 40)
    
    def save_to_file(self, filename: Optional[str] = None):
        """保存追踪记录到文件"""
        if not filename:
            filename = f"chain_trace_{self.trace_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "trace_id": self.trace_id,
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "records": [asdict(record) for record in self.records]
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 追踪记录已保存到: {filename}")


class TrackedAgentCoordinator:
    """带链路追踪的协调智能体包装器"""
    
    def __init__(self, original_coordinator, tracker: ChainTracker):
        self.original = original_coordinator
        self.tracker = tracker
        
    async def coordinate(self, request):
        """带追踪的协调方法"""
        start_time = time.time()
        
        try:
            # 1. 记录请求开始
            self.tracker.add_record(
                component="coordinator",
                stage="request_start",
                action="coordinate_request",
                data={
                    "user_id": request.user_id,
                    "query": request.query,
                    "session_id": request.session_id,
                    "thinking": request.thinking
                }
            )
            
            # 2. 意图识别（带详细追踪）
            intent_result = await self._tracked_intent_recognition(request)
            
            # 3. 上下文构建（带详细追踪）
            context_result = await self._tracked_context_building(request, intent_result)
            
            # 4. 任务创建与分发（带详细追踪）
            task_result = await self._tracked_task_creation(request, intent_result, context_result)
            
            # 5. 执行与汇总（带详细追踪）
            final_result = await self._tracked_execution(request, task_result)
            
            # 6. 记录完成
            execution_time = int((time.time() - start_time) * 1000)
            self.tracker.add_record(
                component="coordinator",
                stage="request_complete",
                action="coordinate_success",
                data={
                    "total_time_ms": execution_time,
                    "final_response_length": len(final_result.get('response', '')) if final_result else 0
                },
                execution_time_ms=execution_time
            )
            
            return ErrorCode.SUCCESS, final_result
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.tracker.add_record(
                component="coordinator",
                stage="request_error",
                action="coordinate_failed",
                data={"error": str(e)},
                execution_time_ms=execution_time,
                status="error",
                error_message=str(e)
            )
            raise
    
    async def _tracked_intent_recognition(self, request):
        """带追踪的意图识别"""
        start_time = time.time()
        
        # 获取可用工具
        tools = await self.original._get_available_tools()
        
        # 构建工具描述
        tool_desc_list = []
        for t in tools:
            name = t.get("name")
            desc = t.get("description", "No description")
            schema = t.get("inputSchema") or t.get("parameters")
            tool_info = f"- '{name}': {desc}"
            if schema:
                tool_info += f" (Args: {json.dumps(schema, ensure_ascii=False)})"
            tool_desc_list.append(tool_info)
        
        tool_section = ""
        if tool_desc_list:
            tool_section = "Available Tools (use these as intents if applicable):\n" + "\n".join(tool_desc_list) + "\n"
        
        # 获取系统prompt
        system_prompt = ""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.original.prompt_service:
            err, prompt_val = await asyncio.to_thread(
                self.original.prompt_service.get_prompt_constant, 
                request.user_id, "agent-coordinator", "system_prompt", current_time
            )
            if err == ErrorCode.SUCCESS and prompt_val:
                system_prompt = prompt_val
        
        if not system_prompt:
            system_prompt = (
                "You are an Intent Recognition Agent. Analyze the user's request and determine the primary intent.\n"
                "Possible intents:\n"
                "- 'city_parking': Related to city parking management, tasks, analysis, or decision support.\n"
                "- 'steward': Related to steward functions (monitoring, alerting, auto license plate, evidence, patrol, external services).\n"
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
            # 补齐上下文
            if tool_section and "Available Tools" not in system_prompt:
                system_prompt += f"\n\n{tool_section}"
            if "intent" not in system_prompt:
                system_prompt += (
                    "\n\n输出要求：\n"
                    "Output ONLY a valid JSON object with the following structure:\n"
                    "{\n"
                    '  "intent": "intent_name",\n'
                    '  "parameters": { "key": "value" },\n'
                    '  "reasoning": "brief reason"\n'
                    "}"
                )
        
        # 记录prompt构建
        self.tracker.add_record(
            component="coordinator",
            stage="intent_recognition",
            action="build_prompt",
            data={
                "tools_count": len(tools),
                "prompt_length": len(system_prompt),
                "has_custom_prompt": bool(prompt_val if self.original.prompt_service else False)
            }
        )
        
        # 调用LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.query}
        ]
        
        try:
            response = await self.original.llm_client.chat.completions.create(
                model=self.original.model,
                messages=messages,
                stream=False,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # 记录LLM调用
            self.tracker.add_record(
                component="llm",
                stage="intent_recognition",
                action="llm_call",
                data={
                    "model": self.original.model,
                    "messages_count": len(messages),
                    "response_format": "json_object"
                },
                prompt=system_prompt + "\n\nUser: " + request.query,
                llm_response=content,
                execution_time_ms=execution_time
            )
            
            # 记录意图识别结果
            self.tracker.add_record(
                component="coordinator",
                stage="intent_recognition",
                action="intent_result",
                data={
                    "intent": result.get('intent'),
                    "parameters": result.get('parameters'),
                    "reasoning": result.get('reasoning'),
                    "confidence": result.get('confidence', 'N/A')
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.tracker.add_record(
                component="llm",
                stage="intent_recognition",
                action="llm_error",
                data={"error": str(e)},
                execution_time_ms=execution_time,
                status="error",
                error_message=str(e)
            )
            raise
    
    async def _tracked_context_building(self, request, intent_result):
        """带追踪的上下文构建"""
        start_time = time.time()
        
        # RAG检索
        rag_context = ""
        if self.original.rag_service:
            try:
                rag_context = await self.original._get_rag_context(request.query, request.user_id)
                self.tracker.add_record(
                    component="coordinator",
                    stage="context_building",
                    action="rag_retrieval",
                    data={
                        "query_length": len(request.query),
                        "rag_context_length": len(rag_context),
                        "has_rag_service": True
                    }
                )
            except Exception as e:
                self.tracker.add_record(
                    component="coordinator",
                    stage="context_building",
                    action="rag_error",
                    data={"error": str(e)},
                    status="warning",
                    error_message=str(e)
                )
        
        # 记忆检索
        memory_context = ""
        if self.original.memory_service:
            try:
                memory_context = await self.original._get_memory_context(request.query, request.user_id)
                self.tracker.add_record(
                    component="coordinator",
                    stage="context_building",
                    action="memory_retrieval",
                    data={
                        "memory_context_length": len(memory_context),
                        "has_memory_service": True
                    }
                )
            except Exception as e:
                self.tracker.add_record(
                    component="coordinator",
                    stage="context_building",
                    action="memory_error",
                    data={"error": str(e)},
                    status="warning",
                    error_message=str(e)
                )
        
        full_context = f"RAG Knowledge:\n{rag_context}\n\nMemory Context:\n{memory_context}\n"
        
        execution_time = int((time.time() - start_time) * 1000)
        self.tracker.add_record(
            component="coordinator",
            stage="context_building",
            action="context_complete",
            data={
                "rag_length": len(rag_context),
                "memory_length": len(memory_context),
                "total_length": len(full_context)
            },
            execution_time_ms=execution_time
        )
        
        return full_context
    
    async def _tracked_task_creation(self, request, intent_result, context):
        """带追踪的任务创建"""
        start_time = time.time()
        
        intent = intent_result.get("intent")
        
        # 路由到对应的智能体
        agent = None
        agent_type = None
        
        if intent == "city_parking":
            agent = self.original.city_parking_agent
            agent_type = "city_parking_agent"
        elif intent == "steward":
            agent = self.original.steward_agent
            agent_type = "steward_agent"
        
        self.tracker.add_record(
            component="coordinator",
            stage="task_routing",
            action="route_to_agent",
            data={
                "intent": intent,
                "selected_agent": agent_type,
                "agent_available": agent is not None
            }
        )
        
        if not agent:
            raise ValueError(f"No agent found for intent: {intent}")
        
        # 获取智能体特定的prompt
        agent_prompt = None
        if self.original.prompt_service:
            prompt_app_type = "agent-planning" if intent == "city_parking" else "steward-agent"
            err, prompt_val = await asyncio.to_thread(
                self.original.prompt_service.get_prompt_constant, 
                request.user_id, prompt_app_type, "system_prompt"
            )
            if err == ErrorCode.SUCCESS and prompt_val:
                agent_prompt = prompt_val
        
        execution_time = int((time.time() - start_time) * 1000)
        self.tracker.add_record(
            component="coordinator",
            stage="task_creation",
            action="agent_prepared",
            data={
                "agent_type": agent_type,
                "has_custom_prompt": agent_prompt is not None,
                "prompt_length": len(agent_prompt) if agent_prompt else 0
            },
            execution_time_ms=execution_time
        )
        
        return {
            "agent": agent,
            "agent_type": agent_type,
            "prompt": agent_prompt,
            "context": context
        }
    
    async def _tracked_execution(self, request, task_info):
        """带追踪的执行过程"""
        start_time = time.time()
        
        agent = task_info["agent"]
        agent_type = task_info["agent_type"]
        agent_prompt = task_info["prompt"]
        context = task_info["context"]
        
        # 构建完整的prompt
        full_prompt = f"""
用户查询: {request.query}

上下文信息:
{context}

请根据以上信息，为用户提供准确的回答。
"""
        
        if agent_prompt:
            full_prompt = f"{agent_prompt}\n\n{full_prompt}"
        
        self.tracker.add_record(
            component="planning_agent",
            stage="execution",
            action="prepare_prompt",
            data={
                "agent_type": agent_type,
                "prompt_length": len(full_prompt),
                "context_length": len(context)
            }
        )
        
        try:
            # 调用智能体生成响应
            response = await agent.generate_plan(request.query, context, system_prompt=agent_prompt)
            
            # 收集所有响应片段
            full_response = ""
            async for chunk in response:
                full_response += chunk
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # 记录智能体执行
            self.tracker.add_record(
                component="planning_agent",
                stage="execution",
                action="generate_response",
                data={
                    "agent_type": agent_type,
                    "response_length": len(full_response),
                    "chunk_count": full_response.count('\n') + 1
                },
                prompt=full_prompt,
                llm_response=full_response,
                execution_time_ms=execution_time
            )
            
            return {
                "response": full_response,
                "agent_type": agent_type,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.tracker.add_record(
                component="planning_agent",
                stage="execution",
                action="execution_error",
                data={
                    "agent_type": agent_type,
                    "error": str(e)
                },
                execution_time_ms=execution_time,
                status="error",
                error_message=str(e)
            )
            raise


async def trace_full_chain(coordinator, request, save_to_file: bool = True):
    """追踪完整的智能体链路"""
    
    print("🚀 开始智能体链路追踪...")
    print(f"📝 Trace ID: {tracker.trace_id}")
    print(f"👤 用户ID: {request.user_id}")
    print(f"💬 查询: {request.query}")
    print(f"🧠 深度思考: {request.thinking}")
    
    # 创建带追踪的包装器
    tracked_coordinator = TrackedAgentCoordinator(coordinator, tracker)
    
    try:
        # 执行完整的协调流程
        err, result = await tracked_coordinator.coordinate(request)
        
        # 打印最终结果摘要
        tracker.print_summary()
        
        # 保存到文件
        if save_to_file:
            tracker.save_to_file()
        
        return err, result
        
    except Exception as e:
        print(f"\n❌ 链路追踪过程中发生异常: {e}")
        tracker.print_summary()
        tracker.save_to_file()
        raise


# 示例使用代码
if __name__ == "__main__":
    # 这里需要根据实际的依赖注入来初始化
    # tracker = ChainTracker()
    # 
    # # 模拟请求
    # from interfaces.dto.coordinator_dto import CoordinateRequest
    # request = CoordinateRequest(
    #     user_id=1,
    #     query="查询停车场A今天的停车情况",
    #     session_id=None,
    #     thinking=True
    # )
    # 
    # # 执行追踪
    # asyncio.run(trace_full_chain(coordinator, request))
    pass
