-- 创建pg-platform-db数据库
CREATE DATABASE IF NOT EXISTS `pg-platform-db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE `pg-platform-db`;

-- 创建用户表
CREATE TABLE IF NOT EXISTS `user_tbl` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password` varchar(255) NOT NULL COMMENT '密码',
  `real_name` varchar(50) DEFAULT NULL COMMENT '真实姓名',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `phone` varchar(20) DEFAULT NULL COMMENT '手机号',
  `avatar` varchar(255) DEFAULT NULL COMMENT '头像',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态：0-禁用，1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) DEFAULT NULL COMMENT '更新人',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_email` (`email`),
  KEY `idx_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 创建角色表
CREATE TABLE IF NOT EXISTS `role_tbl` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `role_code` varchar(50) NOT NULL COMMENT '角色编码',
  `role_name` varchar(100) NOT NULL COMMENT '角色名称',
  `upper_level_role_code` varchar(50) NOT NULL COMMENT '上一级角色',
  `next_level_role_code` varchar(50) NOT NULL COMMENT '下一级角色',
  `description` varchar(500) DEFAULT NULL COMMENT '角色描述',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态：0-禁用，1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `create_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) DEFAULT NULL COMMENT '更新人',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 创建用户角色关联表
CREATE TABLE IF NOT EXISTS `user_role_tbl` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `role_id` bigint(20) NOT NULL COMMENT '角色ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `create_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`, `role_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_role_id` (`role_id`),
  CONSTRAINT `fk_user_role_role_id` FOREIGN KEY (`role_id`) REFERENCES `role_tbl` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_role_user_id` FOREIGN KEY (`user_id`) REFERENCES `user_tbl` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';

-- 创建边缘计算单元表
CREATE TABLE IF NOT EXISTS `edge_unit_tbl` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `unit_code` varchar(50) NOT NULL COMMENT '边缘单元编码',
  `unit_name` varchar(100) NOT NULL COMMENT '边缘单元名称',
  `unit_type` varchar(50) NOT NULL COMMENT '边缘单元类型',
  `ip_address` varchar(50) NOT NULL COMMENT 'IP地址',
  `mac_address` varchar(50) NOT NULL COMMENT 'MAC地址',
  `port` int(11) NOT NULL COMMENT '端口号',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态：0-离线，1-在线',
  `location` varchar(255) DEFAULT NULL COMMENT '地理位置',
  `description` varchar(500) DEFAULT NULL COMMENT '描述',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `binding_user` bigint(20) NOT NULL COMMENT '绑定用户ID',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_unit_code` (`unit_code`),
  KEY `idx_unit_type` (`unit_type`),
  KEY `idx_ip_address` (`ip_address`),
  KEY `idx_status` (`status`),
  KEY `idx_binding_user` (`binding_user`),
  CONSTRAINT `fk_edge_unit_binding_user` FOREIGN KEY (`binding_user`) REFERENCES `user_tbl` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='边缘计算单元表';

-- 创建智能设备表
CREATE TABLE IF NOT EXISTS `device_tbl` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `device_code` varchar(50) NOT NULL COMMENT '设备编码',
  `device_name` varchar(100) NOT NULL COMMENT '设备名称',
  `device_type` varchar(50) NOT NULL COMMENT '设备类型',
  `edge_unit_id` bigint(20) NOT NULL COMMENT '所属边缘单元ID',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态：0-离线，1-在线',
  `protocol` varchar(50) DEFAULT NULL COMMENT '通信协议',
  `ip_address` varchar(50) DEFAULT NULL COMMENT 'IP地址',
  `port` int(11) DEFAULT NULL COMMENT '端口号',
  `location` varchar(255) DEFAULT NULL COMMENT '设备位置',
  `description` varchar(500) DEFAULT NULL COMMENT '设备描述',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `binding_user` bigint(20) NOT NULL COMMENT '绑定用户ID',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_device_code` (`device_code`),
  KEY `idx_device_type` (`device_type`),
  KEY `idx_edge_unit_id` (`edge_unit_id`),
  KEY `idx_status` (`status`),
  KEY `idx_binding_user` (`binding_user`),
  KEY `idx_protocol` (`protocol`),
  CONSTRAINT `fk_device_edge_unit_id` FOREIGN KEY (`edge_unit_id`) REFERENCES `edge_unit_tbl` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_device_binding_user` FOREIGN KEY (`binding_user`) REFERENCES `user_tbl` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能设备表';

-- 初始化管理员用户
INSERT INTO `user_tbl` (`username`, `password`, `real_name`, `email`, `create_by`) VALUES 
('admin', '$2b$12$srRpLoHU7/MAM4YLAzqHnesDN/19jW3UQBfIVKGcpEAes56cxNyJe', '系统管理员', 'admin@pg-platform.com', 'system');

-- 初始化角色
INSERT INTO `role_tbl` (`role_code`, `role_name`, `upper_level_role_code`, `next_level_role_code`, `description`, `create_by`) VALUES 
('ADMIN', '系统管理员', '', '', '系统管理员，拥有所有权限', 'system'),
('USER', '普通用户', 'ADMIN', '', '普通用户，拥有基本操作权限', 'system'),
('OPERATOR', '运维人员', 'ADMIN', '', '运维人员，负责设备和边缘单元管理', 'system');

-- 关联管理员用户和角色
INSERT INTO `user_role_tbl` (`user_id`, `role_id`, `create_by`) 
SELECT u.id, r.id, 'system' 
FROM `user_tbl` u, `role_tbl` r 
WHERE u.username = 'admin' AND r.role_code = 'ADMIN';
