USE `pg-platform-db`;

-- 1. 提示词模板表
CREATE TABLE IF NOT EXISTS `prompt_template` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '模板ID',
  `template_name` varchar(100) NOT NULL COMMENT '模板名称',
  `template_content` text NOT NULL COMMENT '模板内容（支持变量占位符）',
  `description` varchar(500) DEFAULT NULL COMMENT '模板描述',
  `category` varchar(50) DEFAULT 'general' COMMENT '分类：general',
  `version` varchar(20) NOT NULL DEFAULT '1.0.0' COMMENT '版本号',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态：0-禁用，1-启用，2-草稿',
  `is_default` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否为默认模板：0-否，1-是',
  `creator_id` bigint NOT NULL COMMENT '创建人ID',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_name_version` (`template_name`, `version`),
  KEY `idx_category_status` (`category`, `status`),
  KEY `idx_creator` (`creator_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_is_default` (`is_default`),
  FULLTEXT KEY `ft_template_content` (`template_content`),
  INDEX `idx_template_name` (`template_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词模板表';

-- 2. 模板变量表
CREATE TABLE IF NOT EXISTS `prompt_variable` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '变量ID',
  `template_id` bigint NOT NULL COMMENT '模板ID',
  `variable_name` varchar(100) NOT NULL COMMENT '变量名（如：{{user_name}}）',
  `display_name` varchar(100) NOT NULL COMMENT '显示名称',
  `default_value` text COMMENT '默认值',
  `description` varchar(500) DEFAULT NULL COMMENT '变量描述',
  `data_type` varchar(20) NOT NULL DEFAULT 'string' COMMENT '数据类型：string/number/boolean/array/object',
  `is_required` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否必填：0-否，1-是',
  `validation_rule` varchar(500) DEFAULT NULL COMMENT '验证规则（JSON）',
  `sort_order` int NOT NULL DEFAULT 0 COMMENT '排序序号',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_variable` (`template_id`, `variable_name`),
  KEY `idx_template_id` (`template_id`),
  KEY `idx_is_required` (`is_required`),
  KEY `idx_sort_order` (`sort_order`),
  CONSTRAINT `fk_variable_template` FOREIGN KEY (`template_id`) REFERENCES `prompt_template` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词变量表';

-- 3. 模板版本历史表
CREATE TABLE IF NOT EXISTS `prompt_version_history` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '历史ID',
  `template_id` bigint NOT NULL COMMENT '模板ID',
  `version` varchar(20) NOT NULL COMMENT '版本号',
  `template_name` varchar(100) NOT NULL COMMENT '模板名称',
  `template_content` text NOT NULL COMMENT '模板内容',
  `change_log` text COMMENT '变更说明',
  `operator_id` bigint NOT NULL COMMENT '操作人ID',
  `operation_type` varchar(20) NOT NULL COMMENT '操作类型：create/update/delete/rollback',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_version` (`template_id`, `version`),
  KEY `idx_template_id` (`template_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_operator` (`operator_id`),
  CONSTRAINT `fk_history_template` FOREIGN KEY (`template_id`) REFERENCES `prompt_template` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模板版本历史表';

-- 4. 测试评估表
CREATE TABLE IF NOT EXISTS `prompt_test` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '测试ID',
  `test_name` varchar(100) NOT NULL COMMENT '测试名称',
  `test_type` varchar(20) NOT NULL COMMENT '测试类型：ab_test/batch_test/quick_test',
  `description` text COMMENT '测试描述',
  `creator_id` bigint NOT NULL COMMENT '创建人ID',
  `status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT '状态：pending/running/completed/failed',
  `total_cases` int NOT NULL DEFAULT 0 COMMENT '总测试用例数',
  `passed_cases` int NOT NULL DEFAULT 0 COMMENT '通过用例数',
  `failed_cases` int NOT NULL DEFAULT 0 COMMENT '失败用例数',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_test_type` (`test_type`),
  KEY `idx_creator` (`creator_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词测试表';

-- 5. A/B测试配置表
CREATE TABLE IF NOT EXISTS `prompt_ab_test` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'A/B测试ID',
  `test_id` bigint NOT NULL COMMENT '测试ID',
  `template_a_id` bigint NOT NULL COMMENT '模板A ID',
  `template_b_id` bigint NOT NULL COMMENT '模板B ID',
  `test_input` text NOT NULL COMMENT '测试输入',
  `variables_a` json DEFAULT NULL COMMENT '模板A的变量值（JSON）',
  `variables_b` json DEFAULT NULL COMMENT '模板B的变量值（JSON）',
  `evaluation_criteria` json COMMENT '评估标准（JSON数组）',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_test_id` (`test_id`),
  KEY `idx_template_a` (`template_a_id`),
  KEY `idx_template_b` (`template_b_id`),
  CONSTRAINT `fk_ab_test_test` FOREIGN KEY (`test_id`) REFERENCES `prompt_test` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_template_a` FOREIGN KEY (`template_a_id`) REFERENCES `prompt_template` (`id`),
  CONSTRAINT `fk_template_b` FOREIGN KEY (`template_b_id`) REFERENCES `prompt_template` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A/B测试配置表';

-- 6. 批量测试配置表
CREATE TABLE IF NOT EXISTS `prompt_batch_test` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '批量测试ID',
  `test_id` bigint NOT NULL COMMENT '测试ID',
  `template_id` bigint NOT NULL COMMENT '模板ID',
  `test_data_file` varchar(500) DEFAULT NULL COMMENT '测试数据文件路径',
  `test_data_count` int NOT NULL DEFAULT 0 COMMENT '测试数据数量',
  `sampling_rate` decimal(3,2) DEFAULT 1.0 COMMENT '采样率（0-1）',
  `variables_mapping` json COMMENT '变量映射（JSON）',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_test_id` (`test_id`),
  KEY `idx_template_id` (`template_id`),
  CONSTRAINT `fk_batch_test_test` FOREIGN KEY (`test_id`) REFERENCES `prompt_test` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_batch_template` FOREIGN KEY (`template_id`) REFERENCES `prompt_template` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批量测试配置表';

-- 7. 测试用例表
CREATE TABLE IF NOT EXISTS `prompt_test_case` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '用例ID',
  `test_id` bigint NOT NULL COMMENT '测试ID',
  `case_index` int NOT NULL COMMENT '用例序号',
  `input_data` text NOT NULL COMMENT '输入数据',
  `variables` json DEFAULT NULL COMMENT '变量值（JSON格式）',
  `expected_output` text COMMENT '期望输出',
  `actual_output` text COMMENT '实际输出',
  `execution_status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT '执行状态：pending/running/success/failed',
  `execution_time` int DEFAULT NULL COMMENT '执行耗时（毫秒）',
  `similarity_score` decimal(5,4) DEFAULT NULL COMMENT '相似度得分（0-1）',
  `evaluation_result` json COMMENT '评估结果（JSON）',
  `error_message` text COMMENT '错误信息',
  `executed_at` datetime DEFAULT NULL COMMENT '执行时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_test_case` (`test_id`, `case_index`),
  KEY `idx_test_id` (`test_id`),
  KEY `idx_execution_status` (`execution_status`),
  KEY `idx_executed_at` (`executed_at`),
  CONSTRAINT `fk_case_test` FOREIGN KEY (`test_id`) REFERENCES `prompt_test` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试用例表';

-- 8. prompt常量表
CREATE TABLE IF NOT EXISTS `prompt_constant_tbl` ( 
   `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'ID', 
   `user_id` bigint NOT NULL COMMENT '用户ID', 
   `application_type` varchar(50) NOT NULL COMMENT '应用类型', -- agent-coordinator,agent-planning 
   `type` varchar(50)  NOT NULL COMMENT '常量类型', -- 例如：system_prompt, user_prompt, assistant_prompt 
   `value` text NOT NULL COMMENT '常量值', 
   `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间', 
   PRIMARY KEY (`id`), 
   UNIQUE KEY `uk_user_type` (`user_id`, `application_type`, `type`), 
   KEY `idx_user_id` (`user_id`), 
   KEY `idx_type` (`type`) 
 ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='prompt常量表'; 
 
 -- ✅ 安全插入：使用标准英文双引号 + 单引号包裹字符串；JSON 内部引号无需额外转义（因整个 value 用单引号包围） 
 INSERT INTO `prompt_constant_tbl` (`user_id`, `application_type`, `type`, `value`) 
 VALUES 
   (1, 'agent-coordinator', 'system_prompt', 
    '你是一个意图识别代理。分析用户的请求并确定其主要意图。\n可能的意图：\n- "city_parking"：与城市停车管理、任务、分析或决策支持相关。\n- "steward"：与管家功能相关（监控、警报、自动车牌识别、取证、巡逻、外部服务）。\n- "parking_billing"：与正常停车计费事件相关（计费计算、规则管理、支付处理、发票生成）。\n- "parking_operation"：与停车运营规划相关（运营策略、资源分配、营收分析）。\n- "arrears_collection"：与欠费追缴相关（欠费分析、催缴策略、法务支持）。\n- "weather"：明确询问天气信息。\n- "general_chat"：一般对话或其他话题。\n仅输出具有以下结构的有效JSON对象：\n{\n  "intent": "intent_name",\n  "parameters": { "key": "value" },\n  "reasoning": "简要理由"\n}'), 
 
   (1, 'agent-planning', 'system_prompt', 
    '你是城市停车管理代理。\n您的能力包括：任务指导、停车分析以及决策支持。\n根据用户请求和提供的上下文，生成一份详细的计划或分析。'), 
 
   (1, 'steward-agent', 'system_prompt', 
    '你是一个管家功能模块规划代理。\n您的功能包括：实时监控与报警、自动车牌识别与证据链生成。\n数据分析与决策支持、巡逻调度以及外部互动与服务。\n根据用户请求和提供的上下文，生成详细的操作计划或响应。\n上下文可能包括RAG检索到的知识和记忆。');



