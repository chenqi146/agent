#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP API响应格式定义
"""

from datetime import datetime
from typing import Dict, Any, Optional
from .errcode import ErrorCode, ErrorMessage


class ApiResponse:
    """API响应格式类"""
    
    @staticmethod
    def success(data: Any = None, message: str = None) -> Dict[str, Any]:
        """成功响应"""
        return {
            "success": True,
            "code": ErrorCode.SUCCESS.value,
            "message": message or ErrorMessage.get_message(ErrorCode.SUCCESS),
            "data": data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @staticmethod
    def error(code: int, message: str = None, details: Any = None) -> Dict[str, Any]:
        """错误响应"""
        return {
            "success": False,
            "code": code,
            "message": message or ErrorMessage.get_message_by_code(code),
            "data": details,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @staticmethod
    def error_by_enum(error_code: ErrorCode, message: str = None, details: Any = None) -> Dict[str, Any]:
        """通过错误码枚举创建错误响应"""
        return ApiResponse.error(error_code.value, message, details)
    
    @staticmethod
    def invalid_request(message: str = None, details: Any = None) -> Dict[str, Any]:
        """无效请求响应"""
        return ApiResponse.error_by_enum(ErrorCode.INVALID_PARAMETER, message, details)
    
    @staticmethod
    def missing_parameter(param_name: str = None, details: Any = None) -> Dict[str, Any]:
        """缺少参数响应"""
        message = f"缺少必需参数: {param_name}" if param_name else None
        return ApiResponse.error_by_enum(ErrorCode.MISSING_PARAMETER, message, details)
    
    @staticmethod
    def model_not_found(model_name: str = None, details: Any = None) -> Dict[str, Any]:
        """模型未找到响应"""
        message = f"模型未找到: {model_name}" if model_name else None
        return ApiResponse.error_by_enum(ErrorCode.MODEL_NOT_FOUND, message, details)
    
    @staticmethod
    def model_start_failed(message: str = None, details: Any = None) -> Dict[str, Any]:
        """模型启动失败响应"""
        return ApiResponse.error_by_enum(ErrorCode.MODEL_INIT_FAILED, message, details)
    
    @staticmethod
    def model_stop_failed(message: str = None, details: Any = None) -> Dict[str, Any]:
        """模型停止失败响应"""
        return ApiResponse.error_by_enum(ErrorCode.OPERATION_FAILED, message, details)
    
    @staticmethod
    def internal_error(message: str = None, details: Any = None) -> Dict[str, Any]:
        """内部错误响应"""
        return ApiResponse.error_by_enum(ErrorCode.UNKNOWN_ERROR, message, details)
    
    @staticmethod
    def timeout(message: str = None, details: Any = None) -> Dict[str, Any]:
        """超时错误响应"""
        return ApiResponse.error_by_enum(ErrorCode.TIMEOUT, message, details)
    
    @staticmethod
    def service_unavailable(message: str = None, details: Any = None) -> Dict[str, Any]:
        """服务不可用响应"""
        return ApiResponse.error_by_enum(ErrorCode.SERVICE_UNAVAILABLE, message, details)
    
    @staticmethod
    def permission_denied(message: str = None, details: Any = None) -> Dict[str, Any]:
        """权限不足响应"""
        return ApiResponse.error_by_enum(ErrorCode.PERMISSION_DENIED, message, details)
    
    @staticmethod
    def resource_not_found(resource_type: str = None, details: Any = None) -> Dict[str, Any]:
        """资源未找到响应"""
        message = f"资源未找到: {resource_type}" if resource_type else None
        return ApiResponse.error_by_enum(ErrorCode.RESOURCE_NOT_FOUND, message, details)
    
    @staticmethod
    def invalid_format(message: str = None, details: Any = None) -> Dict[str, Any]:
        """格式无效响应"""
        return ApiResponse.error_by_enum(ErrorCode.INVALID_FORMAT, message, details)
    
    @staticmethod
    def network_error(message: str = None, details: Any = None) -> Dict[str, Any]:
        """网络错误响应"""
        return ApiResponse.error_by_enum(ErrorCode.NETWORK_ERROR, message, details)
    
    @staticmethod
    def database_error(message: str = None, details: Any = None) -> Dict[str, Any]:
        """数据库错误响应"""
        return ApiResponse.error_by_enum(ErrorCode.DATABASE_ERROR, message, details)
    
    @staticmethod
    def config_error(message: str = None, details: Any = None) -> Dict[str, Any]:
        """配置错误响应"""
        return ApiResponse.error_by_enum(ErrorCode.CONFIG_INVALID, message, details)
    
    @staticmethod
    def business_error(message: str = None, details: Any = None) -> Dict[str, Any]:
        """业务错误响应"""
        return ApiResponse.error_by_enum(ErrorCode.BUSINESS_RULE_VIOLATION, message, details)
    
    @staticmethod
    def external_service_error(message: str = None, details: Any = None) -> Dict[str, Any]:
        """外部服务错误响应"""
        return ApiResponse.error_by_enum(ErrorCode.EXTERNAL_SERVICE_ERROR, message, details)
