USE `pg-platform-db`;
-- 创建知识库表
CREATE TABLE IF NOT EXISTS `rag_tbl` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `rag_name` varchar(50) NOT NULL COMMENT '知识库名称',
  `type` varchar(255) NOT NULL COMMENT '知识库类型',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态：0-禁用，1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `file_capacity` bigint(20) NOT NULL COMMENT '容量',
  `file_count` bigint(20) NOT NULL COMMENT '文件数量',
  `binding_user_id` bigint(20) NOT NULL COMMENT '绑定用户ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_rag_name` (`binding_user_id`, `rag_name`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库表';

-- 创建知识库表关联的文件
CREATE TABLE IF NOT EXISTS `rag_file_tbl` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_name` varchar(50) NOT NULL COMMENT '文件名称',
  `file_path` varchar(255) NOT NULL COMMENT '文件路径',
  `extension` varchar(255) NOT NULL COMMENT '文件扩展名',
  `embedding_process` bigint(20) NOT NULL COMMENT '嵌入进度',
  `file_embedding_offset` bigint(20) NOT NULL COMMENT '嵌入偏移量',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态：0-禁用，1-启用',
  `upload_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `file_char_count` bigint(20) NOT NULL COMMENT '字符数量',
  `recall_count` bigint(20) NOT NULL COMMENT '召回数量',
  `rag_id` bigint(20) NOT NULL COMMENT '知识库ID',
  `binding_user_id` bigint(20) NOT NULL COMMENT '绑定用户ID',
  `segmentation_type` varchar(255) NOT NULL COMMENT '分段类型',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rag_file_name` (`rag_id`, `file_name`),
  KEY `idx_status` (`status`),
  KEY `idx_rag_id` (`rag_id`),
  KEY `idx_user_rag_status` (`binding_user_id`, `rag_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文件表';

-- 创建知识片段内容及关联的文件
CREATE TABLE IF NOT EXISTS `rag_knowledge_segment_tbl` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '片段唯一ID',
  `file_id` bigint(20) NOT NULL COMMENT '关联文件ID',
  `binding_user_id` bigint(20) NOT NULL COMMENT '绑定用户ID',
  `title` varchar(255) NOT NULL DEFAULT '' COMMENT '片段标题',
  `content` text COMMENT '片段详细内容 (支持Markdown/HTML/纯文本)',
  `summary` varchar(500) DEFAULT '' COMMENT '内容摘要，用于列表展示',
  `snippet_type` varchar(50) DEFAULT 'text' COMMENT '片段类型: text文本, code代码, link链接, image图片描述等',
  `sort_index` int(11) DEFAULT '9999' COMMENT '排序索引，数字越小越靠前',
  `status` tinyint(4) DEFAULT '1' COMMENT '状态: 0-删除, 1-草稿, 2-已发布',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `recall_count` bigint(20) NOT NULL DEFAULT 0 COMMENT '召回次数',
  `last_search_time` datetime DEFAULT NULL COMMENT '最后搜索时间',
  `average_retrieval_score` decimal(5,3) DEFAULT NULL COMMENT '平均检索分数',
  `command_score` decimal(5,3) DEFAULT NULL COMMENT '命令评分',
  `relevance_score` decimal(5,3) DEFAULT NULL COMMENT '相关性评分',
  `is_noise` tinyint(1) DEFAULT '0' COMMENT '是否为噪声片段（0-否，1-是）',
  `is_redundant` tinyint(1) DEFAULT '0' COMMENT '是否为冗余片段（0-否，1-是）',
   -- 外键引用
  `qdrant_vector_id` VARCHAR(255),  -- Qdrant中的向量ID
  `neo4j_node_id` VARCHAR(255),     -- Neo4j中的节点ID
  PRIMARY KEY (`id`),
  KEY `idx_file_id` (`file_id`),
  KEY `idx_status_time` (`status`,`update_time`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_status_recall` (`status`,`recall_count`),
  KEY `idx_last_search_time` (`last_search_time`),
  KEY `idx_status_recall_time` (`status`,`recall_count`,`last_search_time`),
  KEY `idx_user_status_time` (`binding_user_id`, `status`, `update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识片段主表';

DROP TABLE IF EXISTS `memory_config`;
-- 创建记忆配置表（修正CHECK约束问题）
CREATE TABLE IF NOT EXISTS `memory_config` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `binding_user_id` bigint(20) NOT NULL COMMENT '绑定用户ID',
  `agent_id` varchar(100) NOT NULL COMMENT '智能体ID',
  `config_name` varchar(100) NOT NULL DEFAULT 'default' COMMENT '配置名称',
  
  -- 记忆衰减与遗忘配置
  `memory_half_life` int NOT NULL DEFAULT 24 COMMENT '记忆半衰期（小时）',
  `auto_forget_enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '启用自动遗忘低价值记忆（0-禁用，1-启用）',
  
  -- 评分规则权重（移除了CHECK约束，改为应用层验证）
  `importance_weight` decimal(4,3) NOT NULL DEFAULT 0.4 COMMENT '重要性权重',
  `freshness_weight` decimal(4,3) NOT NULL DEFAULT 0.3 COMMENT '新鲜度权重',
  `frequency_weight` decimal(4,3) NOT NULL DEFAULT 0.3 COMMENT '出现频次权重',
  
  -- 压缩与摘要规则
  `compress_trigger_count` int NOT NULL DEFAULT 200 COMMENT '压缩触发条数',
  `summary_style` varchar(50) DEFAULT 'compact_technical' COMMENT '摘要风格',
  
  -- 上下文短记忆配置
  `context_max_count` int NOT NULL DEFAULT 20 COMMENT '上下文最大条数',
  `context_retention_minutes` int NOT NULL DEFAULT 60 COMMENT '保留时长（分钟）',
  `single_item_max_chars` int NOT NULL DEFAULT 500 COMMENT '单条最大字符数',
  `important_context_to_long_term` tinyint(1) NOT NULL DEFAULT 1 COMMENT '重要上下文可写入长期记忆（0-否，1-是）',
  
  -- 元数据
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否激活（0-停用，1-激活）',
  `description` text COMMENT '配置描述',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_agent_config` (`binding_user_id`, `agent_id`, `config_name`),
  KEY `idx_user_agent_active` (`binding_user_id`, `agent_id`, `is_active`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='智能体记忆配置表';

-- 插入默认配置
INSERT INTO `memory_config` (
  `binding_user_id`, `agent_id`, `config_name`, `memory_half_life`, `auto_forget_enabled`,
  `importance_weight`, `freshness_weight`, `frequency_weight`,
  `compress_trigger_count`, `summary_style`, `context_max_count`,
  `context_retention_minutes`, `single_item_max_chars`, 
  `important_context_to_long_term`, `description`
) VALUES (
  0, 'default_agent', 'default_config', 24, 1,
  0.4, 0.3, 0.3, 200, 'compact_technical',
  20, 60, 500, 1,
  '默认记忆配置'
);

-- 应用角色管理
CREATE TABLE IF NOT EXISTS `application_role_tbl` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(50) NOT NULL COMMENT '文件名称',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态：0-禁用，1-启用',
  `upload_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `period_start_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '周期开始时间',
  `period_end_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '周期结束时间',
  `daily_activation_start_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '每天启用开始时间',
  `daily_activation_end_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '每天启用结束时间',
  `description` text COMMENT '角色描述',
  `prompt_template_id` bigint NOT NULL COMMENT '关联的模板ID',
  `binding_user_id` bigint(20) NOT NULL COMMENT '绑定用户ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role_name` (`binding_user_id`, `name`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`binding_user_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应用角色表';
