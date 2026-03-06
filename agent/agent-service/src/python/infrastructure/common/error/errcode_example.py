#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误码使用示例
"""

from errcode import (
    ErrorCode, ErrorMessage, SystemError, create_error,
    success, unknown_error, invalid_parameter, missing_parameter,
    resource_not_found, permission_denied, is_success, is_error
)


def example_basic_usage():
    """基本使用示例"""
    print("=" * 50)
    print("错误码基本使用示例")
    print("=" * 50)
    
    # 1. 创建成功响应
    result = success()
    print(f"成功响应: {result}")
    print(f"  代码: {result.code}")
    print(f"  消息: {result.message}")
    print(f"  字典格式: {result.to_dict()}")
    print()
    
    # 2. 创建错误响应
    error = create_error(ErrorCode.INVALID_PARAMETER, "用户名格式不正确")
    print(f"错误响应: {error}")
    print(f"  代码: {error.code}")
    print(f"  消息: {error.message}")
    print(f"  字典格式: {error.to_dict()}")
    print()
    
    # 3. 使用预定义错误消息
    error2 = create_error(ErrorCode.FILE_NOT_FOUND)
    print(f"预定义错误: {error2}")
    print(f"  代码: {error2.code}")
    print(f"  消息: {error2.message}")
    print()


def example_error_categories():
    """错误分类示例"""
    print("=" * 50)
    print("错误分类示例")
    print("=" * 50)
    
    # 通用错误
    print("通用错误:")
    print(f"  参数无效: {ErrorCode.INVALID_PARAMETER.value}")
    print(f"  资源未找到: {ErrorCode.RESOURCE_NOT_FOUND.value}")
    print(f"  权限不足: {ErrorCode.PERMISSION_DENIED.value}")
    print()
    
    # 配置错误
    print("配置错误:")
    print(f"  配置文件未找到: {ErrorCode.CONFIG_NOT_FOUND.value}")
    print(f"  配置解析错误: {ErrorCode.CONFIG_PARSE_ERROR.value}")
    print()
    
    # 模型错误
    print("模型错误:")
    print(f"  模型未找到: {ErrorCode.MODEL_NOT_FOUND.value}")
    print(f"  模型加载失败: {ErrorCode.MODEL_LOAD_FAILED.value}")
    print(f"  模型推理失败: {ErrorCode.MODEL_INFERENCE_FAILED.value}")
    print()
    
    # Web服务错误
    print("Web服务错误:")
    print(f"  服务器启动失败: {ErrorCode.WEB_SERVER_START_FAILED.value}")
    print(f"  端口被占用: {ErrorCode.WEB_PORT_ALREADY_IN_USE.value}")
    print()


def example_shortcut_methods():
    """快捷方法示例"""
    print("=" * 50)
    print("快捷方法示例")
    print("=" * 50)
    
    # 1. 参数错误
    param_error = invalid_parameter("username", {"value": "invalid_user", "expected": "alphanumeric"})
    print(f"参数错误: {param_error}")
    print()
    
    # 2. 缺少参数
    missing_error = missing_parameter("password")
    print(f"缺少参数: {missing_error}")
    print()
    
    # 3. 资源未找到
    resource_error = resource_not_found("用户", "user123")
    print(f"资源未找到: {resource_error}")
    print()
    
    # 4. 权限不足
    perm_error = permission_denied("删除用户")
    print(f"权限不足: {perm_error}")
    print()
    
    # 5. 未知错误
    unknown = unknown_error("系统内部错误", {"traceback": "..."})
    print(f"未知错误: {unknown}")
    print()


def example_error_handling():
    """错误处理示例"""
    print("=" * 50)
    print("错误处理示例")
    print("=" * 50)
    
    def simulate_operation(operation_type: str):
        """模拟操作，可能返回成功或错误"""
        if operation_type == "success":
            return success()
        elif operation_type == "invalid_param":
            return invalid_parameter("input_data")
        elif operation_type == "not_found":
            return resource_not_found("文件", "config.yaml")
        elif operation_type == "permission":
            return permission_denied("访问数据库")
        else:
            return unknown_error("未知操作类型")
    
    # 测试不同的操作
    operations = ["success", "invalid_param", "not_found", "permission", "unknown"]
    
    for op in operations:
        result = simulate_operation(op)
        print(f"操作 '{op}':")
        print(f"  结果: {result}")
        print(f"  是否成功: {is_success(result.error_code)}")
        print(f"  是否错误: {is_error(result.error_code)}")
        print()


def example_error_message_lookup():
    """错误消息查找示例"""
    print("=" * 50)
    print("错误消息查找示例")
    print("=" * 50)
    
    # 1. 根据错误码获取消息
    error_code = ErrorCode.MODEL_LOAD_FAILED
    message = ErrorMessage.get_message(error_code)
    print(f"错误码 {error_code.value} 的消息: {message}")
    
    # 2. 根据数字代码获取消息
    code = 4001
    message2 = ErrorMessage.get_message_by_code(code)
    print(f"数字代码 {code} 的消息: {message2}")
    
    # 3. 遍历所有错误码
    print("\n所有错误码:")
    for error_code in ErrorCode:
        message = ErrorMessage.get_message(error_code)
        print(f"  {error_code.value:4d}: {message}")


def example_api_response():
    """API响应示例"""
    print("=" * 50)
    print("API响应示例")
    print("=" * 50)
    
    def create_api_response(success: bool, data=None, error=None):
        """创建API响应格式"""
        if success:
            return {
                "success": True,
                "code": 0,
                "message": "操作成功",
                "data": data
            }
        else:
            return {
                "success": False,
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "data": None
            }
    
    # 成功响应
    success_response = create_api_response(True, {"user_id": 123, "username": "test"})
    print("成功响应:")
    print(f"  {success_response}")
    print()
    
    # 错误响应
    error = resource_not_found("用户", "user456")
    error_response = create_api_response(False, error=error)
    print("错误响应:")
    print(f"  {error_response}")


if __name__ == "__main__":
    example_basic_usage()
    example_error_categories()
    example_shortcut_methods()
    example_error_handling()
    example_error_message_lookup()
    example_api_response()
    
    print("\n" + "=" * 50)
    print("错误码系统示例完成！")
    print("=" * 50) 