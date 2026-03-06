package com.pg.platform.securitymng.shared.constant;

import java.util.HashMap;
import java.util.Map;

/**
 * 错误消息定义（与 Python ErrorMessage 对齐）
 */
public final class ErrorMessage {

    private static final Map<ErrorCode, String> MESSAGES = new HashMap<>();

    static {
        MESSAGES.put(ErrorCode.SUCCESS, "操作成功");

        MESSAGES.put(ErrorCode.UNKNOWN_ERROR, "未知错误");
        MESSAGES.put(ErrorCode.INVALID_PARAMETER, "参数无效");
        MESSAGES.put(ErrorCode.MISSING_PARAMETER, "缺少必需参数");
        MESSAGES.put(ErrorCode.INVALID_FORMAT, "格式无效");
        MESSAGES.put(ErrorCode.TIMEOUT, "操作超时");
        MESSAGES.put(ErrorCode.NETWORK_ERROR, "网络错误");
        MESSAGES.put(ErrorCode.DATABASE_ERROR, "数据库错误");
        MESSAGES.put(ErrorCode.DATABASE_CONNECTION_ERROR, "数据库连接错误");
        MESSAGES.put(ErrorCode.DATABASE_EXECUTION_ERROR, "数据库执行错误");
        MESSAGES.put(ErrorCode.DATABASE_INSERT_ERROR, "数据库插入错误");
        MESSAGES.put(ErrorCode.DATABASE_DELETE_ERROR, "数据库删除错误");
        MESSAGES.put(ErrorCode.DATABASE_UPDATE_ERROR, "数据库更新错误");
        MESSAGES.put(ErrorCode.DATABASE_QUERY_ERROR, "数据库查询错误");
        MESSAGES.put(ErrorCode.DATABASE_TRANSACTION_ERROR, "数据库事务错误");
        MESSAGES.put(ErrorCode.FILE_NOT_FOUND, "文件未找到");
        MESSAGES.put(ErrorCode.PERMISSION_DENIED, "权限不足");
        MESSAGES.put(ErrorCode.RESOURCE_NOT_FOUND, "资源未找到");
        MESSAGES.put(ErrorCode.RESOURCE_ALREADY_EXISTS, "资源已存在");
        MESSAGES.put(ErrorCode.OPERATION_FAILED, "操作失败");
        MESSAGES.put(ErrorCode.SYSTEM_BUSY, "系统繁忙");
        MESSAGES.put(ErrorCode.SERVICE_UNAVAILABLE, "服务不可用");
        MESSAGES.put(ErrorCode.INIT_FAILURE, "初始化失败");
        MESSAGES.put(ErrorCode.INVALID_REQUEST, "无效请求");
        MESSAGES.put(ErrorCode.NOT_FOUND, "资源未找到");
        MESSAGES.put(ErrorCode.INTERNAL_ERROR, "服务器内部错误");
        MESSAGES.put(ErrorCode.CONTROLLER_INIT_FAILED, "控制器初始化失败");
        MESSAGES.put(ErrorCode.ACTIVEMQ_CONNECTION_ERROR, "ActiveMQ 连接错误");
        MESSAGES.put(ErrorCode.ACTIVEMQ_PUBLISH_ERROR, "ActiveMQ 消息发布错误");
        MESSAGES.put(ErrorCode.REDIS_CLIENT_NOT_INIT, "Redis 客户端未初始化");
        MESSAGES.put(ErrorCode.EXCEPTION_ERROR, "系统异常错误");
        MESSAGES.put(ErrorCode.MQ_RUNNING_ERROR, "消息队列运行错误");
        MESSAGES.put(ErrorCode.PARKING_SPACE_MNG_RUNNING_ERROR, "停车位管理运行错误");
        MESSAGES.put(ErrorCode.DEVOPS_RUNNER_START_FAILED, "DevOps Runner 启动失败");
        MESSAGES.put(ErrorCode.SCHE_FUNC_RUNNER_START_FAILED, "调度函数 Runner 启动失败");
        MESSAGES.put(ErrorCode.SYSTEM_INIT_RUNNER_START_FAILED, "系统初始化 Runner 启动失败");
        MESSAGES.put(ErrorCode.EVENT_SCHE_ENGINE_RUNNER_START_FAILED, "事件调度引擎 Runner 启动失败");
        MESSAGES.put(ErrorCode.OBJ_NOT_FOUND, "对象未找到");
        MESSAGES.put(ErrorCode.OBJ_OUTSTRICTION, "对象数量超出限制");
        MESSAGES.put(ErrorCode.OBJ_ALREADY_EXISTS, "对象已存在");
        MESSAGES.put(ErrorCode.NOT_SUPPORTED, "操作不支持");
        MESSAGES.put(ErrorCode.PTZ_CAMERA_CONTROLLER_INIT_ERROR, "球机控制器初始化失败");
        MESSAGES.put(ErrorCode.INVALID_DATA, "数据无效");
        MESSAGES.put(ErrorCode.INIT_SERVICE_FALURE, "初始化服务失败");
        MESSAGES.put(ErrorCode.INITIALIZED_WORKFLOW, "工作流已初始化");
        MESSAGES.put(ErrorCode.INIT_COMPONENTS_FALURE, "组件初始化失败");

        MESSAGES.put(ErrorCode.CONFIG_NOT_FOUND, "配置文件未找到");
        MESSAGES.put(ErrorCode.CONFIG_INVALID, "配置文件无效");
        MESSAGES.put(ErrorCode.CONFIG_PARSE_ERROR, "配置文件解析错误");
        MESSAGES.put(ErrorCode.CONFIG_MISSING_REQUIRED, "配置文件缺少必需项");

        MESSAGES.put(ErrorCode.LOG_INIT_FAILED, "日志系统初始化失败");
        MESSAGES.put(ErrorCode.LOG_WRITE_FAILED, "日志写入失败");
        MESSAGES.put(ErrorCode.LOG_LEVEL_INVALID, "日志级别无效");
        MESSAGES.put(ErrorCode.LOG_PATH_INVALID, "日志路径无效");

        MESSAGES.put(ErrorCode.ADD_LONG_MEMROY_FAILURE, "添加长时记忆失败");
        MESSAGES.put(ErrorCode.RETRIEVE_LONG_MEMROY_FAILURE, "检索长时记忆失败");
        MESSAGES.put(ErrorCode.UPDATE_SHORT_MEMROY_FAILURE, "更新短时记忆失败");
        MESSAGES.put(ErrorCode.GET_CONVERSATION_CONTEXT_FAILURE, "获取会话上下文失败");
        MESSAGES.put(ErrorCode.CLEAR_SHORT_MEMROY_FAILURE, "清空短时记忆失败");
        MESSAGES.put(ErrorCode.SAVE_TOOL_RESULT_FAILURE, "保存工具结果失败");
        MESSAGES.put(ErrorCode.VLMS_NOT_INITIALIZED, "VLMS 未初始化");
        MESSAGES.put(ErrorCode.PLANNING_NODE_FAILURE, "规划节点失败");
        MESSAGES.put(ErrorCode.MODE_SELECTOR_FAILURE, "模式选择器失败");
        MESSAGES.put(ErrorCode.BUILD_REACT_WORKFLOW_FAILURE, "构建 ReAct 工作流失败");
        MESSAGES.put(ErrorCode.BUILD_PLAN_EXECUTE_WORKFLOW_FAILURE, "构建 Plan-Execute 工作流失败");
        MESSAGES.put(ErrorCode.BUILD_UNIFIED_AGENT_FAILURE, "构建统一 Agent 失败");
        MESSAGES.put(ErrorCode.GET_MODE_PROMPT_FAILURE, "获取模式提示失败");
        MESSAGES.put(ErrorCode.SELECT_MODE_FAILURE, "选择模式失败");
        MESSAGES.put(ErrorCode.PLAN_EXECUTE_FAILURE, "Plan 执行失败");
        MESSAGES.put(ErrorCode.SEARCH_LONG_TERM_FAILURE, "长时记忆检索失败");
        MESSAGES.put(ErrorCode.INIT_MEMORY_FAILURE, "记忆初始化失败");
        MESSAGES.put(ErrorCode.ADD_LONG_TERM_FAILURE, "添加长时记忆失败");
        MESSAGES.put(ErrorCode.UPDATE_SHORT_TERM_FAILURE, "更新短时记忆失败");
        MESSAGES.put(ErrorCode.CLEAR_SHORT_TERM_FAILURE, "清空短时记忆失败");
        MESSAGES.put(ErrorCode.GET_TOOL_MEMORY_FAILURE, "获取工具记忆失败");
        MESSAGES.put(ErrorCode.MEMORY_CLIENT_NOT_INITIALIZED, "记忆客户端未初始化");
        MESSAGES.put(ErrorCode.MODE_ROUTER_FAILURE, "模式路由失败");
        MESSAGES.put(ErrorCode.INIT_PROMPT_TEMPLATE_FAILURE, "初始化提示模板失败");
        MESSAGES.put(ErrorCode.IMAGE_TO_BASE64_FAILURE, "图片转换为 base64 失败");
        MESSAGES.put(ErrorCode.BUILD_VLM_REQUEST_FAILURE, "构建 VLM 请求失败");
        MESSAGES.put(ErrorCode.INVOKE_LLM_FAILURE, "调用大模型失败");
        MESSAGES.put(ErrorCode.VLM_NOT_INITIALIZED, "VLM 未初始化");
        MESSAGES.put(ErrorCode.BUILD_INITIAL_STATE_FAILURE, "初始化状态失败");

        MESSAGES.put(ErrorCode.MODEL_NOT_FOUND, "模型未找到");
        MESSAGES.put(ErrorCode.MODEL_LOAD_FAILED, "模型加载失败");
        MESSAGES.put(ErrorCode.MODEL_INIT_FAILED, "模型初始化失败");
        MESSAGES.put(ErrorCode.MODEL_INFERENCE_FAILED, "模型推理失败");
        MESSAGES.put(ErrorCode.MODEL_CONFIG_INVALID, "模型配置无效");
        MESSAGES.put(ErrorCode.MODEL_VERSION_NOT_SUPPORTED, "模型版本不支持");
        MESSAGES.put(ErrorCode.MODEL_MEMORY_INSUFFICIENT, "模型内存不足");
        MESSAGES.put(ErrorCode.MODEL_DEVICE_NOT_AVAILABLE, "模型设备不可用");
        MESSAGES.put(ErrorCode.MODEL_BUSY, "模型繁忙，请稍后重试");
        MESSAGES.put(ErrorCode.MODEL_CHAT_ERROR, "模型聊天错误");
        MESSAGES.put(ErrorCode.MODEL_CHAT_STOP_ERROR, "模型聊天停止错误");
        MESSAGES.put(ErrorCode.MODEL_MCP_ERROR, "模型 MCP 错误");
        MESSAGES.put(ErrorCode.MODEL_ALREADY_LOADED, "模型已加载");
        MESSAGES.put(ErrorCode.MODEL_NOT_FOUND_TOKENS, "模型未找到对应 tokens");
        MESSAGES.put(ErrorCode.MODEL_NOT_LOADED, "模型未加载");
        MESSAGES.put(ErrorCode.AUDIO_DURATION_INVALID, "音频时长不合法");
        MESSAGES.put(ErrorCode.LINK_VLLM_SERVER_FAILURE, "连接 VLLM 服务失败");

        MESSAGES.put(ErrorCode.WEB_SERVER_START_FAILED, "Web 服务器启动失败");
        MESSAGES.put(ErrorCode.WEB_SERVER_STOP_FAILED, "Web 服务器停止失败");
        MESSAGES.put(ErrorCode.WEB_PORT_ALREADY_IN_USE, "Web 端口已被占用");
        MESSAGES.put(ErrorCode.WEB_ADDRESS_INVALID, "Web 地址无效");
        MESSAGES.put(ErrorCode.WEB_REQUEST_INVALID, "Web 请求无效");
        MESSAGES.put(ErrorCode.WEB_RESPONSE_FAILED, "Web 响应失败");
        MESSAGES.put(ErrorCode.WEB_AUTHENTICATION_FAILED, "Web 认证失败");
        MESSAGES.put(ErrorCode.WEB_AUTHORIZATION_FAILED, "Web 授权失败");
        MESSAGES.put(ErrorCode.WEB_RATE_LIMIT_EXCEEDED, "Web 请求频率超限");
        MESSAGES.put(ErrorCode.WEB_APP_START_FAILED, "Web 应用启动失败");

        MESSAGES.put(ErrorCode.USER_NOT_FOUND, "用户未找到");
        MESSAGES.put(ErrorCode.USER_ALREADY_EXISTS, "用户已存在");
        MESSAGES.put(ErrorCode.USER_AUTHENTICATION_FAILED, "用户认证失败");
        MESSAGES.put(ErrorCode.USER_AUTHORIZATION_FAILED, "用户授权失败");
        MESSAGES.put(ErrorCode.USER_SESSION_EXPIRED, "用户会话已过期");
        MESSAGES.put(ErrorCode.USER_INPUT_INVALID, "用户输入无效");

        MESSAGES.put(ErrorCode.DATA_NOT_FOUND, "数据未找到");
        MESSAGES.put(ErrorCode.DATA_INVALID, "数据无效");
        MESSAGES.put(ErrorCode.DATA_PARSE_ERROR, "数据解析错误");
        MESSAGES.put(ErrorCode.DATA_SAVE_FAILED, "数据保存失败");
        MESSAGES.put(ErrorCode.DATA_DELETE_FAILED, "数据删除失败");
        MESSAGES.put(ErrorCode.DATA_QUERY_FAILED, "数据查询失败");
        MESSAGES.put(ErrorCode.DATA_FORMAT_INVALID, "数据格式无效");

        MESSAGES.put(ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, "外部服务不可用");
        MESSAGES.put(ErrorCode.EXTERNAL_SERVICE_TIMEOUT, "外部服务超时");
        MESSAGES.put(ErrorCode.EXTERNAL_SERVICE_ERROR, "外部服务错误");
        MESSAGES.put(ErrorCode.EXTERNAL_API_INVALID, "外部 API 无效");
        MESSAGES.put(ErrorCode.EXTERNAL_AUTHENTICATION_FAILED, "外部服务认证失败");

        MESSAGES.put(ErrorCode.BUSINESS_RULE_VIOLATION, "违反业务规则");
        MESSAGES.put(ErrorCode.BUSINESS_STATE_INVALID, "业务状态无效");
        MESSAGES.put(ErrorCode.BUSINESS_OPERATION_NOT_ALLOWED, "业务操作不被允许");
        MESSAGES.put(ErrorCode.BUSINESS_DATA_INCONSISTENT, "业务数据不一致");
        MESSAGES.put(ErrorCode.LLM_APPLICATION_NOT_FOUND, "大模型应用未找到");
        MESSAGES.put(ErrorCode.LLM_APPLICATION_GET_FAILED, "获取大模型应用失败");
        MESSAGES.put(ErrorCode.LLM_APPLICATION_NOT_UNIQUE, "大模型应用不唯一");
        MESSAGES.put(ErrorCode.LLM_ANALYZE_FAILED, "大模型分析失败");

        MESSAGES.put(ErrorCode.DEVICE_NOT_FOUND, "设备未找到");
        MESSAGES.put(ErrorCode.DEVICE_INIT_FAILED, "设备初始化失败");
        MESSAGES.put(ErrorCode.DEVICE_SELECT_FAILED, "设备选择失败");
        MESSAGES.put(ErrorCode.DEVICE_BUSY, "设备繁忙");
        MESSAGES.put(ErrorCode.DEVICE_NOT_SELECTED, "设备未选择");
        MESSAGES.put(ErrorCode.DEVICE_START_FAILED, "设备启动失败");
        MESSAGES.put(ErrorCode.DEVICE_STOP_FAILED, "设备停止失败");
        MESSAGES.put(ErrorCode.DEVICE_OPERATION_FAILED, "设备操作失败");

        MESSAGES.put(ErrorCode.SQL_SELECT_FAILED, "SQL 查询失败");
        MESSAGES.put(ErrorCode.SQL_INSERT_FAILED, "SQL 插入失败");
        MESSAGES.put(ErrorCode.SQL_UPDATE_FAILED, "SQL 更新失败");
        MESSAGES.put(ErrorCode.SQL_DELETE_FAILED, "SQL 删除失败");

        MESSAGES.put(ErrorCode.PARKING_BEHAVIOR_FAILED, "停车行为处理失败");
        MESSAGES.put(ErrorCode.PLATE_COPYING_MISS, "车牌识别失败");

        MESSAGES.put(ErrorCode.MEMORY_RETRIEVAL_NODE_FAILURE, "记忆检索节点失败");
        MESSAGES.put(ErrorCode.LLM_BRAIN_NODE_FAILURE, "LLM 思维节点失败");
        MESSAGES.put(ErrorCode.TOOL_CALL_NODE_FAILURE, "工具调用节点失败");
        MESSAGES.put(ErrorCode.RESPONSE_NODE_FAILURE, "响应节点失败");
        MESSAGES.put(ErrorCode.STEP_MANAGER_NODE_FAILURE, "步骤管理节点失败");
        MESSAGES.put(ErrorCode.PARSE_PLAN_EXECUTION_RESPONSE_FAILURE, "解析 Plan-Execute 响应失败");
        MESSAGES.put(ErrorCode.PARSE_REACT_RESPONSE_FAILURE, "解析 ReAct 响应失败");
        MESSAGES.put(ErrorCode.TOOL_NOT_FOUND, "工具未找到");
        MESSAGES.put(ErrorCode.TOOL_EXECUTION_FAILURE, "工具执行失败");
        MESSAGES.put(ErrorCode.UNSUPPORTED_OPERATION, "不支持的操作");
        MESSAGES.put(ErrorCode.DIAGNOSIS_NODE_FAILURE, "诊断节点失败");
        MESSAGES.put(ErrorCode.INFO_COLLECTION_NODE_FAILURE, "信息收集节点失败");
        MESSAGES.put(ErrorCode.DECISION_NODE_FAILURE, "决策节点失败");
        MESSAGES.put(ErrorCode.EXECUTE_NODE_FAILURE, "执行节点失败");
        MESSAGES.put(ErrorCode.VERIFY_NODE_FAILURE, "验证节点失败");
        MESSAGES.put(ErrorCode.HISTORY_CHECK_NODE_FAILURE, "历史检查节点失败");
        MESSAGES.put(ErrorCode.VLM_ANALYSIS_NODE_FAILURE, "VLM 分析节点失败");
        MESSAGES.put(ErrorCode.STORAGE_NODE_FAILURE, "存储节点失败");
        MESSAGES.put(ErrorCode.REFLECTION_NODE_FAILURE, "反思节点失败");

        MESSAGES.put(ErrorCode.GENE_BANK_SEARCH_FAILURE, "基因库搜索失败");
        MESSAGES.put(ErrorCode.GENE_BANK_MATCH_FAILURE, "基因库匹配失败");
        MESSAGES.put(ErrorCode.GENE_BANK_INSERT_FAILURE, "基因库插入失败");
        MESSAGES.put(ErrorCode.GENE_BANK_UPDATE_FAILURE, "基因库更新失败");
        MESSAGES.put(ErrorCode.GENE_BANK_QUERY_FAILURE, "基因库查询失败");

        MESSAGES.put(ErrorCode.FACT_MEMORY_QUERY_FAILURE, "事实记忆查询失败");
        MESSAGES.put(ErrorCode.FACT_MEMORY_INSERT_FAILURE, "事实记忆插入失败");
        MESSAGES.put(ErrorCode.FACT_MEMORY_UPDATE_FAILURE, "事实记忆更新失败");
        MESSAGES.put(ErrorCode.VEHICLE_HISTORY_QUERY_FAILURE, "车辆历史查询失败");

        MESSAGES.put(ErrorCode.TOOL_MEMORY_RECORD_FAILURE, "工具记忆记录失败");

        MESSAGES.put(ErrorCode.EVENT_CONFIDENCE_ROUTER_FAILURE, "事件置信度路由失败");
        MESSAGES.put(ErrorCode.CAPTCHA_INVALID, "验证码无效");
        MESSAGES.put(ErrorCode.INVALID_USER_OR_PASSWORD,"无效用户或者密码");
        MESSAGES.put(ErrorCode.TOKEN_INVALID, "无效的token");
        MESSAGES.put(ErrorCode.TOKEN_EXPIRED, "token已过期");
        MESSAGES.put(ErrorCode.TOKEN_MISSING, "token缺失");
    }

    private ErrorMessage() {}

    public static String getMessage(ErrorCode errorCode) {
        return MESSAGES.getOrDefault(errorCode, "未知错误");
    }

    public static String getMessageByCode(int code) {
        ErrorCode e = ErrorCode.fromCode(code);
        return e != null ? getMessage(e) : "未知错误";
    }
}
