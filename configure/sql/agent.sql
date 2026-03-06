USE `pg-platform-db`;

-- 1. 对话表（对应"新建对话"）
CREATE TABLE IF NOT EXISTS `chat_conversation` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '对话ID',
  `conversation_id` varchar(64) NOT NULL COMMENT '对话唯一标识（可前端生成）',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `title` varchar(200) DEFAULT NULL COMMENT '对话标题（自动生成）',
  `model_name` varchar(100) NOT NULL COMMENT '使用的模型名称',
  `is_pinned` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否置顶：0-否，1-是',
  `message_count` int NOT NULL DEFAULT 0 COMMENT '消息数量',
  `token_count` int NOT NULL DEFAULT 0 COMMENT '总token数',
  `last_message_time` datetime DEFAULT NULL COMMENT '最后消息时间',
  `is_deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否删除：0-否，1-是',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_conversation_id` (`conversation_id`),
  KEY `idx_user_created` (`user_id`, `created_at`),
  KEY `idx_user_deleted` (`user_id`, `is_deleted`, `last_message_time`),
  KEY `idx_last_time` (`last_message_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话表';

-- 2. 消息表
CREATE TABLE IF NOT EXISTS `chat_message` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '消息ID',
  `message_id` varchar(64) NOT NULL COMMENT '消息唯一标识',
  `conversation_id` varchar(64) NOT NULL COMMENT '对话ID',
  `user_id` bigint NOT NULL COMMENT '用户ID（消息发送者/拥有者）',
  `parent_message_id` varchar(64) DEFAULT NULL COMMENT '父消息ID（用于消息树结构）',
  `role` varchar(20) NOT NULL COMMENT '角色：user/assistant/system',
  `content` text NOT NULL COMMENT '消息内容',
  `content_type` varchar(20) NOT NULL DEFAULT 'text' COMMENT '内容类型：text/image/file/event-json',
  `model_name` varchar(100) DEFAULT NULL COMMENT '使用的模型',
  `token_count` int NOT NULL DEFAULT 0 COMMENT 'token数量',
  `is_context` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否作为上下文：0-否，1-是',
  `metadata` json DEFAULT NULL COMMENT '元数据（JSON格式）',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `seq_no` int NOT NULL DEFAULT 0 COMMENT '消息序号',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_message_id` (`message_id`),
  KEY `idx_conversation_seq` (`conversation_id`, `seq_no`),
  KEY `idx_conversation_created` (`conversation_id`, `created_at`),
  KEY `idx_user_conversation` (`user_id`, `conversation_id`),
  KEY `idx_role` (`role`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息表';

-- 3. 消息附件表（支持图片/文件）
CREATE TABLE IF NOT EXISTS `chat_message_attachment` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '附件ID',
  `message_id` varchar(64) NOT NULL COMMENT '消息ID',
  `user_id` bigint NOT NULL COMMENT '用户ID（附件所有者）',
  `conversation_id` varchar(64) NOT NULL COMMENT '所属对话ID',
  `file_name` varchar(255) NOT NULL COMMENT '文件名',
  `file_type` varchar(50) NOT NULL COMMENT '文件类型',
  `file_size` bigint NOT NULL COMMENT '文件大小（字节）',
  `file_url` varchar(500) NOT NULL COMMENT '文件URL',
  `thumbnail_url` varchar(500) DEFAULT NULL COMMENT '缩略图URL',
  `storage_type` varchar(20) NOT NULL DEFAULT 'local' COMMENT '存储类型：local/oss/s3',
  `metadata` json DEFAULT NULL COMMENT '元数据',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_message_id` (`message_id`),
  KEY `idx_user_conversation` (`user_id`, `conversation_id`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息附件表';

-- 4. 对话历史搜索表（优化查询）
CREATE TABLE IF NOT EXISTS `chat_history_index` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '索引ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `conversation_id` varchar(64) NOT NULL COMMENT '对话ID',
  `search_content` text COMMENT '搜索内容（标题+消息摘要）',
  `keywords` varchar(500) DEFAULT NULL COMMENT '关键词',
  `last_message_preview` varchar(500) DEFAULT NULL COMMENT '最后消息预览',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  FULLTEXT KEY `ft_search` (`search_content`),
  KEY `idx_user_keywords` (`user_id`, `keywords`(100)),
  KEY `idx_user_conversation` (`user_id`, `conversation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话历史搜索索引表';

-- 5. task - 任务主表
CREATE TABLE IF NOT EXISTS `task` (
  `task_id` varchar(64) PRIMARY KEY COMMENT '全局唯一任务ID，由协调智能体在创建时生成',
  `user_id` bigint NOT NULL COMMENT '用户ID（任务所有者）',
  `session_id` varchar(64) COMMENT '会话ID，用于关联同一用户/对话的多个任务',
  `parent_task_id` varchar(64) COMMENT '父任务ID，用于任务链',
  `conversation_id` varchar(64) COMMENT '关联的对话ID（可选）',
  `task_type` varchar(50) NOT NULL COMMENT '协调智能体通过意图识别得出的类型',
  `original_input` text COMMENT '原始请求',
  `final_output` longtext,
  `status` enum('CREATED', 'INTENT_IDENTIFIED', 'PLANNING', 'PLAN_READY', 'EXECUTING_DIRECT', 'EXECUTING_PLAN', 'PAUSED', 'COMPLETED', 'FAILED', 'CANCELLED') DEFAULT 'CREATED',
  `current_stage` varchar(100) COMMENT '更细粒度的阶段，如: "awaiting_user_confirmation"',
  `priority` tinyint DEFAULT 5,
  `coordinator_instance` varchar(100) COMMENT '处理本任务的协调智能体实例标识',
  `intent_snapshot` json COMMENT '协调智能体初始意图识别的结果快照',
  `error_info` json COMMENT '任务失败时的错误详情',
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `completed_at` datetime(6),
  `metadata` json COMMENT '扩展字段，如渠道、标签、超时设置等',
  INDEX `idx_status_priority_created` (`status`, `priority`, `created_at`), -- 核心调度索引
  INDEX `idx_user_session` (`user_id`, `session_id`),
  INDEX `idx_user_status` (`user_id`, `status`),
  INDEX `idx_updated_at` (`updated_at`),
  INDEX `idx_task_type` (`task_type`),
  INDEX `idx_conversation` (`conversation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='由协调智能体创建与维护，是任务管理的总览';

-- 6. task_plan - 任务规划表
CREATE TABLE IF NOT EXISTS `task_plan` (
  `id` bigint PRIMARY KEY AUTO_INCREMENT,
  `plan_uid` varchar(64) UNIQUE COMMENT '计划全局唯一ID，由规划智能体生成',
  `task_id` varchar(64) NOT NULL COMMENT '关联的任务',
  `user_id` bigint NOT NULL COMMENT '用户ID（任务所有者）',
  `plan_version` int NOT NULL DEFAULT 1,
  `plan_type` enum('SEQUENTIAL', 'DAG', 'HTN') NOT NULL,
  
  -- **规划输入快照**
  `input_goal_snapshot` json COMMENT '规划时收到的TaskGoal快照',
  `input_world_state_snapshot` json COMMENT '规划时感知到的WorldState快照',
  
  -- **规划过程与输出**
  `planning_agent_id` varchar(100) NOT NULL,
  `planning_strategy` varchar(50) COMMENT '使用的规划策略，如："llm_zero_shot", "rule_based", "rag_enhanced"',
  `reasoning_chain` longtext COMMENT '完整的思维链/推理过程（LLM的Raw Response或规则触发的日志）',
  `generated_plan` json NOT NULL COMMENT '最终输出的Plan结构（Actions等）',
  
  -- **评估与元数据**
  `candidate_plans` json COMMENT '如果生成了多个候选计划，全部存储在此',
  `evaluation_score` json COMMENT '对计划的评估分数，如：{"feasibility": 0.9, "cost": 0.2, "duration": 0.7}',
  `knowledge_used` json COMMENT '规划过程中用到的knowledge_base的ID列表',
  
  `is_current` tinyint(1) DEFAULT 1,
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  INDEX `idx_task_id_version` (`task_id`, `plan_version`),
  INDEX `idx_user_task` (`user_id`, `task_id`),
  INDEX `idx_planning_agent` (`planning_agent_id`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储规划智能体为任务生成的完整计划及过程数据，是核心审计表';

-- 7. task_action_dispatch - 动作分发表
CREATE TABLE IF NOT EXISTS `task_action_dispatch` (
  `id` bigint PRIMARY KEY AUTO_INCREMENT,
  `task_id` varchar(64) NOT NULL,
  `user_id` bigint NOT NULL COMMENT '用户ID（任务所有者）',
  `action_id` varchar(100) NOT NULL COMMENT '对应task_action.action_id',
  `ability_name` varchar(100) NOT NULL,
  `selected_executor_id` varchar(200) COMMENT '协调智能体最终选择执行的执行单元实例ID',
  `candidate_executors` json COMMENT '协调智能体匹配到的所有候选执行单元列表',
  `dispatch_strategy` varchar(50) COMMENT '使用的调度策略，如："round_robin", "least_load"',
  `dispatch_time` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  INDEX `idx_task_action` (`task_id`, `action_id`),
  INDEX `idx_user_task` (`user_id`, `task_id`),
  INDEX `idx_executor` (`selected_executor_id`),
  INDEX `idx_dispatch_time` (`dispatch_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='记录协调智能体的调度决策日志，用于分析调度效果和问题定位';

-- 8. coordinator_heartbeat - 协调智能体心跳表
CREATE TABLE IF NOT EXISTS `coordinator_heartbeat` (
  `instance_id` varchar(100) PRIMARY KEY COMMENT '协调智能体实例标识',
  `instance_metadata` json COMMENT '实例配置、版本等信息',
  `last_heartbeat_time` datetime(6) NOT NULL,
  `current_load` int DEFAULT 0 COMMENT '当前正在管理的任务数',
  `total_users_served` int DEFAULT 0 COMMENT '服务过的总用户数',
  `status` enum('ALIVE', 'SUSPECTED', 'DEAD') DEFAULT 'ALIVE',
  `updated_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='协调智能体定期上报心跳，用于服务发现和负载感知';

-- 9. planning_feedback - 规划效果反馈表
CREATE TABLE IF NOT EXISTS `planning_feedback` (
  `id` bigint PRIMARY KEY AUTO_INCREMENT,
  `plan_uid` varchar(64) NOT NULL COMMENT '关联的plan_uid',
  `task_id` varchar(64) NOT NULL,
  `user_id` bigint NOT NULL COMMENT '用户ID（任务所有者）',
  `success` tinyint(1) NOT NULL COMMENT '任务最终是否成功',
  `failure_point_action_id` varchar(100) COMMENT '若失败，是在哪个Action失败的',
  `failure_reason` text COMMENT '失败原因分析',
  `actual_duration_ms` int COMMENT '实际执行总耗时',
  `actual_cost` decimal(10,4) COMMENT '实际总成本',
  `plan_quality_score` decimal(3,2) COMMENT '人工或自动对规划质量的评分（1-5）',
  `user_feedback` text COMMENT '用户直接反馈',
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  INDEX `idx_plan_uid` (`plan_uid`),
  INDEX `idx_user_task` (`user_id`, `task_id`),
  INDEX `idx_success` (`success`),
  INDEX `idx_failure_reason` (`failure_reason`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='记录计划的实际执行效果，用于反向优化规划智能体';

-- 10. planning_knowledge_base - 规划知识库
CREATE TABLE IF NOT EXISTS `planning_knowledge_base` (
  `id` bigint PRIMARY KEY AUTO_INCREMENT,
  `user_id` bigint COMMENT '用户ID（创建者，NULL表示系统级知识）',
  `knowledge_type` enum('GOAL_TEMPLATE', 'DECOMPOSITION_RULE', 'ACTION_TEMPLATE', 'BEST_PRACTICE', 'CONSTRAINT', 'USER_CUSTOM') NOT NULL COMMENT 'USER_CUSTOM表示用户自定义知识',
  `domain` varchar(50) COMMENT '知识所属领域，如："data_analysis", "content_creation"',
  `scope` enum('SYSTEM', 'USER', 'TEAM') DEFAULT 'SYSTEM' COMMENT '知识范围：系统级、用户级、团队级',
  `trigger_condition` json COMMENT '触发此知识的条件（如关键词、意图类型）',
  `content` json NOT NULL COMMENT '知识内容本身，如模板、规则',
  -- 为JSON content添加文本摘要列，用于全文检索
  `content_summary` text GENERATED ALWAYS AS (
    CASE 
      WHEN JSON_EXTRACT(content, '$.description') IS NOT NULL 
        THEN JSON_UNQUOTE(JSON_EXTRACT(content, '$.description'))
      WHEN JSON_EXTRACT(content, '$.name') IS NOT NULL 
        THEN JSON_UNQUOTE(JSON_EXTRACT(content, '$.name'))
      ELSE ''
    END
  ) STORED COMMENT '从content中提取的文本摘要，用于全文检索',
  `effectiveness_score` decimal(3,2) DEFAULT 1.0 COMMENT '此知识的有效性评分（根据历史成功率动态更新）',
  `usage_count` int DEFAULT 0,
  `created_by` varchar(50) COMMENT '创建者（系统/管理员/用户）',
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  INDEX `idx_domain_type` (`domain`, `knowledge_type`),
  INDEX `idx_user_scope` (`user_id`, `scope`),
  INDEX `idx_scope_type` (`scope`, `knowledge_type`),
  FULLTEXT INDEX `idx_fulltext_summary` (`content_summary`), -- 在生成列上创建全文索引
  INDEX `idx_effectiveness` (`effectiveness_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='规划智能体的核心知识库，支持基于规则或检索增强的规划';

-- 11. planning_agent_heartbeat - 规划智能体心跳表
CREATE TABLE IF NOT EXISTS `planning_agent_heartbeat` (
  `instance_id` varchar(100) PRIMARY KEY,
  `current_model` varchar(100) COMMENT '使用的LLM模型或规则引擎版本',
  `last_heartbeat_time` datetime(6) NOT NULL,
  `queue_length` int DEFAULT 0 COMMENT '当前待处理的规划请求数',
  `avg_planning_time_ms` int COMMENT '平均规划耗时',
  `total_users_served` int DEFAULT 0 COMMENT '服务过的总用户数',
  `status` enum('IDLE', 'BUSY', 'ERROR') DEFAULT 'IDLE',
  `updated_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='规划智能体健康状态监控';

-- 12. playbook_strategies - 剧本策略表
CREATE TABLE IF NOT EXISTS `playbook_strategies` (
  `id` VARCHAR(36) PRIMARY KEY,              -- 策略唯一标识
  `user_id` bigint COMMENT '用户ID（NULL表示系统级策略）',
  `content` TEXT NOT NULL,                   -- 策略具体内容
  `category` VARCHAR(100),                   -- 策略分类（如 react, calculation）
  `scope` enum('SYSTEM', 'USER', 'TEAM') DEFAULT 'SYSTEM' COMMENT '策略范围：系统级、用户级、团队级',
  `helpful_count` INT DEFAULT 0,            -- 有效次数统计
  `harmful_count` INT DEFAULT 0,             -- 有害次数统计
  `neutral_count` INT DEFAULT 0,              -- 中性次数统计
  `usage_count` INT DEFAULT 0,               -- 使用次数
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_category` (`category`),
  INDEX `idx_user_scope` (`user_id`, `scope`),
  FULLTEXT INDEX `idx_fulltext_content` (`content`), -- 直接在TEXT列上创建全文索引
  INDEX `idx_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='剧本策略表,存储不同类型的策略内容和统计信息';

-- 13. delta_operations - 剧本策略变更操作表
CREATE TABLE IF NOT EXISTS `delta_operations` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` bigint COMMENT '用户ID（操作者）',
  `operation_type` ENUM('ADD', 'UPDATE', 'TAG', 'REMOVE') NOT NULL,
  `target_section` VARCHAR(200),              -- 操作的目标章节
  `target_bullet_id` VARCHAR(36),            -- 操作的具体条目ID
  `content` TEXT,                             -- 新增或更新的内容
  `metadata` JSON,                            -- 操作附加信息
  `reasoning` TEXT,                           -- 操作理由（便于调试）
  `batch_id` VARCHAR(36),                     -- 批次ID（同一批操作归组）
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_batch` (`batch_id`),
  INDEX `idx_user_batch` (`user_id`, `batch_id`),
  INDEX `idx_section` (`target_section`),
  INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='剧本策略变更操作表,记录对剧本策略的具体变更操作';

-- 14. task_traces - 任务推理轨迹表
CREATE TABLE IF NOT EXISTS `task_traces` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `task_id` VARCHAR(36) NOT NULL,            -- 关联的外部任务ID
  `user_id` bigint NOT NULL COMMENT '用户ID（任务所有者）',
  `trace_data` JSON,                          -- 完整的推理轨迹（输入、输出、中间状态）
  `status` ENUM('success', 'failure', 'partial') NOT NULL,
  `generator_model` VARCHAR(100),             -- 生成器模型标识
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_task` (`task_id`),
  INDEX `idx_user_task` (`user_id`, `task_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务推理轨迹表,记录每个任务的详细推理过程和结果';

-- 15. agent_ability - 智能体能力注册表（新增）
CREATE TABLE IF NOT EXISTS `agent_ability` (
  `id` bigint PRIMARY KEY AUTO_INCREMENT,
  `ability_name` varchar(100) NOT NULL UNIQUE COMMENT '能力名称，如: "image_processing.scale", "web_search"',
  `description` text COMMENT '能力描述',
  `endpoint_url` varchar(500) COMMENT '执行单元的调用端点（HTTP/gRPC等）',
  `executor_type` varchar(50) COMMENT '执行器类型，如: "http_service", "lambda", "script"',
  `req_schema` json COMMENT '请求参数JSON Schema，用于验证Action参数',
  `resp_schema` json COMMENT '响应结果JSON Schema',
  `max_concurrency` int DEFAULT 5 COMMENT '最大并发数',
  `health_status` enum('HEALTHY', 'UNHEALTHY', 'UNKNOWN') DEFAULT 'UNKNOWN',
  `last_heartbeat_time` datetime COMMENT '最后一次心跳时间',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_health_status` (`health_status`),
  INDEX `idx_updated_at` (`updated_at`),
  FULLTEXT INDEX `idx_fulltext_description` (`description`) -- 在description上创建全文索引
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体能力注册表，用于调度匹配';

-- 16. user_quota - 用户配额表（新增）
CREATE TABLE IF NOT EXISTS `user_quota` (
  `user_id` bigint PRIMARY KEY,
  `max_concurrent_tasks` int DEFAULT 5 COMMENT '最大并发任务数',
  `daily_task_limit` int DEFAULT 100 COMMENT '每日任务限制',
  `monthly_task_limit` int DEFAULT 3000 COMMENT '每月任务限制',
  `max_planning_time_ms` int DEFAULT 30000 COMMENT '最大规划时间（毫秒）',
  `max_execution_time_ms` int DEFAULT 300000 COMMENT '最大执行时间（毫秒）',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户配额表，限制资源使用';

-- ============================================
-- 规划智能体核心表结构（新增）
-- ============================================

-- 1. 规划会话表 (Planning Session)
CREATE TABLE IF NOT EXISTS planning_session_tbl (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    session_id VARCHAR(64) NOT NULL UNIQUE COMMENT '会话ID',
    user_id INT NOT NULL COMMENT '用户ID',
    agent_type VARCHAR(50) NOT NULL COMMENT '智能体类型: parking_billing/parking_operation/arrears_collection',
    initial_context TEXT COMMENT '初始上下文（协同智能体传入）',
    goal TEXT NOT NULL COMMENT '目标描述',
    status VARCHAR(20) DEFAULT 'planning' COMMENT '状态: planning/executing/completed/failed',
    plan_result JSON COMMENT '规划结果（任务DAG、任务清单等）',
    execution_log JSON COMMENT '执行日志',
    strategy_knowledge_refs JSON COMMENT '引用的策略知识ID列表',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    completed_at DATETIME COMMENT '完成时间',
    INDEX idx_user_id (user_id),
    INDEX idx_agent_type (agent_type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='规划智能体会话表';

-- 2. 任务DAG表 (Task DAG)
CREATE TABLE IF NOT EXISTS task_dag_tbl (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    session_id VARCHAR(64) NOT NULL COMMENT '规划会话ID',
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    task_name VARCHAR(200) NOT NULL COMMENT '任务名称',
    task_type VARCHAR(50) NOT NULL COMMENT '任务类型: analysis/decision/action/verification',
    description TEXT COMMENT '任务描述',
    dependencies JSON COMMENT '依赖任务ID列表（前置任务）',
    dependents JSON COMMENT '后继任务ID列表',
    is_critical_path BOOLEAN DEFAULT FALSE COMMENT '是否在关键路径上',
    execution_order INT COMMENT '执行顺序',
    parallel_group INT DEFAULT 0 COMMENT '并行执行组（同组可并行）',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/running/completed/failed/skipped',
    input_data JSON COMMENT '输入数据',
    output_data JSON COMMENT '输出数据',
    tool_calls JSON COMMENT '工具调用序列',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    max_retries INT DEFAULT 3 COMMENT '最大重试次数',
    timeout_seconds INT DEFAULT 30 COMMENT '超时时间(秒)',
    started_at DATETIME COMMENT '开始执行时间',
    completed_at DATETIME COMMENT '完成时间',
    error_info JSON COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    UNIQUE KEY uk_session_task (session_id, task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务DAG表';

-- 3. 工具匹配记录表 (Tool Matching)
CREATE TABLE IF NOT EXISTS tool_matching_tbl (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    session_id VARCHAR(64) NOT NULL COMMENT '规划会话ID',
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    tool_id VARCHAR(64) NOT NULL COMMENT '工具ID',
    tool_name VARCHAR(100) NOT NULL COMMENT '工具名称',
    match_score DECIMAL(5,2) COMMENT '匹配分数(0-100)',
    match_reason TEXT COMMENT '匹配原因',
    input_params JSON COMMENT '输入参数',
    output_schema JSON COMMENT '输出格式',
    fallback_tools JSON COMMENT '回退工具列表（按优先级）',
    is_primary BOOLEAN DEFAULT TRUE COMMENT '是否是主工具',
    execution_order INT DEFAULT 1 COMMENT '执行顺序',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
    result JSON COMMENT '执行结果',
    error_info TEXT COMMENT '错误信息',
    execution_time_ms INT COMMENT '执行耗时(ms)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_task_id (task_id),
    INDEX idx_tool_id (tool_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工具匹配记录表';

-- 4. 策略知识库表 (Strategy Knowledge Base)
CREATE TABLE IF NOT EXISTS strategy_knowledge_tbl (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    knowledge_id VARCHAR(64) NOT NULL UNIQUE COMMENT '知识ID',
    agent_type VARCHAR(50) NOT NULL COMMENT '适用的智能体类型',
    scenario_type VARCHAR(100) NOT NULL COMMENT '场景类型',
    pattern_name VARCHAR(200) NOT NULL COMMENT '模式名称',
    description TEXT COMMENT '描述',
    success_criteria JSON COMMENT '成功标准',
    failure_patterns JSON COMMENT '失败模式识别',
    best_practice TEXT COMMENT '最佳实践',
    tool_combination JSON COMMENT '推荐工具组合',
    execution_strategy JSON COMMENT '执行策略（重试、超时等）',
    sample_cases JSON COMMENT '样例案例',
    effectiveness_score DECIMAL(5,2) DEFAULT 0 COMMENT '有效性评分',
    usage_count INT DEFAULT 0 COMMENT '使用次数',
    success_count INT DEFAULT 0 COMMENT '成功次数',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_agent_type (agent_type),
    INDEX idx_scenario (scenario_type),
    INDEX idx_active (is_active),
    INDEX idx_score (effectiveness_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略知识库表';

-- 5. 执行轨迹表 (Execution Trajectory)
CREATE TABLE IF NOT EXISTS execution_trajectory_tbl (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    session_id VARCHAR(64) NOT NULL COMMENT '规划会话ID',
    trajectory_id VARCHAR(64) NOT NULL UNIQUE COMMENT '轨迹ID',
    trace_data JSON NOT NULL COMMENT '轨迹数据（完整执行路径）',
    analysis_result JSON COMMENT '分析结果',
    success_patterns JSON COMMENT '识别的成功模式',
    failure_lessons JSON COMMENT '失败教训',
    optimization_suggestions JSON COMMENT '优化建议',
    strategy_update_needed BOOLEAN DEFAULT FALSE COMMENT '是否需要更新策略',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='执行轨迹表';

-- 6. 规划中间态表 (Planning Intermediate State)
CREATE TABLE IF NOT EXISTS planning_intermediate_state_tbl (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    session_id VARCHAR(64) NOT NULL COMMENT '规划会话ID',
    stage VARCHAR(50) NOT NULL COMMENT '阶段: parsing/decomposition/dependency_analysis/tool_matching/task_generation',
    state_data JSON NOT NULL COMMENT '状态数据',
    reasoning_chain TEXT COMMENT '推理链',
    conflicts_detected JSON COMMENT '检测到的冲突',
    resolutions JSON COMMENT '冲突解决方案',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_stage (stage),
    UNIQUE KEY uk_session_stage (session_id, stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='规划中间态表';

-- 7. 智能体配置表 (Agent Configuration)
CREATE TABLE IF NOT EXISTS planning_agent_config_tbl (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    agent_type VARCHAR(50) NOT NULL UNIQUE COMMENT '智能体类型',
    agent_name VARCHAR(100) NOT NULL COMMENT '智能体名称',
    description TEXT COMMENT '描述',
    capabilities JSON COMMENT '能力列表',
    default_tools JSON COMMENT '默认工具集',
    system_prompt TEXT COMMENT '系统提示词',
    llm_config JSON COMMENT 'LLM配置',
    max_concurrent_tasks INT DEFAULT 5 COMMENT '最大并发任务数',
    default_timeout_seconds INT DEFAULT 30 COMMENT '默认超时时间',
    retry_policy JSON COMMENT '重试策略',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体配置表';

-- 8. 依赖关系表 (Dependency Relations)
CREATE TABLE IF NOT EXISTS task_dependency_tbl (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    session_id VARCHAR(64) NOT NULL COMMENT '规划会话ID',
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    depends_on_task_id VARCHAR(64) NOT NULL COMMENT '依赖的任务ID',
    dependency_type VARCHAR(20) DEFAULT 'strong' COMMENT '依赖类型: strong/weak',
    condition_expression TEXT COMMENT '条件表达式（弱依赖的条件）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_task_id (task_id),
    UNIQUE KEY uk_dependency (session_id, task_id, depends_on_task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务依赖关系表';

-- 初始化三种规划智能体配置
INSERT INTO planning_agent_config_tbl (agent_type, agent_name, description, capabilities, default_tools, system_prompt, llm_config, retry_policy) VALUES
('parking_billing', '正常停车计费事件规划智能体', '负责停车计费事件的规划，包括停车记录处理、计费计算、异常检测反思、停车事件入库等功能',
 '["parking_record_analysis", "billing_calculation", "exception_detection", "event_storage"]',
 '["parking_record_query", "billing_calculator", "fee_validator", "event_logger", "anomaly_detector"]',
 '你是一个专业的停车计费事件规划智能体。你的职责是：1.解析停车记录数据 2.计算停车费用 3.检测计费异常 4.生成计费反思报告 5.将停车事件入库',
 '{"model": "gpt-4", "temperature": 0.3, "max_tokens": 4000}',
 '{"max_retries": 3, "retry_delay": 2, "backoff_multiplier": 2}'
),
('parking_operation', '停车运营规划智能体', '负责停车场运营管理，包括资源查询、费率策略管理、政策管理等功能',
 '["resource_management", "pricing_strategy", "policy_enforcement", "utilization_analysis"]',
 '["parking_lot_query", "space_manager", "pricing_engine", "policy_validator", "occupancy_analyzer"]',
 '你是一个专业的停车运营规划智能体。你的职责是：1.查询停车场资源状态 2.管理费率策略 3.管理停车政策 4.分析运营数据 5.协调资源配置',
 '{"model": "gpt-4", "temperature": 0.3, "max_tokens": 4000}',
 '{"max_retries": 3, "retry_delay": 2, "backoff_multiplier": 2}'
),
('arrears_collection', '欠费追缴规划智能体', '负责欠费追缴策略规划，包括风险等级分层、追缴策略制定、自动化追缴流程、欠费处置策略等功能',
 '["risk_assessment", "collection_strategy", "workflow_automation", "legal_compliance"]',
 '["arrears_query", "risk_scorer", "collection_planner", "notification_sender", "payment_gateway", "escalation_manager"]',
 '你是一个专业的欠费追缴规划智能体。你的职责是：1.对欠费记录进行风险分层 2.制定差异化追缴策略 3.设计自动化追缴流程 4.管理欠费处置策略',
 '{"model": "gpt-4", "temperature": 0.3, "max_tokens": 4000}',
 '{"max_retries": 3, "retry_delay": 2, "backoff_multiplier": 2}'
);

-- 初始化策略知识库样本数据
INSERT INTO strategy_knowledge_tbl (knowledge_id, agent_type, scenario_type, pattern_name, description, success_criteria, best_practice, tool_combination, execution_strategy) VALUES
('PARK_BILL_NORMAL_001', 'parking_billing', 'normal_parking', '标准停车计费模式', '适用于标准停车场的正常计费流程',
 '["计费准确", "无重复计费", "费率应用正确", "用户无投诉"]',
 '1.入场时间精确到分钟 2.费率按时段分段计算 3.优惠自动匹配 4.出场时即时结算',
 '["parking_record_query", "billing_calculator", "fee_validator"]',
 '{"timeout": 30, "retry": 3, "fallback": "manual_review"}'
),
('PARK_BILL_EXCEPTION_001', 'parking_billing', 'billing_exception', '计费异常处理模式', '当检测到计费异常时的处理流程',
 '["异常被检测", "根因被识别", "修正方案有效", "用户被通知"]',
 '1.多维度异常检测 2.自动修正低风险异常 3.高风险异常转人工 4.记录异常原因',
 '["anomaly_detector", "billing_calculator", "event_logger", "notification_sender"]',
 '{"timeout": 60, "retry": 2, "fallback": "human_intervention"}'
),
('COLLECTION_LOW_RISK_001', 'arrears_collection', 'low_risk_arrears', '低风险追缴策略', '适用于小额、首次欠费、信用良好的用户',
 '["用户主动还款", "无投诉", "成本低", "速度快"]',
 '1.短信/APP推送提醒 2.提供便捷支付入口 3.给予宽限期 4.小额减免激励',
 '["arrears_query", "risk_scorer", "notification_sender", "payment_gateway"]',
 '{"timeout": 86400, "retry": 5, "interval": 7200, "fallback": "phone_call"}'
),
('COLLECTION_HIGH_RISK_001', 'arrears_collection', 'high_risk_arrears', '高风险追缴策略', '适用于大额、多次欠费、恶意逃费的用户',
 '["成功回收", "法律合规", "证据充分", "成本可控"]',
 '1.电话催收 2.律师函警告 3.信用记录上报 4.法律诉讼准备',
 '["arrears_query", "risk_scorer", "escalation_manager", "legal_preparer"]',
 '{"timeout": 2592000, "retry": 10, "interval": 86400, "fallback": "legal_action"}'
);
