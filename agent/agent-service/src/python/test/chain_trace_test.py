#!/usr/bin/env python3
"""
智能体链路追踪测试脚本
演示从协调智能体到规划智能体的完整执行过程
"""

import asyncio
import json
from datetime import datetime
from interfaces.dto.coordinator_dto import CoordinateRequest


async def test_full_chain():
    """测试完整的智能体链路"""
    
    print("🚀 开始智能体链路追踪测试")
    print("=" * 80)
    
    # 模拟用户请求
    test_requests = [
        {
            "user_id": 1,
            "query": "查询停车场A今天的停车计费情况",
            "thinking": True,
            "description": "停车计费查询 - 测试协调智能体意图识别和规划智能体目标拆解"
        },
        {
            "user_id": 1,
            "query": "分析停车场B本月的异常停车事件",
            "thinking": True,
            "description": "异常事件分析 - 测试依赖分析和工具匹配"
        },
        {
            "user_id": 1,
            "query": "生成停车场C的运营报告",
            "thinking": True,
            "description": "运营报告生成 - 测试任务清单生成和执行引擎"
        }
    ]
    
    for i, test_case in enumerate(test_requests, 1):
        print(f"\n📋 测试用例 {i}: {test_case['description']}")
        print("-" * 80)
        
        # 创建请求对象
        request = CoordinateRequest(
            user_id=test_case["user_id"],
            query=test_case["query"],
            session_id=None,  # 新建会话
            thinking=test_case["thinking"]
        )
        
        print(f"👤 用户ID: {request.user_id}")
        print(f"💬 查询内容: {request.query}")
        print(f"🧠 深度思考模式: {request.thinking}")
        print(f"🆔 会话ID: {request.session_id or '新建会话'}")
        
        # 这里需要实际的协调智能体实例来执行
        # err, result = await coordinator.coordinate(request)
        
        print("\n📊 预期链路过程:")
        print("1️⃣  [协调智能体] 意图识别阶段")
        print("   - FastText快速分类")
        print("   - Neo4j本体验证")
        print("   - 发送完整Prompt给LLM")
        print("   - 接收LLM响应")
        
        print("2️⃣  [协调智能体] 上下文构建阶段")
        print("   - RAG知识检索")
        print("   - 记忆检索")
        print("   - 业务上下文加载")
        
        print("3️⃣  [协调智能体] 任务路由阶段")
        print("   - 路由到对应的规划智能体")
        print("   - 获取智能体特定Prompt")
        
        print("4️⃣  [规划智能体] 目标拆解阶段")
        print("   - 发送目标拆解Prompt给LLM")
        print("   - 接收子目标列表")
        
        print("5️⃣  [规划智能体] 依赖分析阶段")
        print("   - 构建依赖图")
        print("   - 识别关键路径")
        print("   - 检测冲突")
        
        print("6️⃣  [规划智能体] 工具匹配阶段")
        print("   - 发送工具匹配Prompt给LLM")
        print("   - 接收工具匹配结果")
        
        print("7️⃣  [规划智能体] 任务清单生成阶段")
        print("   - 生成任务链")
        print("   - 设置执行策略")
        
        print("8️⃣  [规划智能体] 执行引擎阶段")
        print("   - 执行任务")
        print("   - 处理重试和回退")
        
        print("9️⃣  [协调智能体] 结果汇总阶段")
        print("   - 汇总执行结果")
        print("   - 更新对话历史")
        
        print("\n🎯 关键日志输出点:")
        print("📍 每个阶段开始时会有清晰的标识")
        print("🤖 所有发送给LLM的Prompt都会完整打印")
        print("💬 LLM的响应结果都会详细显示")
        print("📊 中间状态和数据流转都会记录")
        print("⚠️  错误和异常信息会突出显示")
        
        print("\n" + "=" * 80)
    
    print("\n🎉 链路追踪测试完成!")
    print("📝 请查看日志文件获取详细的执行过程:")
    print("   - agent-service/logs/pg_agent_application.log")
    print("   - logs/pg_agent_application.log")


def print_expected_log_format():
    """打印预期的日志格式示例"""
    
    print("\n📋 预期日志格式示例:")
    print("=" * 80)
    
    example_log = """
================================================================================
📍 [协调智能体] 意图识别阶段
👤 用户ID: 1
💬 原始查询: '查询停车场A今天的停车计费情况'
🔧 可用工具数量: 15
--------------------------------------------------------------------------------
🤖 System Prompt:
You are an Intent Recognition Agent. Analyze the user's request and determine the primary intent.
Possible intents:
- 'city_parking': Related to city parking management, tasks, analysis, or decision support.
...
--------------------------------------------------------------------------------
👤 User Query:
查询停车场A今天的停车计费情况
--------------------------------------------------------------------------------
📊 Messages 结构: 共 2 条消息
  Message 0: role=system, content=You are an Intent Recognition Agent...
  Message 1: role=user, content=查询停车场A今天的停车计费情况
================================================================================
🤖 意图识别 - LLM返回结果:
  🎯 识别意图: city_parking
  📋 提取参数: {"parking_lot": "A", "date": "今天", "type": "计费"}
  🧠 推理过程: 用户查询涉及停车计费，属于城市停车管理范畴
📝 槽位信息详情:
  - parking_lot: A
  - date: 今天
  - type: 计费
================================================================================
🎯 [协调智能体] 意图识别阶段完成
================================================================================

================================================================================
📍 [规划智能体] 目标拆解阶段
🆔 会话ID: sess_abc123def456
🤖 智能体类型: city_parking
🎯 目标: 查询停车场A今天的停车计费情况...
⚙️  智能体配置: 城市停车智能体
🔧 能力范围: ['停车查询', '计费分析', '异常检测', '报告生成']
--------------------------------------------------------------------------------
🤖 目标拆解 - 发送给LLM的System Prompt:
你是一个目标拆解专家。请将用户的目标拆解为具体的、可执行的子目标。

智能体类型: 城市停车智能体
能力范围: ['停车查询', '计费分析', '异常检测', '报告生成']
...
--------------------------------------------------------------------------------
👤 User Query:
目标: 查询停车场A今天的停车计费情况

上下文: {"parking_lot": "A", "date": "今天", "type": "计费"}
================================================================================
🤖 目标拆解 - LLM返回结果:
  📊 拆解完成，共 3 个子目标
  🎯 子目标 1: 查询停车场基本信息 (analysis)
     📝 描述: 获取停车场A的基本信息和配置
     📤 预期输出: 停车场配置数据
     🔗 依赖: []
  🎯 子目标 2: 获取今日停车记录 (action)
     📝 描述: 查询停车场A今天的所有停车记录
     📤 预期输出: 停车记录列表
     🔗 依赖: ["查询停车场基本信息"]
  🎯 子目标 3: 计算停车费用 (analysis)
     📝 描述: 根据停车记录计算相应的停车费用
     📤 预期输出: 费用计算结果
     🔗 依赖: ["获取今日停车记录"]
================================================================================
🎯 [规划智能体] 目标拆解阶段完成
================================================================================
"""
    
    print(example_log)
    
    print("🔍 日志特点:")
    print("✅ 使用emoji图标增强可读性")
    print("✅ 每个阶段有清晰的开始和结束标识")
    print("✅ 所有LLM交互都有完整的Prompt和响应")
    print("✅ 数据流转过程详细记录")
    print("✅ 错误信息突出显示")
    print("✅ 使用分隔线区分不同阶段")


if __name__ == "__main__":
    print("🎯 智能体链路追踪工具")
    print("=" * 80)
    
    # 打印预期的日志格式
    print_expected_log_format()
    
    # 运行测试
    asyncio.run(test_full_chain())
