USE `pg-platform-db`;

-- Table structure for mcp_server_tbl
DROP TABLE IF EXISTS `mcp_server_tbl`;
CREATE TABLE `mcp_server_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `server_name` varchar(100) NOT NULL COMMENT 'MCP服务名称',
  `server_url` varchar(200) NOT NULL COMMENT 'MCP服务地址',
  `server_type` varchar(50) DEFAULT 'service' COMMENT '服务类型: service/hardware',
  `api_key` varchar(255) DEFAULT NULL COMMENT 'API Key',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_server_url` (`server_url`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='MCP服务配置表';

-- Table structure for mcp_tools_tbl
DROP TABLE IF EXISTS `mcp_tools_tbl`;
CREATE TABLE `mcp_tools_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '工具唯一名称',
  `display_name` varchar(200) DEFAULT NULL COMMENT '显示名称',
  `description_short` varchar(500) DEFAULT NULL COMMENT '简短描述(用于紧凑版)',
  `description_full` text COMMENT '完整描述',
  `tool_type` varchar(50) NOT NULL COMMENT '工具类型: function/service/device等',
  `category` varchar(100) DEFAULT NULL COMMENT '分类',
  `server_id` int DEFAULT NULL COMMENT '关联的MCP服务ID',
  `tags` json DEFAULT NULL COMMENT '标签数组',
  `primary_skill_id` int DEFAULT NULL COMMENT '主要关联技能ID',
  `related_skill_ids` json DEFAULT NULL COMMENT '相关技能ID数组',
  `skill_coverage_score` decimal(3,2) DEFAULT '0.00' COMMENT '技能覆盖度评分',
  `current_interface_version` varchar(20) DEFAULT 'v1',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活',
  `priority` tinyint DEFAULT '5' COMMENT '优先级(1-10)',
  `call_count_full` int DEFAULT '0' COMMENT '完整版调用次数',
  `call_count_compact` int DEFAULT '0' COMMENT '紧凑版调用次数',
  `total_token_usage_full` bigint DEFAULT '0' COMMENT '完整版总token使用量',
  `total_token_usage_compact` bigint DEFAULT '0' COMMENT '紧凑版总token使用量',
  `avg_skill_improvement_score` decimal(5,2) DEFAULT NULL COMMENT '平均技能提升分数',
  `mastery_contribution_score` decimal(3,2) DEFAULT NULL COMMENT '掌握度贡献评分',
  `learning_efficiency_score` decimal(5,2) DEFAULT NULL COMMENT '学习效率评分',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_type` (`tool_type`),
  KEY `idx_category` (`category`),
  KEY `idx_active_priority` (`is_active`,`priority`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_primary_skill` (`primary_skill_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='MCP工具主表';

-- Table structure for tool_interfaces_tbl
DROP TABLE IF EXISTS `tool_interfaces_tbl`;
CREATE TABLE `tool_interfaces_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tool_id` int NOT NULL COMMENT '工具ID',
  `interface_type` enum('full','compact') NOT NULL COMMENT '接口类型',
  `version` varchar(20) NOT NULL COMMENT '接口版本',
  `is_default` tinyint(1) DEFAULT '0' COMMENT '是否默认版本',
  `endpoint_url` varchar(1000) NOT NULL COMMENT '接口端点URL',
  `api_key` varchar(255) DEFAULT NULL COMMENT 'API Key',
  `http_method` varchar(10) DEFAULT 'POST' COMMENT 'HTTP方法',
  `timeout_ms` int DEFAULT '30000' COMMENT '超时时间',
  `description` text COMMENT '接口描述(针对此版本)',
  `input_schema` json DEFAULT NULL COMMENT '输入JSON Schema',
  `output_schema` json DEFAULT NULL COMMENT '输出JSON Schema',
  `examples` json DEFAULT NULL COMMENT '调用示例数组',
  `target_skill_level` enum('novice','intermediate','advanced','expert') DEFAULT 'novice' COMMENT '目标技能水平',
  `learning_curve_score` decimal(3,2) DEFAULT NULL COMMENT '学习曲线评分',
  `skill_mastery_weight` decimal(3,2) DEFAULT '1.00' COMMENT '技能掌握度权重',
  `estimated_token_length` int DEFAULT NULL COMMENT '预估的token长度(当包含在提示词中时)',
  `parameter_count` int DEFAULT NULL COMMENT '参数数量',
  `avg_llm_accuracy` float DEFAULT NULL COMMENT 'LLM使用此版本时的平均准确率',
  `avg_response_time` int DEFAULT NULL COMMENT '平均响应时间(ms)',
  `success_rate` float DEFAULT NULL COMMENT '成功率',
  `call_count` int DEFAULT '0' COMMENT '调用次数',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tool_interface` (`tool_id`,`interface_type`,`version`),
  KEY `idx_tool_id` (`tool_id`),
  KEY `idx_type_version` (`interface_type`,`version`),
  KEY `idx_token_length` (`estimated_token_length`),
  KEY `idx_skill_level` (`target_skill_level`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工具接口版本表';

-- Table structure for tool_parameters_tbl
DROP TABLE IF EXISTS `tool_parameters_tbl`;
CREATE TABLE `tool_parameters_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `interface_id` int NOT NULL COMMENT '接口ID',
  `param_name` varchar(100) NOT NULL COMMENT '参数名',
  `display_name` varchar(200) DEFAULT NULL COMMENT '显示名称',
  `description_full` text COMMENT '完整描述',
  `description_short` varchar(500) DEFAULT NULL COMMENT '简短描述',
  `data_type` varchar(50) NOT NULL COMMENT '数据类型: string/number/boolean/array/object',
  `required` tinyint(1) DEFAULT '0' COMMENT '是否必填',
  `default_value` text COMMENT '默认值',
  `example_value` text COMMENT '示例值',
  `complexity_level` enum('easy','medium','hard') DEFAULT 'medium' COMMENT '参数复杂度',
  `learning_importance` tinyint DEFAULT '3' COMMENT '学习重要性(1-5)',
  `skill_learning_tags` json DEFAULT NULL COMMENT '技能学习标签',
  `include_in_compact` tinyint(1) DEFAULT '1' COMMENT '是否包含在紧凑版',
  `compact_priority` tinyint DEFAULT '5' COMMENT '紧凑版中的优先级(1-10, 1最高)',
  `importance_score` float DEFAULT '1' COMMENT '重要性评分(基于使用频率)',
  `validation_rules` json DEFAULT NULL COMMENT '验证规则',
  `allowed_values` json DEFAULT NULL COMMENT '允许的值列表',
  `min_value` decimal(20,6) DEFAULT NULL COMMENT '最小值',
  `max_value` decimal(20,6) DEFAULT NULL COMMENT '最大值',
  `estimated_token_length` int DEFAULT NULL COMMENT '预估token长度',
  `common_values` json DEFAULT NULL COMMENT '常用值数组(供LLM参考)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_interface_param` (`interface_id`,`param_name`),
  KEY `idx_interface_id` (`interface_id`),
  KEY `idx_compact_priority` (`include_in_compact`,`compact_priority`),
  KEY `idx_learning_importance` (`learning_importance`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工具参数表';

-- Table structure for tool_capabilities_tbl
DROP TABLE IF EXISTS `tool_capabilities_tbl`;
CREATE TABLE `tool_capabilities_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tool_id` int NOT NULL COMMENT '工具ID',
  `capability_name` varchar(100) NOT NULL COMMENT '能力名称',
  `display_name` varchar(200) DEFAULT NULL COMMENT '显示名称',
  `description_full` text COMMENT '完整能力描述',
  `description_short` varchar(500) DEFAULT NULL COMMENT '简短描述',
  `skill_id` int DEFAULT NULL COMMENT '关联技能ID',
  `skill_impact_level` enum('low','medium','high','critical') DEFAULT 'medium' COMMENT '对技能的影响程度',
  `mastery_requirement` enum('none','basic','intermediate','advanced') DEFAULT 'none' COMMENT '所需掌握度',
  `available_in_full` tinyint(1) DEFAULT '1' COMMENT '完整版中可用',
  `available_in_compact` tinyint(1) DEFAULT '1' COMMENT '紧凑版中可用',
  `compact_description` varchar(300) DEFAULT NULL COMMENT '紧凑版中的超短描述',
  `full_token_estimate` int DEFAULT NULL COMMENT '完整描述预估token数',
  `compact_token_estimate` int DEFAULT NULL COMMENT '紧凑描述预估token数',
  `usage_frequency` float DEFAULT '0' COMMENT '使用频率',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tool_capability` (`tool_id`,`capability_name`),
  KEY `idx_tool_id` (`tool_id`),
  KEY `idx_availability` (`available_in_full`,`available_in_compact`),
  KEY `idx_skill_capability` (`skill_id`,`skill_impact_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工具能力表';

-- Table structure for tool_usage_stats_tbl
DROP TABLE IF EXISTS `tool_usage_stats_tbl`;
CREATE TABLE `tool_usage_stats_tbl` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tool_id` int NOT NULL,
  `skill_id` int NOT NULL COMMENT '关联技能ID（新增）',
  `user_id` varchar(100) NOT NULL COMMENT '用户ID（新增）',
  `interface_type` enum('full','compact') NOT NULL COMMENT '使用的接口类型',
  `interface_version` varchar(20) NOT NULL,
  `caller_type` varchar(50) DEFAULT NULL COMMENT '调用者类型: human/llm/agent',
  `caller_id` varchar(100) DEFAULT NULL COMMENT '调用者ID',
  `prompt_token_count` int DEFAULT NULL COMMENT '提示词token数',
  `input_token_count` int DEFAULT NULL COMMENT '输入token数',
  `output_token_count` int DEFAULT NULL COMMENT '输出token数',
  `total_token_count` int DEFAULT NULL COMMENT '总token数',
  `estimated_saved_tokens` int DEFAULT NULL COMMENT '预估节省的token数(与完整版相比)',
  `success` tinyint DEFAULT '0' COMMENT '是否成功',
  `response_time_ms` int DEFAULT NULL COMMENT '响应时间',
  `error_code` varchar(100) DEFAULT NULL COMMENT '错误码',
  `used_parameters` json DEFAULT NULL COMMENT '实际使用的参数',
  `result_quality` tinyint DEFAULT NULL COMMENT '结果质量评分(1-5)',
  `mastery_before` decimal(5,2) DEFAULT NULL COMMENT '使用前技能掌握度',
  `mastery_after` decimal(5,2) DEFAULT NULL COMMENT '使用后技能掌握度',
  `mastery_delta` decimal(5,2) DEFAULT NULL COMMENT '掌握度变化',
  `learning_efficiency` decimal(5,2) DEFAULT NULL COMMENT '学习效率评分',
  `difficulty_perception` enum('too_easy','just_right','too_hard') DEFAULT NULL COMMENT '难度感知',
  `called_at` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
  `date_key` date GENERATED ALWAYS AS (cast(`called_at` as date)) STORED NOT NULL COMMENT '日期分区键',
  PRIMARY KEY (`id`,`date_key`),
  KEY `idx_tool_date` (`tool_id`,`date_key`),
  KEY `idx_skill_tool` (`skill_id`,`tool_id`),
  KEY `idx_user_skill_tool` (`user_id`,`skill_id`,`tool_id`),
  KEY `idx_interface_type` (`interface_type`),
  KEY `idx_caller_type` (`caller_type`),
  KEY `idx_called_at` (`called_at`),
  KEY `idx_success_time` (`success`,`response_time_ms`),
  KEY `idx_mastery_change` (`mastery_delta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工具使用统计表（含技能维度）'
/*!50100 PARTITION BY RANGE (((year(`date_key`) * 100) + month(`date_key`)))
(PARTITION p202501 VALUES LESS THAN (202502) ENGINE = InnoDB,
 PARTITION p202502 VALUES LESS THAN (202503) ENGINE = InnoDB,
 PARTITION p202503 VALUES LESS THAN (202504) ENGINE = InnoDB,
 PARTITION p202504 VALUES LESS THAN (202505) ENGINE = InnoDB,
 PARTITION p_future VALUES LESS THAN MAXVALUE ENGINE = InnoDB) */;

-- Table structure for tool_permissions_tbl
DROP TABLE IF EXISTS `tool_permissions_tbl`;
CREATE TABLE `tool_permissions_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tool_id` int NOT NULL COMMENT '工具ID',
  `user_type` enum('all','role','user','group') NOT NULL COMMENT '用户类型',
  `user_id` varchar(100) DEFAULT NULL COMMENT '用户/角色/组ID',
  `permission_level` enum('read','execute','admin') NOT NULL COMMENT '权限级别',
  `rate_limit` int DEFAULT '0' COMMENT '调用频率限制(次/分钟)',
  `valid_from` datetime DEFAULT NULL COMMENT '有效期开始',
  `valid_to` datetime DEFAULT NULL COMMENT '有效期结束',
  `required_skill_level` enum('novice','intermediate','advanced','expert') DEFAULT NULL COMMENT '所需技能等级',
  `minimum_mastery_score` decimal(5,2) DEFAULT '0.00' COMMENT '最低掌握分数',
  `skill_prerequisites` json DEFAULT NULL COMMENT '技能先决条件',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tool_permission` (`tool_id`,`user_type`,`user_id`),
  KEY `idx_tool_id` (`tool_id`),
  KEY `idx_user` (`user_type`,`user_id`),
  KEY `idx_skill_permission` (`required_skill_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工具权限表（含技能要求）';

-- Table structure for tool_relationships_tbl
DROP TABLE IF EXISTS `tool_relationships_tbl`;
CREATE TABLE `tool_relationships_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `source_tool_id` int NOT NULL COMMENT '源工具ID',
  `target_tool_id` int NOT NULL COMMENT '目标工具ID',
  `relationship_type` enum('depends_on','recommends','alternative','prerequisite','similar','skill_related') NOT NULL COMMENT '关系类型',
  `weight` float DEFAULT '1' COMMENT '关系权重',
  `shared_skill_id` int DEFAULT NULL COMMENT '共享技能ID',
  `skill_transfer_score` decimal(3,2) DEFAULT NULL COMMENT '技能迁移分数',
  `learning_path_order` int DEFAULT NULL COMMENT '学习路径顺序',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tool_relationship` (`source_tool_id`,`target_tool_id`,`relationship_type`),
  KEY `idx_source_tool` (`source_tool_id`),
  KEY `idx_target_tool` (`target_tool_id`),
  KEY `idx_relationship` (`relationship_type`,`weight`),
  KEY `idx_skill_relationship` (`shared_skill_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工具关系表（含技能维度）';

-- Table structure for skill_definitions_tbl
DROP TABLE IF EXISTS `skill_definitions_tbl`;
CREATE TABLE `skill_definitions_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `skill_code` varchar(50) NOT NULL COMMENT '技能编码',
  `skill_name` varchar(100) NOT NULL COMMENT '技能名称',
  `display_name` varchar(200) DEFAULT NULL COMMENT '显示名称',
  `description` text COMMENT '技能描述',
  `category` varchar(50) NOT NULL COMMENT '技能类别',
  `domain` varchar(50) NOT NULL COMMENT '技能领域',
  `complexity_level` enum('beginner','intermediate','advanced','expert') NOT NULL DEFAULT 'beginner',
  `essential_tool_ids` json DEFAULT NULL COMMENT '必需工具ID列表',
  `recommended_tool_ids` json DEFAULT NULL COMMENT '推荐工具ID列表',
  `alternative_tool_ids` json DEFAULT NULL COMMENT '替代工具ID列表',
  `estimated_hours` int DEFAULT NULL COMMENT '预计学习时长(小时)',
  `prerequisite_skill_ids` json DEFAULT NULL COMMENT '先修技能ID列表',
  `learning_objectives` json DEFAULT NULL COMMENT '学习目标',
  `common_applications` json DEFAULT NULL COMMENT '常见应用场景',
  `market_demand_score` decimal(3,2) DEFAULT NULL COMMENT '市场需求评分',
  `average_mastery_time` int DEFAULT NULL COMMENT '平均掌握时间(天)',
  `popularity_score` decimal(3,2) DEFAULT NULL COMMENT '受欢迎度评分',
  `is_active` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用',
  `version` varchar(20) NOT NULL DEFAULT 'v1.0' COMMENT '技能版本',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_skill_code` (`skill_code`),
  KEY `idx_category` (`category`),
  KEY `idx_domain` (`domain`),
  KEY `idx_complexity` (`complexity_level`),
  KEY `idx_active` (`is_active`,`popularity_score` DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='技能定义表';

-- Table structure for user_skill_mastery_tbl
DROP TABLE IF EXISTS `user_skill_mastery_tbl`;
CREATE TABLE `user_skill_mastery_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` varchar(36) NOT NULL COMMENT '用户ID',
  `skill_id` int NOT NULL COMMENT '技能ID',
  `skill_version` varchar(20) NOT NULL COMMENT '技能版本',
  `mastery_level` enum('novice','intermediate','advanced','expert','master') NOT NULL DEFAULT 'novice',
  `mastery_score` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '掌握分数(0-100)',
  `confidence_level` decimal(3,2) NOT NULL DEFAULT '0.00' COMMENT '置信度(0-1)',
  `primary_tool_id` int DEFAULT NULL COMMENT '主要使用工具ID',
  `tool_proficiency_scores` json DEFAULT NULL COMMENT '工具熟练度评分{tool_id: score}',
  `preferred_interface_type` enum('full','compact','auto') DEFAULT 'auto' COMMENT '偏好接口类型',
  `tool_usage_distribution` json DEFAULT NULL COMMENT '工具使用分布',
  `learning_progress` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '学习进度(0-100)',
  `learning_path_id` int DEFAULT NULL COMMENT '学习路径ID',
  `next_recommendation` json DEFAULT NULL COMMENT '下一步建议',
  `learning_priority` enum('low','medium','high','urgent') DEFAULT 'medium' COMMENT '学习优先级',
  `use_count` int NOT NULL DEFAULT '0' COMMENT '使用次数',
  `success_count` int NOT NULL DEFAULT '0' COMMENT '成功次数',
  `recent_accuracy` decimal(5,2) DEFAULT NULL COMMENT '近期准确率',
  `avg_execution_time_ms` bigint DEFAULT NULL COMMENT '平均执行时间(毫秒)',
  `avg_tool_accuracy` decimal(5,2) DEFAULT NULL COMMENT '平均工具准确率',
  `best_performing_tool_id` int DEFAULT NULL COMMENT '最佳表现工具ID',
  `tool_learning_curve_score` decimal(3,2) DEFAULT NULL COMMENT '工具学习曲线评分',
  `preferred_config` json DEFAULT NULL COMMENT '偏好配置',
  `customizations` json DEFAULT NULL COMMENT '个性化定制',
  `favorite` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否收藏',
  `rating` tinyint DEFAULT NULL COMMENT '用户评分(1-5)',
  `first_used_at` datetime(3) DEFAULT NULL COMMENT '首次使用时间',
  `last_used_at` datetime(3) DEFAULT NULL COMMENT '最后使用时间',
  `last_improved_at` datetime(3) DEFAULT NULL COMMENT '最后提升时间',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_skill` (`user_id`,`skill_id`),
  KEY `idx_user_mastery` (`user_id`,`mastery_level`),
  KEY `idx_skill_users` (`skill_id`,`mastery_level`),
  KEY `idx_favorites` (`user_id`,`favorite`),
  KEY `idx_last_used` (`user_id`,`last_used_at`),
  KEY `idx_tool_proficiency` (`primary_tool_id`,`mastery_score`),
  KEY `idx_skill_tool_user` (`skill_id`,`primary_tool_id`,`user_id`),
  CONSTRAINT `user_skill_mastery_tbl_chk_1` CHECK ((`rating` between 1 and 5))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户技能掌握表（含工具维度）';

-- Table structure for user_skill_learning_records_tbl
DROP TABLE IF EXISTS `user_skill_learning_records_tbl`;
CREATE TABLE `user_skill_learning_records_tbl` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` varchar(36) NOT NULL COMMENT '用户ID',
  `skill_id` int NOT NULL COMMENT '技能ID',
  `learning_session_id` varchar(64) NOT NULL COMMENT '学习会话ID',
  `primary_tool_id` int DEFAULT NULL COMMENT '主要使用工具ID',
  `tool_interface_type` enum('full','compact') DEFAULT NULL COMMENT '使用的工具接口类型',
  `tools_used` json DEFAULT NULL COMMENT '使用的工具列表[{tool_id, interface_type, duration_ms}]',
  `tool_switches` int DEFAULT '0' COMMENT '工具切换次数',
  `learning_type` enum('practice','tutorial','challenge','review','discovery','assessment') NOT NULL,
  `learning_method` enum('guided','exploratory','reinforcement','social','adaptive') NOT NULL DEFAULT 'guided',
  `difficulty_level` enum('easy','medium','hard','expert') NOT NULL DEFAULT 'medium',
  `learning_scenario` varchar(200) DEFAULT NULL COMMENT '学习场景',
  `learning_goals` json DEFAULT NULL COMMENT '学习目标',
  `provided_examples` json DEFAULT NULL COMMENT '提供的示例',
  `attempted_solutions` json DEFAULT NULL COMMENT '尝试的解决方案',
  `success` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否成功',
  `accuracy_score` decimal(5,2) DEFAULT NULL COMMENT '准确率得分',
  `efficiency_score` decimal(5,2) DEFAULT NULL COMMENT '效率得分',
  `quality_score` decimal(5,2) DEFAULT NULL COMMENT '质量得分',
  `completion_time_ms` bigint DEFAULT NULL COMMENT '完成时间',
  `tool_accuracy` decimal(5,2) DEFAULT NULL COMMENT '工具使用准确率',
  `tool_efficiency` decimal(5,2) DEFAULT NULL COMMENT '工具使用效率',
  `interface_suitability` enum('perfect','good','fair','poor') DEFAULT NULL COMMENT '接口适用性',
  `self_assessment` json DEFAULT NULL COMMENT '自我评估',
  `system_feedback` json DEFAULT NULL COMMENT '系统反馈',
  `ai_feedback` json DEFAULT NULL COMMENT 'AI反馈',
  `improvement_suggestions` text COMMENT '改进建议',
  `mastery_before` decimal(5,2) DEFAULT NULL COMMENT '学习前掌握度',
  `mastery_after` decimal(5,2) DEFAULT NULL COMMENT '学习后掌握度',
  `mastery_delta` decimal(5,2) DEFAULT NULL COMMENT '掌握度变化',
  `confidence_change` decimal(3,2) DEFAULT NULL COMMENT '置信度变化',
  `enjoyment_level` tinyint DEFAULT NULL COMMENT '乐趣程度(1-5)',
  `frustration_level` tinyint DEFAULT NULL COMMENT '挫折程度(1-5)',
  `difficulty_perception` enum('too_easy','just_right','too_hard') DEFAULT NULL COMMENT '难度感知',
  `willingness_to_repeat` tinyint DEFAULT NULL COMMENT '重复意愿(1-5)',
  `learning_duration_ms` bigint NOT NULL COMMENT '学习时长',
  `interaction_count` int NOT NULL DEFAULT '0' COMMENT '交互次数',
  `error_count` int NOT NULL DEFAULT '0' COMMENT '错误次数',
  `hint_requests` int NOT NULL DEFAULT '0' COMMENT '提示请求次数',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `learning_date` date GENERATED ALWAYS AS (cast(`created_at` as date)) STORED,
  PRIMARY KEY (`id`),
  KEY `idx_user_learning` (`user_id`,`skill_id`,`learning_date`),
  KEY `idx_skill_learning` (`skill_id`,`learning_type`,`learning_date`),
  KEY `idx_learning_session` (`learning_session_id`),
  KEY `idx_success_mastery` (`success`,`mastery_delta`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_tool_learning` (`primary_tool_id`,`skill_id`,`created_at`),
  KEY `idx_interface_performance` (`tool_interface_type`,`tool_accuracy`,`tool_efficiency`),
  CONSTRAINT `user_skill_learning_records_tbl_chk_1` CHECK ((`enjoyment_level` between 1 and 5)),
  CONSTRAINT `user_skill_learning_records_tbl_chk_2` CHECK ((`frustration_level` between 1 and 5)),
  CONSTRAINT `user_skill_learning_records_tbl_chk_3` CHECK ((`willingness_to_repeat` between 1 and 5))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户技能学习记录表（含工具使用）';

-- MCP服务配置表（用于动态管理MCP服务连接）
CREATE TABLE IF NOT EXISTS `mcp_server_tbl` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `server_name` VARCHAR(100) NOT NULL COMMENT 'MCP服务名称',
  `base_url` VARCHAR(255) NOT NULL COMMENT '服务基地址',
  `api_key` VARCHAR(255) DEFAULT NULL COMMENT 'API Key',
  `timeout` INT DEFAULT 30 COMMENT '超时时间(秒)',
  `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_server_name` (`server_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MCP服务配置表';


