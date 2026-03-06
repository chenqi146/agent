'''
VLM Assembler - DTO 转换器
负责 Domain 模型与 DTO 之间的转换
'''
import uuid
import time
from typing import List, Dict, Any, Optional, Union

from domain.service.vlm_service import VisionInferenceResult
from infrastructure.llm.llm_work_info import ResourceInfo, HealthStatus

from interfaces.dto.vlm_dto import (
    VisionMessage, VisionChoice, VisionCompletionResponse,
    VisionCompletionChunk, VisionChunkChoice, DeltaMessage,
    ImageAnalyzeResponse, Usage, Role, ContentItem
)


class VLMAssembler:
    """VLM DTO 转换器"""
    
    @staticmethod
    def vision_result_to_response(
        result: VisionInferenceResult,
        model_name: str
    ) -> VisionCompletionResponse:
        """
        将视觉推理结果转换为 OpenAI 格式响应
        
        Args:
            result: 视觉推理结果
            model_name: 模型名称
            
        Returns:
            VisionCompletionResponse: OpenAI 格式响应
        """
        message = VisionMessage(
            role=Role.ASSISTANT,
            content=result.generated_text
        )
        
        choice = VisionChoice(
            index=0,
            message=message,
            finish_reason=result.finish_reason
        )
        
        usage = Usage(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens
        )
        
        return VisionCompletionResponse(
            id=f"chatcmpl-{result.request_id or uuid.uuid4().hex[:24]}",
            model=model_name,
            choices=[choice],
            usage=usage
        )
    
    @staticmethod
    def vision_result_to_analyze_response(
        result: VisionInferenceResult
    ) -> ImageAnalyzeResponse:
        """
        将视觉推理结果转换为图像分析响应
        
        Args:
            result: 视觉推理结果
            
        Returns:
            ImageAnalyzeResponse: 图像分析响应
        """
        return ImageAnalyzeResponse(
            description=result.generated_text,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=result.latency_ms
        )
    
    @staticmethod
    def create_vision_chunk(
        chunk_id: str,
        model_name: str,
        role: Optional[str] = None,
        content: Optional[str] = None,
        finish_reason: Optional[str] = None
    ) -> VisionCompletionChunk:
        """
        创建流式响应块
        
        Args:
            chunk_id: 块ID
            model_name: 模型名称
            role: 消息角色
            content: 消息内容
            finish_reason: 完成原因
            
        Returns:
            VisionCompletionChunk: 流式响应块
        """
        delta = DeltaMessage(
            role=role,
            content=content
        )
        
        choice = VisionChunkChoice(
            index=0,
            delta=delta,
            finish_reason=finish_reason
        )
        
        return VisionCompletionChunk(
            id=chunk_id,
            model=model_name,
            choices=[choice]
        )
    
    @staticmethod
    def messages_to_dict_list(messages: List[VisionMessage]) -> List[Dict[str, Any]]:
        """
        将 DTO 消息列表转换为字典列表
        
        Args:
            messages: VisionMessage 列表
            
        Returns:
            List[Dict]: 字典格式的消息列表
        """
        result = []
        for msg in messages:
            content = msg.content
            
            # 如果 content 是列表（多模态内容），需要特殊处理
            if isinstance(content, list):
                content_list = []
                for item in content:
                    if hasattr(item, 'model_dump'):
                        content_list.append(item.model_dump())
                    elif isinstance(item, dict):
                        content_list.append(item)
                content = content_list
            
            result.append({
                "role": msg.role.value if hasattr(msg.role, 'value') else msg.role,
                "content": content
            })
        
        return result
    
    @staticmethod
    def normalize_stop_words(stop: Optional[Union[str, List[str]]]) -> Optional[List[str]]:
        """
        标准化停止词
        
        Args:
            stop: 停止词（单个字符串或列表）
            
        Returns:
            List[str] or None: 标准化后的停止词列表
        """
        if stop is None:
            return None
        if isinstance(stop, str):
            return [stop]
        return stop
    
    @staticmethod
    def resource_info_to_dto(resource: ResourceInfo) -> Dict[str, Any]:
        """
        将资源信息转换为 DTO
        
        Args:
            resource: ResourceInfo 对象
            
        Returns:
            Dict: 资源信息字典
        """
        return {
            "gpu_id": resource.gpu_id,
            "gpu_name": resource.gpu_name,
            "total_memory_mb": round(resource.total_memory_mb, 2),
            "used_memory_mb": round(resource.used_memory_mb, 2),
            "free_memory_mb": round(resource.free_memory_mb, 2),
            "memory_utilization": round(resource.memory_utilization * 100, 2),
            "gpu_utilization": round(resource.gpu_utilization * 100, 2),
            "temperature": resource.temperature
        }
    
    @staticmethod
    def health_status_to_response(
        health: HealthStatus,
        active_requests: int = 0
    ) -> Dict[str, Any]:
        """
        将健康状态转换为响应格式
        
        Args:
            health: HealthStatus 对象
            active_requests: 当前活跃请求数
            
        Returns:
            Dict: 健康状态响应
        """
        return {
            "is_healthy": health.is_healthy,
            "model_status": health.model_status.value if hasattr(health.model_status, 'value') else str(health.model_status),
            "model_name": health.model_name,
            "model_type": "vlm",
            "uptime_seconds": round(health.uptime_seconds, 2),
            "total_requests": health.total_requests,
            "successful_requests": health.successful_requests,
            "failed_requests": health.failed_requests,
            "active_requests": active_requests,
            "avg_latency_ms": round(health.avg_latency_ms, 2),
            "error_message": health.error_message,
            "gpu_resources": [VLMAssembler.resource_info_to_dto(r) for r in health.gpu_resources] if health.gpu_resources else []
        }

