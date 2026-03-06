'''
统一响应 DTO 定义
'''
from typing import Dict, Any, Optional, TypeVar, Generic
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel
import time

from infrastructure.common.error.errcode import ErrorCode, ErrorMessage


T = TypeVar('T')


class ApiResponse(GenericModel, Generic[T]):
    """
    统一 API 响应格式
    
    格式:
    {
        "code": 0,           // 错误码，0表示成功
        "message": "成功",    // 错误信息
        "data": {...},       // 响应数据
        "timestamp": 1234567890  // 时间戳
    }
    """
    code: int = Field(default=0, description="错误码，0表示成功")
    message: str = Field(default="操作成功", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="时间戳(毫秒)")
    
    class Config:
        # 允许任意类型
        arbitrary_types_allowed = True


class ApiResponseBuilder:
    """API响应构建器"""
    
    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> ApiResponse:
        """
        构建成功响应
        
        Args:
            data: 响应数据
            message: 成功消息
            
        Returns:
            ApiResponse: 统一响应对象
        """
        return ApiResponse(
            code=ErrorCode.SUCCESS.value,
            message=message,
            data=data
        )
    
    @staticmethod
    def error(
        error_code: ErrorCode,
        message: str = None,
        data: Any = None
    ) -> ApiResponse:
        """
        构建错误响应
        
        Args:
            error_code: 错误码枚举
            message: 错误消息（可选，默认使用预定义消息）
            data: 附加数据（可选）
            
        Returns:
            ApiResponse: 统一响应对象
        """
        return ApiResponse(
            code=error_code.value,
            message=message or ErrorMessage.get_message(error_code),
            data=data
        )
    
    @staticmethod
    def from_exception(e: Exception, error_code: ErrorCode = ErrorCode.INTERNAL_ERROR) -> ApiResponse:
        """
        从异常构建错误响应
        
        Args:
            e: 异常对象
            error_code: 错误码（默认内部错误）
            
        Returns:
            ApiResponse: 统一响应对象
        """
        return ApiResponse(
            code=error_code.value,
            message=str(e),
            data=None
        )


# 快捷方法
def ok(data: Any = None, message: str = "操作成功") -> ApiResponse:
    """成功响应快捷方法"""
    return ApiResponseBuilder.success(data, message)


def fail(error_code: ErrorCode, message: str = None, data: Any = None) -> ApiResponse:
    """失败响应快捷方法"""
    return ApiResponseBuilder.error(error_code, message, data)

