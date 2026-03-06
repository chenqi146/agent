
USE `pg-platform-db`;

-- mcp-service专用工具表
DROP TABLE IF EXISTS `ms_tools_tbl`;
CREATE TABLE `ms_tools_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '工具唯一名称',
  `display_name` varchar(200) DEFAULT NULL COMMENT '显示名称',
  `description_short` varchar(500) DEFAULT NULL COMMENT '简短描述',
  `description_full` text COMMENT '完整描述',
  `tool_type` varchar(50) NOT NULL COMMENT '工具类型: function/service/device',
  `category` varchar(100) DEFAULT NULL COMMENT '分类',
  `tags` json DEFAULT NULL COMMENT '标签',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ms_tool_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='MCP服务专用工具表';

-- mcp-service专用接口表
DROP TABLE IF EXISTS `ms_tool_interfaces_tbl`;
CREATE TABLE `ms_tool_interfaces_tbl` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tool_id` int NOT NULL COMMENT '工具ID',
  `interface_type` enum('full','compact') NOT NULL COMMENT '接口类型',
  `version` varchar(20) DEFAULT 'v1' COMMENT '版本',
  `is_default` tinyint(1) DEFAULT '0',
  `endpoint_url` varchar(1000) NOT NULL COMMENT '端点URL',
  `description` text COMMENT '描述',
  `input_schema` json DEFAULT NULL COMMENT '输入Schema',
  `output_schema` json DEFAULT NULL COMMENT '输出Schema',
  `estimated_token_length` int DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ms_tool_interface` (`tool_id`,`interface_type`,`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='MCP服务专用工具接口表';
