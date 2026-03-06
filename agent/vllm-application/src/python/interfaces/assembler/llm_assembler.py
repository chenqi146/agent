'''
LLM DTO 转换器
负责 Domain 实体与 DTO 之间的转换
'''
from typing import List, Dict, Any, Optional
import time
import uuid

from infrastructure.llm.llm_work_info import InferenceResult, ResourceInfo, HealthStatus
from interfaces.dto.llm_dto import (
    # 请求
    ChatMessage, CompletionRequest, ChatCompletionRequest,
    # 响应
    Role, Usage, CompletionChoice, ChatCompletionChoice,
    CompletionResponse, ChatCompletionResponse,
    # 流式
    DeltaMessage, ChatCompletionChunkChoice, ChatCompletionChunk,
    # 其他
    GPUResourceDTO, HealthCheckResponse, ModelInfo
)


class LLMAssembler:
    """LLM DTO 转换器"""
    
    # ==================== 请求转换 ====================
    
    @staticmethod
    def chat_messages_to_dict_list(messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """
        将 ChatMessage 列表转换为字典列表（供 LLMService.chat 使用）
        
        Args:
            messages: ChatMessage 列表
            
        Returns:
            List[Dict[str, str]]: 字典格式的消息列表
        """
        return [{"role": msg.role.value, "content": msg.content} for msg in messages]
    
    @staticmethod
    def normalize_stop_words(stop: Optional[str | List[str]]) -> Optional[List[str]]:
        """
        标准化停止词参数
        
        Args:
            stop: 停止词（字符串或列表）
            
        Returns:
            Optional[List[str]]: 停止词列表
        """
        if stop is None:
            return None
        if isinstance(stop, str):
            return [stop]
        return stop
    
    # ==================== 响应转换 ====================
    
    @staticmethod
    def inference_result_to_completion_response(
        result: InferenceResult,
        model_name: str = ""
    ) -> CompletionResponse:
        """
        将推理结果转换为补全响应
        
        Args:
            result: 推理结果
            model_name: 模型名称
            
        Returns:
            CompletionResponse: OpenAI 格式的补全响应
        """
        return CompletionResponse(
            id=f"cmpl-{result.request_id}",
            model=model_name,
            choices=[
                CompletionChoice(
                    index=0,
                    text=result.generated_text,
                    finish_reason=result.finish_reason
                )
            ],
            usage=Usage(
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens
            )
        )
    
    @staticmethod
    def inference_results_to_completion_response(
        results: List[InferenceResult],
        model_name: str = ""
    ) -> CompletionResponse:
        """
        将批量推理结果转换为补全响应
        
        Args:
            results: 推理结果列表
            model_name: 模型名称
            
        Returns:
            CompletionResponse: OpenAI 格式的补全响应
        """
        choices = [
            CompletionChoice(
                index=i,
                text=result.generated_text,
                finish_reason=result.finish_reason
            )
            for i, result in enumerate(results)
        ]
        
        # 汇总 token 统计
        total_prompt_tokens = sum(r.prompt_tokens for r in results)
        total_completion_tokens = sum(r.completion_tokens for r in results)
        
        return CompletionResponse(
            id=f"cmpl-{results[0].request_id}" if results else f"cmpl-{uuid.uuid4().hex[:24]}",
            model=model_name,
            choices=choices,
            usage=Usage(
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
                total_tokens=total_prompt_tokens + total_completion_tokens
            )
        )
    
    @staticmethod
    def inference_result_to_chat_completion_response(
        result: InferenceResult,
        model_name: str = ""
    ) -> ChatCompletionResponse:
        """
        将推理结果转换为对话补全响应
        
        Args:
            result: 推理结果
            model_name: 模型名称
            
        Returns:
            ChatCompletionResponse: OpenAI 格式的对话补全响应
        """
        return ChatCompletionResponse(
            id=f"chatcmpl-{result.request_id}",
            model=model_name,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role=Role.ASSISTANT,
                        content=result.generated_text
                    ),
                    finish_reason=result.finish_reason
                )
            ],
            usage=Usage(
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens
            )
        )
    
    # ==================== 流式响应转换 ====================
    
    @staticmethod
    def create_chat_completion_chunk(
        chunk_id: str,
        model_name: str,
        content: Optional[str] = None,
        role: Optional[str] = None,
        finish_reason: Optional[str] = None
    ) -> ChatCompletionChunk:
        """
        创建流式对话补全响应块
        
        Args:
            chunk_id: 块ID
            model_name: 模型名称
            content: 内容增量
            role: 角色（首次发送时设置）
            finish_reason: 完成原因（最后发送时设置）
            
        Returns:
            ChatCompletionChunk: 流式响应块
        """
        return ChatCompletionChunk(
            id=chunk_id,
            model=model_name,
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=DeltaMessage(
                        role=role,
                        content=content
                    ),
                    finish_reason=finish_reason
                )
            ]
        )
    
    # ==================== 健康状态转换 ====================
    
    @staticmethod
    def resource_info_to_dto(resource: ResourceInfo) -> GPUResourceDTO:
        """
        将 ResourceInfo 转换为 DTO
        
        Args:
            resource: GPU资源信息
            
        Returns:
            GPUResourceDTO: GPU资源DTO
        """
        return GPUResourceDTO(
            gpu_id=resource.gpu_id,
            gpu_name=resource.gpu_name,
            total_memory_mb=resource.total_memory_mb,
            used_memory_mb=resource.used_memory_mb,
            free_memory_mb=resource.free_memory_mb,
            memory_utilization=resource.memory_utilization,
            gpu_utilization=resource.gpu_utilization,
            temperature=resource.temperature
        )
    
    @staticmethod
    def health_status_to_response(
        health: HealthStatus,
        active_requests: int = 0
    ) -> HealthCheckResponse:
        """
        将健康状态转换为响应 DTO
        
        Args:
            health: 健康状态
            active_requests: 当前活跃请求数
            
        Returns:
            HealthCheckResponse: 健康检查响应
        """
        gpu_resources = [
            LLMAssembler.resource_info_to_dto(r) 
            for r in health.gpu_resources
        ]
        
        return HealthCheckResponse(
            is_healthy=health.is_healthy,
            model_status=health.model_status.value,
            model_name=health.model_name,
            uptime_seconds=health.uptime_seconds,
            total_requests=health.total_requests,
            successful_requests=health.successful_requests,
            failed_requests=health.failed_requests,
            active_requests=active_requests,
            avg_latency_ms=health.avg_latency_ms,
            gpu_resources=gpu_resources,
            error_message=health.error_message
        )
    
    @staticmethod
    def model_info_to_dto(model_path: str, model_info: Dict[str, Any]) -> ModelInfo:
        """
        将模型信息转换为 DTO
        
        Args:
            model_path: 模型路径
            model_info: 模型信息字典
            
        Returns:
            ModelInfo: 模型信息DTO
        """
        # 从路径提取模型名称
        model_name = model_path.split("/")[-1] if "/" in model_path else model_path
        
        return ModelInfo(
            id=model_name,
            owned_by="local"
        )

