from typing import List, Dict, Any, AsyncGenerator
import json
from infrastructure.common.logging.logging import logger
from openai import AsyncOpenAI

@logger()
class BasePlanningAgent:
    def __init__(self, llm_client: AsyncOpenAI, model: str):
        self.llm_client = llm_client
        self.model = model

    async def generate_plan(self, query: str, context: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
        raise NotImplementedError

@logger()
class CityParkingAgent(BasePlanningAgent):
    """
    City Parking Management Agent (城市停车管理智能体)
    Type: Task Guide, Analysis & Decision Support
    """
    async def generate_plan(self, query: str, context: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
        if not system_prompt:
            system_prompt = (
                "You are a City Parking Management Agent (城市停车管理智能体). "
                "Your capabilities include: Task Guidance, Parking Analysis, and Decision Support. "
                "Based on the user request and provided context, generate a detailed plan or analysis. "
                "Context may include RAG retrieved knowledge and memory. "
                "Output in Chinese."
            )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser Request: {query}"}
        ]

        try:
            stream = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            self.log.error(f"CityParkingAgent failed: {e}")
            yield f"Error in CityParkingAgent: {str(e)}"

@logger()
class StewardAgent(BasePlanningAgent):
    """
    Steward Function Module Planning Agent (管家功能模块规划智能体)
    Capabilities: Real-time Monitoring & Alerting, Auto License Plate & Evidence, Data Analysis, Patrol Scheduling, External Services.
    """
    async def generate_plan(self, query: str, context: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
        if not system_prompt:
            system_prompt = (
                "You are a Steward Function Module Planning Agent (管家功能模块规划智能体). "
                "Your capabilities include: Real-time Monitoring & Alerting, Automatic License Plate Recognition & Evidence Chain Generation, "
                "Data Analysis & Decision Support, Patrol Scheduling, and External Interaction & Services. "
                "Based on the user request and provided context, generate a detailed operational plan or response. "
                "Context may include RAG retrieved knowledge and memory. "
                "Output in Chinese."
            )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser Request: {query}"}
        ]

        try:
            stream = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            self.log.error(f"StewardAgent failed: {e}")
            yield f"Error in StewardAgent: {str(e)}"

@logger()
class ParkingBillingAgent(BasePlanningAgent):
    """
    Normal Parking Billing Event Planning Agent (正常停车计费事件规划智能体)
    Capabilities: Parking Fee Calculation, Billing Rules Management, Payment Processing, Invoice Generation.
    """
    async def generate_plan(self, query: str, context: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
        if not system_prompt:
            system_prompt = (
                "You are a Normal Parking Billing Event Planning Agent (正常停车计费事件规划智能体). "
                "Your capabilities include: Parking Fee Calculation, Billing Rules Management, Payment Processing, and Invoice Generation. "
                "Based on the user request and provided context, generate a detailed billing plan or resolution. "
                "Context may include RAG retrieved knowledge and memory. "
                "Output in Chinese."
            )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser Request: {query}"}
        ]

        try:
            stream = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            self.log.error(f"ParkingBillingAgent failed: {e}")
            yield f"Error in ParkingBillingAgent: {str(e)}"

@logger()
class ParkingOperationAgent(BasePlanningAgent):
    """
    Parking Operation Planning Agent (停车运营规划智能体)
    Capabilities: Operation Strategy, Resource Allocation, Revenue Analysis, Traffic Flow Optimization.
    """
    async def generate_plan(self, query: str, context: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
        if not system_prompt:
            system_prompt = (
                "You are a Parking Operation Planning Agent (停车运营规划智能体). "
                "Your capabilities include: Operation Strategy Formulation, Resource Allocation, Revenue Analysis, and Traffic Flow Optimization. "
                "Based on the user request and provided context, generate a detailed operation plan or analysis. "
                "Context may include RAG retrieved knowledge and memory. "
                "Output in Chinese."
            )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser Request: {query}"}
        ]

        try:
            stream = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            self.log.error(f"ParkingOperationAgent failed: {e}")
            yield f"Error in ParkingOperationAgent: {str(e)}"

@logger()
class ArrearsCollectionAgent(BasePlanningAgent):
    """
    Arrears Collection Agent (欠费追缴智能体)
    Capabilities: Debt Analysis, Collection Strategy, User Notification, Legal Process Support.
    """
    async def generate_plan(self, query: str, context: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
        if not system_prompt:
            system_prompt = (
                "You are an Arrears Collection Agent (欠费追缴智能体). "
                "Your capabilities include: Debt Analysis, Collection Strategy Formulation, User Notification, and Legal Process Support. "
                "Based on the user request and provided context, generate a detailed collection plan or strategy. "
                "Context may include RAG retrieved knowledge and memory. "
                "Output in Chinese."
            )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser Request: {query}"}
        ]

        try:
            stream = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            self.log.error(f"ArrearsCollectionAgent failed: {e}")
            yield f"Error in ArrearsCollectionAgent: {str(e)}"
