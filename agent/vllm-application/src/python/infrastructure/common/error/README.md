# 错误码系统

## 概述

错误码系统为QJZH LLM管理系统提供了统一的错误处理机制，包括错误码定义、错误消息管理和错误对象封装。

## 功能特性

- **分类错误码**: 按功能模块分类的错误码体系
- **统一错误消息**: 预定义的中文错误消息
- **错误对象封装**: 包含错误码、消息和详情的错误对象
- **快捷方法**: 常用错误的快速创建方法
- **API响应格式**: 标准化的API错误响应格式

## 错误码分类

### 1. 通用错误 (1000-1999)
- `SUCCESS = 0` - 操作成功
- `UNKNOWN_ERROR = 1000` - 未知错误
- `INVALID_PARAMETER = 1001` - 参数无效
- `MISSING_PARAMETER = 1002` - 缺少必需参数
- `PERMISSION_DENIED = 1008` - 权限不足
- `RESOURCE_NOT_FOUND = 1009` - 资源未找到

### 2. 配置相关错误 (2000-2999)
- `CONFIG_NOT_FOUND = 2000` - 配置文件未找到
- `CONFIG_INVALID = 2001` - 配置文件无效
- `CONFIG_PARSE_ERROR = 2002` - 配置文件解析错误

### 3. 日志相关错误 (3000-3999)
- `LOG_INIT_FAILED = 3000` - 日志系统初始化失败
- `LOG_WRITE_FAILED = 3001` - 日志写入失败

### 4. 模型相关错误 (4000-4999)
- `MODEL_NOT_FOUND = 4000` - 模型未找到
- `MODEL_LOAD_FAILED = 4001` - 模型加载失败
- `MODEL_INFERENCE_FAILED = 4003` - 模型推理失败

### 5. Web服务相关错误 (5000-5999)
- `WEB_SERVER_START_FAILED = 5000` - Web服务器启动失败
- `WEB_PORT_ALREADY_IN_USE = 5002` - Web端口已被占用

### 6. 用户相关错误 (6000-6999)
- `USER_NOT_FOUND = 6000` - 用户未找到
- `USER_AUTHENTICATION_FAILED = 6002` - 用户认证失败

### 7. 数据相关错误 (7000-7999)
- `DATA_NOT_FOUND = 7000` - 数据未找到
- `DATA_SAVE_FAILED = 7003` - 数据保存失败

### 8. 外部服务相关错误 (8000-8999)
- `EXTERNAL_SERVICE_UNAVAILABLE = 8000` - 外部服务不可用
- `EXTERNAL_SERVICE_TIMEOUT = 8001` - 外部服务超时

### 9. 业务逻辑错误 (9000-9999)
- `BUSINESS_RULE_VIOLATION = 9000` - 违反业务规则
- `BUSINESS_OPERATION_NOT_ALLOWED = 9002` - 业务操作不被允许

## 使用方法

### 1. 基本使用

```python
from domain.model.errcode import ErrorCode, create_error, success

# 创建成功响应
result = success()
print(result.code)  # 0
print(result.message)  # "操作成功"

# 创建错误响应
error = create_error(ErrorCode.INVALID_PARAMETER, "用户名格式不正确")
print(error.code)  # 1001
print(error.message)  # "用户名格式不正确"
```

### 2. 使用快捷方法

```python
from domain.model.errcode import (
    invalid_parameter, missing_parameter, resource_not_found,
    permission_denied, unknown_error
)

# 参数错误
error1 = invalid_parameter("username")
print(error1.message)  # "参数无效: username"

# 缺少参数
error2 = missing_parameter("password")
print(error2.message)  # "缺少必需参数: password"

# 资源未找到
error3 = resource_not_found("用户", "user123")
print(error3.message)  # "用户未找到: user123"

# 权限不足
error4 = permission_denied("删除用户")
print(error4.message)  # "权限不足: 删除用户"
```

### 3. 错误处理

```python
from domain.model.errcode import is_success, is_error

def process_operation():
    # 模拟操作
    result = some_operation()
    
    if is_success(result.error_code):
        print("操作成功")
        return result
    elif is_error(result.error_code):
        print(f"操作失败: {result.message}")
        return result
```

### 4. 错误消息查找

```python
from domain.model.errcode import ErrorCode, ErrorMessage

# 根据错误码获取消息
message = ErrorMessage.get_message(ErrorCode.MODEL_LOAD_FAILED)
print(message)  # "模型加载失败"

# 根据数字代码获取消息
message2 = ErrorMessage.get_message_by_code(4001)
print(message2)  # "模型加载失败"
```

### 5. API响应格式

```python
def create_api_response(success: bool, data=None, error=None):
    """创建标准API响应"""
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

# 使用示例
error = resource_not_found("用户", "user456")
response = create_api_response(False, error=error)
```

## 错误对象属性

`SystemError` 对象包含以下属性：

- `error_code`: ErrorCode枚举值
- `code`: 数字错误码
- `message`: 错误消息
- `details`: 错误详情字典

## 方法

### SystemError 方法

- `to_dict()`: 转换为字典格式
- `__str__()`: 字符串表示
- `__repr__()`: 对象表示

### 工具函数

- `create_error()`: 创建错误对象
- `success()`: 创建成功响应
- `is_success()`: 判断是否成功
- `is_error()`: 判断是否错误

### 快捷方法

- `unknown_error()`: 创建未知错误
- `invalid_parameter()`: 创建参数无效错误
- `missing_parameter()`: 创建缺少参数错误
- `resource_not_found()`: 创建资源未找到错误
- `permission_denied()`: 创建权限不足错误

## 运行示例

```bash
cd python/domain/model
python errcode_example.py
```

## 扩展错误码

如需添加新的错误码，请按以下步骤操作：

1. 在 `ErrorCode` 枚举中添加新的错误码
2. 在 `ErrorMessage.MESSAGES` 中添加对应的错误消息
3. 如需要，添加相应的快捷方法

```python
# 添加新的错误码
class ErrorCode(Enum):
    # ... 现有错误码 ...
    NEW_ERROR = 9999

# 添加错误消息
class ErrorMessage:
    MESSAGES = {
        # ... 现有消息 ...
        ErrorCode.NEW_ERROR: "新的错误消息"
    }

# 添加快捷方法
def new_error(details: Dict[str, Any] = None) -> SystemError:
    return create_error(ErrorCode.NEW_ERROR, details=details)
``` 