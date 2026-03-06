// ==========================================
// 路侧停车管理知识库本体 - 简洁版本
// 从文档中提取的核心概念和关系
// ==========================================

// 0. 清理现有数据
MATCH (n) DETACH DELETE n;
RETURN "已清理所有数据" AS message;

// ------------------------------------------
// 1. 实体类定义（从文档中提取的核心概念）
// ------------------------------------------

// 设备类实体
CREATE (:EntityClass {name: "AlarmRule", description: "告警规则"});
CREATE (:EntityClass {name: "Alarm", description: "业务告警"});
CREATE (:EntityClass {name: "Device", description: "基础设备"});
CREATE (:EntityClass {name: "EdgeDevice", description: "边缘计算设备"});
CREATE (:EntityClass {name: "Camera", description: "摄像头"});
CREATE (:EntityClass {name: "PTZCamera", description: "球机摄像头"});
CREATE (:EntityClass {name: "BulletCamera", description: "枪机摄像头"});

// 业务类实体
CREATE (:EntityClass {name: "AgentMetadata", description: "智能体元数据"});
CREATE (:EntityClass {name: "BusinessProcess", description: "通用业务流程"});
CREATE (:EntityClass {name: "LicensePlateRecognition", description: "摄像头抄牌流程"});
CREATE (:EntityClass {name: "PaymentProcessing", description: "缴费处理流程"});
CREATE (:EntityClass {name: "ArrearsCollection", description: "欠费追缴处理流程"});
CREATE (:EntityClass {name: "ParkingPolicy", description: "停车政策"});
CREATE (:EntityClass {name: "ParkingManagement", description: "停车管理流程"});
CREATE (:EntityClass {name: "IllegalParkingProcessing", description: "违停处理流程"});

// ------------------------------------------
// 2. 实体属性定义
// ------------------------------------------

// 告警相关属性
CREATE (:EntityProperty {name: "level", data_type: "ENUM", allowed_values: ["Critical", "High", "Medium", "Low"]});
CREATE (:EntityProperty {name: "alarmType", data_type: "STRING"});
CREATE (:EntityProperty {name: "occurredTime", data_type: "DATETIME"});

// 设备相关属性
CREATE (:EntityProperty {name: "deviceId", data_type: "STRING"});
CREATE (:EntityProperty {name: "ipAddress", data_type: "STRING"});
CREATE (:EntityProperty {name: "installLocation", data_type: "STRING"});
CREATE (:EntityProperty {name: "deviceStatus", data_type: "ENUM", allowed_values: ["Online", "Offline", "Error"]});

// 业务相关属性
CREATE (:EntityProperty {name: "plateNumber", data_type: "STRING"});
CREATE (:EntityProperty {name: "paymentStatus", data_type: "ENUM", allowed_values: ["Paid", "Unpaid", "Pending"]});
CREATE (:EntityProperty {name: "amount", data_type: "FLOAT"});
CREATE (:EntityProperty {name: "policyContent", data_type: "STRING"});
CREATE (:EntityProperty {name: "agentId", data_type: "STRING"});

// ------------------------------------------
// 3. 实体关系定义
// ------------------------------------------

CREATE (:EntityRelation {name: "MONITORS", description: "监控关系"});
CREATE (:EntityRelation {name: "CONTROLS", description: "控制/管理"});
CREATE (:EntityRelation {name: "CAPTURES", description: "抓拍/采集"});
CREATE (:EntityRelation {name: "GENERATES", description: "产生"});
CREATE (:EntityRelation {name: "EXECUTES", description: "执行"});
CREATE (:EntityRelation {name: "GOVERNS", description: "指导/约束"});
CREATE (:EntityRelation {name: "INITIATES", description: "触发"});
CREATE (:EntityRelation {name: "PROCESSES", description: "处理"});
CREATE (:EntityRelation {name: "HANDLES", description: "处置"});
CREATE (:EntityRelation {name: "TRIGGERS_ARREARS", description: "触发欠费追缴"});

// ------------------------------------------
// 4. 实体-属性关联
// ------------------------------------------

// AlarmRule
MATCH (c:EntityClass {name: "AlarmRule"}), (p:EntityProperty {name: "level"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);

// Alarm
MATCH (c:EntityClass {name: "Alarm"}), (p:EntityProperty {name: "alarmType"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);
MATCH (c:EntityClass {name: "Alarm"}), (p:EntityProperty {name: "occurredTime"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);
MATCH (c:EntityClass {name: "Alarm"}), (p:EntityProperty {name: "level"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);

// Device
MATCH (c:EntityClass {name: "Device"}), (p:EntityProperty {name: "deviceId"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);
MATCH (c:EntityClass {name: "Device"}), (p:EntityProperty {name: "ipAddress"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);
MATCH (c:EntityClass {name: "Device"}), (p:EntityProperty {name: "deviceStatus"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);

// Camera
MATCH (c:EntityClass {name: "Camera"}), (p:EntityProperty {name: "installLocation"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);

// AgentMetadata
MATCH (c:EntityClass {name: "AgentMetadata"}), (p:EntityProperty {name: "agentId"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);

// LicensePlateRecognition
MATCH (c:EntityClass {name: "LicensePlateRecognition"}), (p:EntityProperty {name: "plateNumber"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);
MATCH (c:EntityClass {name: "LicensePlateRecognition"}), (p:EntityProperty {name: "occurredTime"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);

// PaymentProcessing
MATCH (c:EntityClass {name: "PaymentProcessing"}), (p:EntityProperty {name: "amount"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);
MATCH (c:EntityClass {name: "PaymentProcessing"}), (p:EntityProperty {name: "paymentStatus"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);

// ParkingPolicy
MATCH (c:EntityClass {name: "ParkingPolicy"}), (p:EntityProperty {name: "policyContent"}) 
CREATE (c)-[:HAS_PROPERTY]->(p);

// ------------------------------------------
// 5. 实体-关系约束
// ------------------------------------------

// AlarmRule MONITORS Device
MATCH (from:EntityClass {name: "AlarmRule"}), (to:EntityClass {name: "Device"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "MONITORS"}]->(to);

// EdgeDevice CONTROLS Camera
MATCH (from:EntityClass {name: "EdgeDevice"}), (to:EntityClass {name: "Camera"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "CONTROLS"}]->(to);

// Camera CAPTURES LicensePlateRecognition
MATCH (from:EntityClass {name: "Camera"}), (to:EntityClass {name: "LicensePlateRecognition"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "CAPTURES"}]->(to);

// LicensePlateRecognition INITIATES ParkingManagement
MATCH (from:EntityClass {name: "LicensePlateRecognition"}), (to:EntityClass {name: "ParkingManagement"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "INITIATES"}]->(to);

// ParkingManagement PROCESSES PaymentProcessing
MATCH (from:EntityClass {name: "ParkingManagement"}), (to:EntityClass {name: "PaymentProcessing"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "PROCESSES"}]->(to);

// ParkingManagement HANDLES IllegalParkingProcessing
MATCH (from:EntityClass {name: "ParkingManagement"}), (to:EntityClass {name: "IllegalParkingProcessing"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "HANDLES"}]->(to);

// ParkingPolicy GOVERNS ParkingManagement
MATCH (from:EntityClass {name: "ParkingPolicy"}), (to:EntityClass {name: "ParkingManagement"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "GOVERNS"}]->(to);

// AgentMetadata EXECUTES BusinessProcess
MATCH (from:EntityClass {name: "AgentMetadata"}), (to:EntityClass {name: "BusinessProcess"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "EXECUTES"}]->(to);

// PaymentProcessing TRIGGERS_ARREARS ArrearsCollection
MATCH (from:EntityClass {name: "PaymentProcessing"}), (to:EntityClass {name: "ArrearsCollection"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "TRIGGERS_ARREARS"}]->(to);

// IllegalParkingProcessing GENERATES Alarm
MATCH (from:EntityClass {name: "IllegalParkingProcessing"}), (to:EntityClass {name: "Alarm"}) 
CREATE (from)-[:CAN_RELATE_VIA {relation: "GENERATES"}]->(to);

// 继承关系
MATCH (sub:EntityClass {name: "PTZCamera"}), (super:EntityClass {name: "Camera"}) 
CREATE (sub)-[:IS_A]->(super);

MATCH (sub:EntityClass {name: "BulletCamera"}), (super:EntityClass {name: "Camera"}) 
CREATE (sub)-[:IS_A]->(super);

MATCH (sub:EntityClass {name: "Camera"}), (super:EntityClass {name: "Device"}) 
CREATE (sub)-[:IS_A]->(super);

MATCH (sub:EntityClass {name: "EdgeDevice"}), (super:EntityClass {name: "Device"}) 
CREATE (sub)-[:IS_A]->(super);

// 业务流程继承
MATCH (sub:EntityClass {name: "LicensePlateRecognition"}), (super:EntityClass {name: "BusinessProcess"}) 
CREATE (sub)-[:IS_A]->(super);

MATCH (sub:EntityClass {name: "PaymentProcessing"}), (super:EntityClass {name: "BusinessProcess"}) 
CREATE (sub)-[:IS_A]->(super);

MATCH (sub:EntityClass {name: "ArrearsCollection"}), (super:EntityClass {name: "BusinessProcess"}) 
CREATE (sub)-[:IS_A]->(super);

MATCH (sub:EntityClass {name: "ParkingManagement"}), (super:EntityClass {name: "BusinessProcess"}) 
CREATE (sub)-[:IS_A]->(super);

MATCH (sub:EntityClass {name: "IllegalParkingProcessing"}), (super:EntityClass {name: "BusinessProcess"}) 
CREATE (sub)-[:IS_A]->(super);

// ------------------------------------------
// 6. 查询和验证
// ------------------------------------------

// 创建索引
CREATE INDEX entity_class_name FOR (n:EntityClass) ON (n.name);
CREATE INDEX entity_property_name FOR (n:EntityProperty) ON (n.name);
CREATE INDEX entity_relation_name FOR (n:EntityRelation) ON (n.name);

RETURN 
  "路侧停车管理本体导入完成" AS message,
  count{(:EntityClass)} AS entity_class_count,
  count{(:EntityProperty)} AS entity_property_count,
  count{(:EntityRelation)} AS entity_relation_count;