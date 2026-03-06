#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统错误码定义
"""

from enum import Enum
from typing import Dict, Any


class ErrorCode(Enum):
    """错误码枚举"""
    
    # 成功
    SUCCESS = 0
    
    # 通用错误 (1000-1999)
    UNKNOWN_ERROR = 1000
    INVALID_PARAMETER = 1001
    MISSING_PARAMETER = 1002
    INVALID_FORMAT = 1003
    TIMEOUT = 1004
    NETWORK_ERROR = 1005
    DATABASE_ERROR = 1006
    DATABASE_CONNECTION_ERROR = 1007
    DATABASE_EXECUTION_ERROR = 1008
    DATABASE_INSERT_ERROR = 1009
    DATABASE_DELETE_ERROR = 1010
    DATABASE_UPDATE_ERROR = 1011
    DATABASE_QUERY_ERROR = 1012
    DATABASE_TRANSACTION_ERROR = 1013
    FILE_NOT_FOUND = 1014
    PERMISSION_DENIED = 1015
    RESOURCE_NOT_FOUND = 1016
    RESOURCE_ALREADY_EXISTS = 1017
    OPERATION_FAILED = 1018
    SYSTEM_BUSY = 1019
    SERVICE_UNAVAILABLE = 1020
    INIT_FAILURE = 1021
    INVALID_REQUEST = 1022
    NOT_FOUND = 1023
    INTERNAL_ERROR = 1024
    CONTROLLER_INIT_FAILED = 1025
    ACTIVEMQ_CONNECTION_ERROR = 1026
    ACTIVEMQ_PUBLISH_ERROR = 1027
    REDIS_CLIENT_NOT_INIT = 1028
    EXCEPTION_ERROR = 1029
    MQ_RUNNING_ERROR = 1030
    PARKING_SPACE_MNG_RUNNING_ERROR = 1031
    DEVOPS_RUNNER_START_FAILED = 1032
    SCHE_FUNC_RUNNER_START_FAILED = 1033
    SYSTEM_INIT_RUNNER_START_FAILED = 1034
    EVENT_SCHE_ENGINE_RUNNER_START_FAILED = 1035
    OBJ_NOT_FOUND = 1036
    OBJ_OUTSTRICTION = 1037  # 对象数量超出限制
    OBJ_ALREADY_EXISTS = 1038  # 对象已存在
    NOT_SUPPORTED = 1039       #不支持
    PTZ_CAMERA_CONTROLLER_INIT_ERROR = 1040 #球机控制器初始化失败
    INVALID_DATA = 1041      #数据无效
    INIT_SERVICE_FALURE = 1042 #服务初始化失败
    INITIALIZED_WORKFLOW = 1043 #工作流已初始化
    INIT_COMPONENTS_FALURE = 1044 #组件初始化失败
    
    # 配置相关错误 (2000-2999)
    CONFIG_NOT_FOUND = 2000
    CONFIG_INVALID = 2001
    CONFIG_PARSE_ERROR = 2002
    CONFIG_MISSING_REQUIRED = 2003
    
    # 日志相关错误 (3000-3999)
    LOG_INIT_FAILED = 3000
    LOG_WRITE_FAILED = 3001
    LOG_LEVEL_INVALID = 3002
    LOG_PATH_INVALID = 3003
    #AGENT 相关
    ADD_LONG_MEMROY_FAILURE = 3500
    RETRIEVE_LONG_MEMROY_FAILURE = 3501
    UPDATE_SHORT_MEMROY_FAILURE = 3502
    GET_CONVERSATION_CONTEXT_FAILURE = 3503
    CLEAR_SHORT_MEMROY_FAILURE = 3504
    SAVE_TOOL_RESULT_FAILURE = 3505
    VLMS_NOT_INITIALIZED = 3506
    PLANNING_NODE_FAILURE = 3507
    MODE_SELECTOR_FAILURE = 3508
    BUILD_REACT_WORKFLOW_FAILURE = 3509
    BUILD_PLAN_EXECUTE_WORKFLOW_FAILURE = 3510
    BUILD_UNIFIED_AGENT_FAILURE = 3511
    GET_MODE_PROMPT_FAILURE = 3512
    SELECT_MODE_FAILURE = 3513
    PLAN_EXECUTE_FAILURE = 3514
    SEARCH_LONG_TERM_FAILURE = 3515
    INIT_MEMORY_FAILURE = 3516
    ADD_LONG_TERM_FAILURE = 3517
    UPDATE_SHORT_TERM_FAILURE = 3518
    CLEAR_SHORT_TERM_FAILURE = 3519
    GET_TOOL_MEMORY_FAILURE = 3520
    MEMORY_CLIENT_NOT_INITIALIZED = 3521
    MODE_ROUTER_FAILURE = 3522
    INIT_PROMPT_TEMPLATE_FAILURE = 3523
    IMAGE_TO_BASE64_FAILURE = 3524
    BUILD_VLM_REQUEST_FAILURE = 3525
    INVOKE_LLM_FAILURE = 3526
    VLM_NOT_INITIALIZED = 3527
    BUILD_INITIAL_STATE_FAILURE = 3528
    
    # 模型相关错误 (4000-4999)
    MODEL_NOT_FOUND = 4000
    MODEL_LOAD_FAILED = 4001
    MODEL_INIT_FAILED = 4002
    MODEL_INFERENCE_FAILED = 4003
    MODEL_CONFIG_INVALID = 4004
    MODEL_VERSION_NOT_SUPPORTED = 4005
    MODEL_MEMORY_INSUFFICIENT = 4006
    MODEL_DEVICE_NOT_AVAILABLE = 4007
    MODEL_BUSY = 4008
    MODEL_CHAT_ERROR = 4009
    MODEL_CHAT_STOP_ERROR = 4010
    MODEL_MCP_ERROR = 4011
    MODEL_ALREADY_LOADED = 4012
    MODEL_NOT_FOUND_TOKENS = 4013
    MODEL_NOT_LOADED = 4014
    AUDIO_DURATION_INVALID = 4015
    LINK_VLLM_SERVER_FAILURE = 4016
    
    # Web服务相关错误 (5000-5999)
    WEB_SERVER_START_FAILED = 5000
    WEB_SERVER_STOP_FAILED = 5001
    WEB_PORT_ALREADY_IN_USE = 5002
    WEB_ADDRESS_INVALID = 5003
    WEB_REQUEST_INVALID = 5004
    WEB_RESPONSE_FAILED = 5005
    WEB_AUTHENTICATION_FAILED = 5006
    WEB_AUTHORIZATION_FAILED = 5007
    WEB_RATE_LIMIT_EXCEEDED = 5008
    WEB_APP_START_FAILED = 5009
    
    # 用户相关错误 (6000-6999)
    USER_NOT_FOUND = 6000
    USER_ALREADY_EXISTS = 6001
    USER_AUTHENTICATION_FAILED = 6002
    USER_AUTHORIZATION_FAILED = 6003
    USER_SESSION_EXPIRED = 6004
    USER_INPUT_INVALID = 6005
    
    # 数据相关错误 (7000-7999)
    DATA_NOT_FOUND = 7000
    DATA_INVALID = 7001
    DATA_PARSE_ERROR = 7002
    DATA_SAVE_FAILED = 7003
    DATA_DELETE_FAILED = 7004
    DATA_QUERY_FAILED = 7005
    DATA_FORMAT_INVALID = 7006
    
    
    # 外部服务相关错误 (8000-8999)
    EXTERNAL_SERVICE_UNAVAILABLE = 8000
    EXTERNAL_SERVICE_TIMEOUT = 8001
    EXTERNAL_SERVICE_ERROR = 8002
    EXTERNAL_API_INVALID = 8003
    EXTERNAL_AUTHENTICATION_FAILED = 8004
    
    # 业务逻辑错误 (9000-9999)
    BUSINESS_RULE_VIOLATION = 9000
    BUSINESS_STATE_INVALID = 9001
    BUSINESS_OPERATION_NOT_ALLOWED = 9002
    BUSINESS_DATA_INCONSISTENT = 9003
    LLM_APPLICATION_NOT_FOUND = 9004
    LLM_APPLICATION_GET_FAILED = 9005
    LLM_APPLICATION_NOT_UNIQUE = 9006
    LLM_ANALYZE_FAILED = 9007
    #device
    DEVICE_NOT_FOUND = 10000
    DEVICE_INIT_FAILED = 10001
    DEVICE_SELECT_FAILED = 10002
    DEVICE_BUSY = 10003
    DEVICE_NOT_SELECTED = 10004
    DEVICE_START_FAILED = 10005
    DEVICE_STOP_FAILED = 10006
    DEVICE_OPERATION_FAILED = 10007

    #sql
    SQL_SELECT_FAILED = 11007
    SQL_INSERT_FAILED = 11008
    SQL_UPDATE_FAILED = 11009
    SQL_DELETE_FAILED = 11010

    #停车抄牌相关错误
    PARKING_BEHAVIOR_FAILED = 12000
    PLATE_COPYING_MISS = 12001
    
    # 节点函数相关错误 (12100-12199)
    MEMORY_RETRIEVAL_NODE_FAILURE = 12100
    LLM_BRAIN_NODE_FAILURE = 12101
    TOOL_CALL_NODE_FAILURE = 12102
    RESPONSE_NODE_FAILURE = 12103
    STEP_MANAGER_NODE_FAILURE = 12104
    PARSE_PLAN_EXECUTION_RESPONSE_FAILURE = 12105
    PARSE_REACT_RESPONSE_FAILURE = 12106
    TOOL_NOT_FOUND = 12107
    TOOL_EXECUTION_FAILURE = 12108
    UNSUPPORTED_OPERATION = 12109
    DIAGNOSIS_NODE_FAILURE = 12110
    INFO_COLLECTION_NODE_FAILURE = 12111
    DECISION_NODE_FAILURE = 12112
    EXECUTE_NODE_FAILURE = 12113
    VERIFY_NODE_FAILURE = 12114
    HISTORY_CHECK_NODE_FAILURE = 12115
    VLM_ANALYSIS_NODE_FAILURE = 12116
    STORAGE_NODE_FAILURE = 12117
    REFLECTION_NODE_FAILURE = 12118
    
    # 基因库相关错误 (12200-12299)
    GENE_BANK_SEARCH_FAILURE = 12200
    GENE_BANK_MATCH_FAILURE = 12201
    GENE_BANK_INSERT_FAILURE = 12202
    GENE_BANK_UPDATE_FAILURE = 12203
    GENE_BANK_QUERY_FAILURE = 12204
    
    # 事实记忆相关错误 (12300-12399)
    FACT_MEMORY_QUERY_FAILURE = 12300
    FACT_MEMORY_INSERT_FAILURE = 12301
    FACT_MEMORY_UPDATE_FAILURE = 12302
    VEHICLE_HISTORY_QUERY_FAILURE = 12303
    
    # 工具记忆相关错误 (12400-12499)
    TOOL_MEMORY_RECORD_FAILURE = 12400
    
    # 置信度路由相关错误 (12500-12599)
    EVENT_CONFIDENCE_ROUTER_FAILURE = 12500


class ErrorMessage:
    """错误消息定义"""
    
    MESSAGES = {
        # 成功
        ErrorCode.SUCCESS: "操作成功",
        
        # 通用错误 (1000-1999)
        ErrorCode.UNKNOWN_ERROR: "未知错误",
        ErrorCode.INVALID_PARAMETER: "参数无效",
        ErrorCode.MISSING_PARAMETER: "缺少必需参数",
        ErrorCode.INVALID_FORMAT: "格式无效",
        ErrorCode.TIMEOUT: "操作超时",
        ErrorCode.NETWORK_ERROR: "网络错误",
        ErrorCode.DATABASE_ERROR: "数据库错误",
        ErrorCode.DATABASE_CONNECTION_ERROR: "数据库连接错误",
        ErrorCode.DATABASE_EXECUTION_ERROR: "数据库执行错误",
        ErrorCode.DATABASE_INSERT_ERROR: "数据库插入错误",
        ErrorCode.DATABASE_DELETE_ERROR: "数据库删除错误",
        ErrorCode.DATABASE_UPDATE_ERROR: "数据库更新错误",
        ErrorCode.DATABASE_QUERY_ERROR: "数据库查询错误",
        ErrorCode.DATABASE_TRANSACTION_ERROR: "数据库事务错误",
        ErrorCode.FILE_NOT_FOUND: "文件未找到",
        ErrorCode.PERMISSION_DENIED: "权限不足",
        ErrorCode.RESOURCE_NOT_FOUND: "资源未找到",
        ErrorCode.RESOURCE_ALREADY_EXISTS: "资源已存在",
        ErrorCode.OPERATION_FAILED: "操作失败",
        ErrorCode.SYSTEM_BUSY: "系统繁忙",
        ErrorCode.SERVICE_UNAVAILABLE: "服务不可用",
        ErrorCode.INIT_FAILURE: "初始化失败",
        ErrorCode.INVALID_REQUEST: "无效请求",
        ErrorCode.NOT_FOUND: "资源未找到",
        ErrorCode.INTERNAL_ERROR: "服务器内部错误",
        ErrorCode.CONTROLLER_INIT_FAILED: "控制器初始化失败",
        ErrorCode.ACTIVEMQ_CONNECTION_ERROR: "ActiveMQ 连接错误",
        ErrorCode.ACTIVEMQ_PUBLISH_ERROR: "ActiveMQ 消息发布错误",
        ErrorCode.REDIS_CLIENT_NOT_INIT: "Redis 客户端未初始化",
        ErrorCode.EXCEPTION_ERROR: "系统异常错误",
        ErrorCode.MQ_RUNNING_ERROR: "消息队列运行错误",
        ErrorCode.PARKING_SPACE_MNG_RUNNING_ERROR: "停车位管理运行错误",
        ErrorCode.DEVOPS_RUNNER_START_FAILED: "DevOps Runner 启动失败",
        ErrorCode.SCHE_FUNC_RUNNER_START_FAILED: "调度函数 Runner 启动失败",
        ErrorCode.SYSTEM_INIT_RUNNER_START_FAILED: "系统初始化 Runner 启动失败",
        ErrorCode.EVENT_SCHE_ENGINE_RUNNER_START_FAILED: "事件调度引擎 Runner 启动失败",
        ErrorCode.OBJ_NOT_FOUND: "对象未找到",
        ErrorCode.OBJ_OUTSTRICTION: "对象数量超出限制",
        ErrorCode.OBJ_ALREADY_EXISTS: "对象已存在",
        ErrorCode.NOT_SUPPORTED: "操作不支持",
        ErrorCode.PTZ_CAMERA_CONTROLLER_INIT_ERROR: "球机控制器初始化失败",
        ErrorCode.INVALID_DATA: "数据无效",
        ErrorCode.INIT_SERVICE_FALURE: '初始化服务失败',
        ErrorCode.INIT_PROMPT_TEMPLATE_FAILURE: '初始化提示模板失败',
        ErrorCode.MODE_ROUTER_FAILURE: '模式路由失败',
        ErrorCode.IMAGE_TO_BASE64_FAILURE: '图片转换为base64失败',
        ErrorCode.BUILD_VLM_REQUEST_FAILURE: '构建vlm请求失败',
        ErrorCode.INVOKE_LLM_FAILURE: '调用大模型失败',
        ErrorCode.VLM_NOT_INITIALIZED: 'vlm未初始化',
        ErrorCode.BUILD_INITIAL_STATE_FAILURE: '初始化状态失败',
        # 配置相关错误
        ErrorCode.CONFIG_NOT_FOUND: "配置文件未找到",
        ErrorCode.CONFIG_INVALID: "配置文件无效",
        ErrorCode.CONFIG_PARSE_ERROR: "配置文件解析错误",
        ErrorCode.CONFIG_MISSING_REQUIRED: "配置文件缺少必需项",
        
        # 日志相关错误
        ErrorCode.LOG_INIT_FAILED: "日志系统初始化失败",
        ErrorCode.LOG_WRITE_FAILED: "日志写入失败",
        ErrorCode.LOG_LEVEL_INVALID: "日志级别无效",
        ErrorCode.LOG_PATH_INVALID: "日志路径无效",
        
        # 模型相关错误
        ErrorCode.MODEL_NOT_FOUND: "模型未找到",
        ErrorCode.MODEL_LOAD_FAILED: "模型加载失败",
        ErrorCode.MODEL_INIT_FAILED: "模型初始化失败",
        ErrorCode.MODEL_INFERENCE_FAILED: "模型推理失败",
        ErrorCode.MODEL_CONFIG_INVALID: "模型配置无效",
        ErrorCode.MODEL_VERSION_NOT_SUPPORTED: "模型版本不支持",
        ErrorCode.MODEL_MEMORY_INSUFFICIENT: "模型内存不足",
        ErrorCode.MODEL_DEVICE_NOT_AVAILABLE: "模型设备不可用",
        ErrorCode.MODEL_BUSY: "模型繁忙，请稍后重试",
        ErrorCode.MODEL_CHAT_ERROR: "模型聊天错误",
        ErrorCode.MODEL_CHAT_STOP_ERROR: "模型聊天停止错误",
        ErrorCode.MODEL_MCP_ERROR: "模型 MCP 错误",
        ErrorCode.MODEL_ALREADY_LOADED: "模型已加载",
        ErrorCode.MODEL_NOT_FOUND_TOKENS: "模型未找到对应 tokens",
        ErrorCode.MODEL_NOT_LOADED: "模型未加载",
        ErrorCode.AUDIO_DURATION_INVALID: "音频时长不合法",
        # Web服务相关错误
        ErrorCode.WEB_SERVER_START_FAILED: "Web服务器启动失败",
        ErrorCode.WEB_SERVER_STOP_FAILED: "Web服务器停止失败",
        ErrorCode.WEB_PORT_ALREADY_IN_USE: "Web端口已被占用",
        ErrorCode.WEB_ADDRESS_INVALID: "Web地址无效",
        ErrorCode.WEB_REQUEST_INVALID: "Web请求无效",
        ErrorCode.WEB_RESPONSE_FAILED: "Web响应失败",
        ErrorCode.WEB_AUTHENTICATION_FAILED: "Web认证失败",
        ErrorCode.WEB_AUTHORIZATION_FAILED: "Web授权失败",
        ErrorCode.WEB_RATE_LIMIT_EXCEEDED: "Web请求频率超限",
        ErrorCode.WEB_APP_START_FAILED: "Web应用启动失败",
        
        # 用户相关错误
        ErrorCode.USER_NOT_FOUND: "用户未找到",
        ErrorCode.USER_ALREADY_EXISTS: "用户已存在",
        ErrorCode.USER_AUTHENTICATION_FAILED: "用户认证失败",
        ErrorCode.USER_AUTHORIZATION_FAILED: "用户授权失败",
        ErrorCode.USER_SESSION_EXPIRED: "用户会话已过期",
        ErrorCode.USER_INPUT_INVALID: "用户输入无效",
        
        # 数据相关错误
        ErrorCode.DATA_NOT_FOUND: "数据未找到",
        ErrorCode.DATA_INVALID: "数据无效",
        ErrorCode.DATA_PARSE_ERROR: "数据解析错误",
        ErrorCode.DATA_SAVE_FAILED: "数据保存失败",
        ErrorCode.DATA_DELETE_FAILED: "数据删除失败",
        ErrorCode.DATA_QUERY_FAILED: "数据查询失败",
        ErrorCode.DATA_FORMAT_INVALID: "数据格式无效",
        
        # 外部服务相关错误
        ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE: "外部服务不可用",
        ErrorCode.EXTERNAL_SERVICE_TIMEOUT: "外部服务超时",
        ErrorCode.EXTERNAL_SERVICE_ERROR: "外部服务错误",
        ErrorCode.EXTERNAL_API_INVALID: "外部API无效",
        ErrorCode.EXTERNAL_AUTHENTICATION_FAILED: "外部服务认证失败",
        
        # 业务逻辑错误
        ErrorCode.BUSINESS_RULE_VIOLATION: "违反业务规则",
        ErrorCode.BUSINESS_STATE_INVALID: "业务状态无效",
        ErrorCode.BUSINESS_OPERATION_NOT_ALLOWED: "业务操作不被允许",
        ErrorCode.BUSINESS_DATA_INCONSISTENT: "业务数据不一致",
        ErrorCode.LLM_APPLICATION_NOT_FOUND: "大模型应用未找到",
        ErrorCode.LLM_APPLICATION_GET_FAILED: "获取大模型应用失败",
        ErrorCode.LLM_APPLICATION_NOT_UNIQUE: "大模型应用不唯一",
        ErrorCode.LLM_ANALYZE_FAILED: "大模型分析失败",
        
        # 设备相关错误
        ErrorCode.DEVICE_NOT_FOUND: "设备未找到",
        ErrorCode.DEVICE_INIT_FAILED: "设备初始化失败",
        ErrorCode.DEVICE_SELECT_FAILED: "设备选择失败",
        ErrorCode.DEVICE_BUSY: "设备繁忙",
        ErrorCode.DEVICE_NOT_SELECTED: "设备未选择",
        ErrorCode.DEVICE_START_FAILED: "设备启动失败",
        ErrorCode.DEVICE_STOP_FAILED: "设备停止失败",
        ErrorCode.DEVICE_OPERATION_FAILED: "设备操作失败",
        
        # SQL 相关错误
        ErrorCode.SQL_SELECT_FAILED: "SQL 查询失败",
        ErrorCode.SQL_INSERT_FAILED: "SQL 插入失败",
        ErrorCode.SQL_UPDATE_FAILED: "SQL 更新失败",
        ErrorCode.SQL_DELETE_FAILED: "SQL 删除失败",
        
        # 停车抄牌相关错误
        ErrorCode.PARKING_BEHAVIOR_FAILED: "停车行为处理失败",
        ErrorCode.PLATE_COPYING_MISS: "车牌识别失败",
        
        # 节点函数相关错误
        ErrorCode.MEMORY_RETRIEVAL_NODE_FAILURE: "记忆检索节点失败",
        ErrorCode.LLM_BRAIN_NODE_FAILURE: "LLM思维节点失败",
        ErrorCode.TOOL_CALL_NODE_FAILURE: "工具调用节点失败",
        ErrorCode.RESPONSE_NODE_FAILURE: "响应节点失败",
        ErrorCode.STEP_MANAGER_NODE_FAILURE: "步骤管理节点失败",
        ErrorCode.PARSE_PLAN_EXECUTION_RESPONSE_FAILURE: "解析Plan-Execute响应失败",
        ErrorCode.PARSE_REACT_RESPONSE_FAILURE: "解析ReAct响应失败",
        ErrorCode.TOOL_NOT_FOUND: "工具未找到",
        ErrorCode.TOOL_EXECUTION_FAILURE: "工具执行失败",
        ErrorCode.UNSUPPORTED_OPERATION: "不支持的操作",
        ErrorCode.DIAGNOSIS_NODE_FAILURE: "诊断节点失败",
        ErrorCode.INFO_COLLECTION_NODE_FAILURE: "信息收集节点失败",
        ErrorCode.DECISION_NODE_FAILURE: "决策节点失败",
        ErrorCode.EXECUTE_NODE_FAILURE: "执行节点失败",
        ErrorCode.VERIFY_NODE_FAILURE: "验证节点失败",
        ErrorCode.HISTORY_CHECK_NODE_FAILURE: "历史检查节点失败",
        ErrorCode.VLM_ANALYSIS_NODE_FAILURE: "VLM分析节点失败",
        ErrorCode.STORAGE_NODE_FAILURE: "存储节点失败",
        ErrorCode.REFLECTION_NODE_FAILURE: "反思节点失败",
        
        # 基因库相关错误
        ErrorCode.GENE_BANK_SEARCH_FAILURE: "基因库搜索失败",
        ErrorCode.GENE_BANK_MATCH_FAILURE: "基因库匹配失败",
        ErrorCode.GENE_BANK_INSERT_FAILURE: "基因库插入失败",
        ErrorCode.GENE_BANK_UPDATE_FAILURE: "基因库更新失败",
        ErrorCode.GENE_BANK_QUERY_FAILURE: "基因库查询失败",
        
        # 事实记忆相关错误
        ErrorCode.FACT_MEMORY_QUERY_FAILURE: "事实记忆查询失败",
        ErrorCode.FACT_MEMORY_INSERT_FAILURE: "事实记忆插入失败",
        ErrorCode.FACT_MEMORY_UPDATE_FAILURE: "事实记忆更新失败",
        ErrorCode.VEHICLE_HISTORY_QUERY_FAILURE: "车辆历史查询失败",
        
        # 工具记忆相关错误
        ErrorCode.TOOL_MEMORY_RECORD_FAILURE: "工具记忆记录失败",
        
        # 置信度路由相关错误
        ErrorCode.EVENT_CONFIDENCE_ROUTER_FAILURE: "事件置信度路由失败",
    }
    
    @classmethod
    def get_message(cls, error_code: ErrorCode) -> str:
        """获取错误消息"""
        return cls.MESSAGES.get(error_code, "未知错误")
    
    @classmethod
    def get_message_by_code(cls, code: int) -> str:
        """根据错误码获取错误消息"""
        for error_code in ErrorCode:
            if error_code.value == code:
                return cls.get_message(error_code)
        return "未知错误"

class SystemError:
    """系统错误类"""
    
    def __init__(self, error_code: ErrorCode, message: str = None, details: Dict[str, Any] = None):
        """
        初始化系统错误
        
        Args:
            error_code: 错误码
            message: 错误消息（可选，默认使用预定义消息）
            details: 错误详情（可选）
        """
        self.error_code = error_code
        self.code = error_code.value
        self.message = message or ErrorMessage.get_message(error_code)
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'code': self.code,
            'message': self.message,
            'details': self.details
        }
    
    def __str__(self) -> str:
        return f"Error {self.code}: {self.message}"
    
    def __repr__(self) -> str:
        return f"SystemError(code={self.code}, message='{self.message}')"


def create_error(error_code: ErrorCode, message: str = None, details: Dict[str, Any] = None) -> SystemError:
    """
    创建系统错误
    
    Args:
        error_code: 错误码
        message: 错误消息（可选）
        details: 错误详情（可选）
    
    Returns:
        SystemError: 系统错误对象
    """
    return SystemError(error_code, message, details)


def is_success(error_code_or_obj) -> bool:
    """判断是否为成功状态"""
    if isinstance(error_code_or_obj, SystemError):
        return error_code_or_obj.error_code == ErrorCode.SUCCESS
    return error_code_or_obj == ErrorCode.SUCCESS


def is_error(error_code_or_obj) -> bool:
    """判断是否为错误状态"""
    return not is_success(error_code_or_obj)


# 常用错误快捷方法
def success() -> SystemError:
    """创建成功响应"""
    return create_error(ErrorCode.SUCCESS)


def unknown_error(message: str = None, details: Dict[str, Any] = None) -> SystemError:
    """创建未知错误"""
    return create_error(ErrorCode.UNKNOWN_ERROR, message, details)


def invalid_parameter(param_name: str = None, details: Dict[str, Any] = None) -> SystemError:
    """创建参数无效错误"""
    message = f"参数无效: {param_name}" if param_name else None
    return create_error(ErrorCode.INVALID_PARAMETER, message, details)


def missing_parameter(param_name: str, details: Dict[str, Any] = None) -> SystemError:
    """创建缺少参数错误"""
    message = f"缺少必需参数: {param_name}"
    return create_error(ErrorCode.MISSING_PARAMETER, message, details)


def resource_not_found(resource_type: str = None, resource_id: str = None, details: Dict[str, Any] = None) -> SystemError:
    """创建资源未找到错误"""
    if resource_type and resource_id:
        message = f"{resource_type}未找到: {resource_id}"
    elif resource_type:
        message = f"{resource_type}未找到"
    else:
        message = None
    return create_error(ErrorCode.RESOURCE_NOT_FOUND, message, details)


def permission_denied(operation: str = None, details: Dict[str, Any] = None) -> SystemError:
    """创建权限不足错误"""
    message = f"权限不足: {operation}" if operation else None
    return create_error(ErrorCode.PERMISSION_DENIED, message, details) 

