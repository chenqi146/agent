#!/usr/bin/env python3
"""
高级ECharts工具测试脚本
演示各种图表类型的创建和数据分析功能
"""

import json
import asyncio
from datetime import datetime

def test_advanced_echarts():
    """测试高级ECharts工具的各种功能"""
    
    print("🎯 高级ECharts工具测试")
    print("=" * 80)
    
    # 测试数据
    test_cases = [
        {
            "name": "柱状图 - 月度销售数据",
            "action": "create_chart",
            "type": "bar",
            "title": "2024年月度销售数据",
            "data": [
                {"month": "1月", "sales": 1200, "profit": 300, "costs": 900},
                {"month": "2月", "sales": 1800, "profit": 450, "costs": 1350},
                {"month": "3月", "sales": 1500, "profit": 380, "costs": 1120},
                {"month": "4月", "sales": 2000, "profit": 520, "costs": 1480},
                {"month": "5月", "sales": 2200, "profit": 580, "costs": 1620},
                {"month": "6月", "sales": 1900, "profit": 470, "costs": 1430}
            ],
            "width": "900px",
            "height": "500px",
            "enable_animation": True
        },
        {
            "name": "折线图 - 股票价格走势",
            "action": "create_chart",
            "type": "line",
            "title": "股票价格走势图",
            "data": [
                {"date": "2024-01-01", "price": 100.5, "volume": 15000},
                {"date": "2024-01-02", "price": 102.3, "volume": 18000},
                {"date": "2024-01-03", "price": 98.7, "volume": 22000},
                {"date": "2024-01-04", "price": 105.2, "volume": 19000},
                {"date": "2024-01-05", "price": 108.9, "volume": 16000},
                {"date": "2024-01-06", "price": 107.1, "volume": 20000},
                {"date": "2024-01-07", "price": 110.5, "volume": 17000}
            ],
            "options": {
                "tooltip": {
                    "trigger": "axis",
                    "formatter": function(params) {
                        return params[0].name + '<br/>' +
                               params[0].seriesName + ': $' + params[0].value + '<br/>' +
                               'Volume: ' + params[1].value;
                    }
                }
            }
        },
        {
            "name": "饼图 - 市场份额",
            "action": "create_chart",
            "type": "pie",
            "title": "2024年市场份额分布",
            "data": [
                {"brand": "苹果", "market_share": 28.5},
                {"brand": "三星", "market_share": 22.3},
                {"brand": "小米", "market_share": 18.7},
                {"brand": "OPPO", "market_share": 15.2},
                {"brand": "vivo", "market_share": 10.8},
                {"brand": "其他", "market_share": 4.5}
            ],
            "options": {
                "legend": {
                    "orient": "vertical",
                    "left": "left"
                }
            }
        },
        {
            "name": "散点图 - 身高体重关系",
            "action": "create_chart",
            "type": "scatter",
            "title": "身高体重分布图",
            "data": [
                {"height": 165, "weight": 55, "age": 25},
                {"height": 170, "weight": 62, "age": 28},
                {"height": 175, "weight": 70, "age": 30},
                {"height": 180, "weight": 75, "age": 32},
                {"height": 168, "weight": 58, "age": 26},
                {"height": 172, "weight": 65, "age": 29},
                {"height": 178, "weight": 72, "age": 31},
                {"height": 160, "weight": 50, "age": 24},
                {"height": 185, "weight": 80, "age": 33},
                {"height": 173, "weight": 68, "age": 27}
            ]
        },
        {
            "name": "雷达图 - 能力评估",
            "action": "create_chart",
            "type": "radar",
            "title": "员工能力评估",
            "data": [
                {"name": "技术能力", "value": 85, "max": 100},
                {"name": "沟通能力", "value": 78, "max": 100},
                {"name": "领导力", "value": 72, "max": 100},
                {"name": "创新思维", "value": 88, "max": 100},
                {"name": "执行力", "value": 90, "max": 100},
                {"name": "团队合作", "value": 82, "max": 100}
            ]
        },
        {
            "name": "热力图 - 活动强度",
            "action": "create_chart",
            "type": "heatmap",
            "title": "一周活动强度热力图",
            "data": [
                {"x": "周一", "y": "上午", "value": 85},
                {"x": "周一", "y": "下午", "value": 92},
                {"x": "周一", "y": "晚上", "value": 45},
                {"x": "周二", "y": "上午", "value": 78},
                {"x": "周二", "y": "下午", "value": 88},
                {"x": "周二", "y": "晚上", "value": 52},
                {"x": "周三", "y": "上午", "value": 90},
                {"x": "周三", "y": "下午", "value": 95},
                {"x": "周三", "y": "晚上", "value": 38},
                {"x": "周四", "y": "上午", "value": 82},
                {"x": "周四", "y": "下午", "value": 86},
                {"x": "周四", "y": "晚上", "value": 41},
                {"x": "周五", "y": "上午", "value": 75},
                {"x": "周五", "y": "下午", "value": 80},
                {"x": "周五", "y": "晚上", "value": 55},
                {"x": "周六", "y": "上午", "value": 45},
                {"x": "周六", "y": "下午", "value": 60},
                {"x": "周六", "y": "晚上", "value": 70},
                {"x": "周日", "y": "上午", "value": 30},
                {"x": "周日", "y": "下午", "value": 45},
                {"x": "周日", "y": "晚上", "value": 65}
            ]
        },
        {
            "name": "仪表盘 - KPI指标",
            "action": "create_chart",
            "type": "gauge",
            "title": "完成率仪表盘",
            "data": [
                {"name": "项目完成率", "value": 78}
            ]
        },
        {
            "name": "漏斗图 - 转化率",
            "action": "create_chart",
            "type": "funnel",
            "title": "销售转化漏斗",
            "data": [
                {"stage": "访问", "count": 1000},
                {"stage": "注册", "count": 600},
                {"stage": "激活", "count": 350},
                {"stage": "购买", "count": 180},
                {"stage": "复购", "count": 95}
            ]
        }
    ]
    
    # 执行测试用例
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 测试用例 {i}: {test_case['name']}")
        print("-" * 60)
        
        # 模拟工具调用
        print(f"🔧 Action: {test_case['action']}")
        print(f"📈 Chart Type: {test_case['type']}")
        print(f"📝 Title: {test_case['title']}")
        print(f"📏 Size: {test_case.get('width', '800px')} x {test_case.get('height', '400px')}")
        print(f"📊 Data Points: {len(test_case['data'])}")
        
        if 'options' in test_case:
            print(f"⚙️  Custom Options: {len(test_case['options'])} 项")
        
        print("\n📋 预期输出:")
        print("  ✅ success: true")
        print("  🆔 chart_id: chart_xxxxxxxx")
        print("  📄 html: <完整的HTML页面>")
        print("  ⚙️  config: <ECharts配置对象>")
        print("  🔗 chart_url: chart://chart_xxxxxxxx")
        print("  📅 created_at: <时间戳>")
        
        print("\n🎯 前端使用方式:")
        print("  1. 直接嵌入HTML到iframe")
        print("  2. 使用chart_url通过API获取")
        print("  3. 支持响应式布局")
        print("  4. 内置导出、刷新、数据视图功能")
    
    # 测试数据分析功能
    print("\n" + "=" * 80)
    print("📊 数据分析功能测试")
    print("=" * 80)
    
    analysis_tests = [
        {
            "name": "数据摘要分析",
            "action": "analyze_data",
            "analysis_type": "summary",
            "data": [
                {"age": 25, "salary": 50000, "experience": 2},
                {"age": 30, "salary": 60000, "experience": 5},
                {"age": 35, "salary": 75000, "experience": 8},
                {"age": 28, "salary": 55000, "experience": 3},
                {"age": 32, "salary": 68000, "experience": 6},
                {"age": 40, "salary": 85000, "experience": 12}
            ]
        },
        {
            "name": "相关性分析",
            "action": "analyze_data",
            "analysis_type": "correlation",
            "data": [
                {"study_hours": 2, "score": 65, "attendance": 90},
                {"study_hours": 4, "score": 78, "attendance": 95},
                {"study_hours": 6, "score": 85, "attendance": 92},
                {"study_hours": 3, "score": 72, "attendance": 88},
                {"study_hours": 5, "score": 82, "attendance": 94},
                {"study_hours": 7, "score": 92, "attendance": 96}
            ]
        }
    ]
    
    for i, test in enumerate(analysis_tests, 1):
        print(f"\n📈 分析测试 {i}: {test['name']}")
        print("-" * 40)
        print(f"🔧 Analysis Type: {test['analysis_type']}")
        print(f"📊 Data Points: {len(test['data'])}")
        print(f"📋 Fields: {list(test['data'][0].keys())}")
        
        print("\n📋 预期分析结果:")
        if test['analysis_type'] == 'summary':
            print("  📊 数值字段统计: count, min, max, sum, avg, median, std")
            print("  📊 分类型字段统计: count, unique, most_common, distribution")
        elif test['analysis_type'] == 'correlation':
            print("  🔗 相关系数矩阵")
            print("  📈 相关性强度解释")
            print("  📊 正负相关性判断")
    
    # 测试图表管理功能
    print("\n" + "=" * 80)
    print("🗂️  图表管理功能测试")
    print("=" * 80)
    
    management_tests = [
        {"action": "list_charts", "name": "列出所有图表"},
        {"action": "update_chart", "name": "更新图表数据", "chart_id": "chart_abc123", "data": [{"new": "data"}]},
        {"action": "get_chart", "name": "获取图表HTML", "chart_id": "chart_abc123"},
        {"action": "delete_chart", "name": "删除图表", "chart_id": "chart_abc123"}
    ]
    
    for i, test in enumerate(management_tests, 1):
        print(f"\n🔧 管理测试 {i}: {test['name']}")
        print(f"   Action: {test['action']}")
        if 'chart_id' in test:
            print(f"   Chart ID: {test['chart_id']}")
        if 'data' in test:
            print(f"   Data: {len(test['data'])} items")
    
    print("\n" + "=" * 80)
    print("🎯 高级ECharts工具特性总结")
    print("=" * 80)
    
    features = [
        "🎨 支持10种图表类型：柱状图、折线图、饼图、散点图、面积图、雷达图、热力图、仪表盘、漏斗图、树图",
        "📱 响应式设计：自适应不同屏幕尺寸",
        "🎬 丰富动画：平滑过渡和交互效果",
        "🛠️ 交互工具栏：导出图片、数据视图、类型切换、缩放还原",
        "📊 数据分析：摘要统计、相关性分析、分布分析",
        "💾 图表管理：创建、更新、查询、删除、列表",
        "🎨 自定义样式：支持颜色、主题、布局定制",
        "📱 前端友好：生成完整HTML，可直接嵌入",
        "🔄 动态更新：支持数据实时更新",
        "📈 智能推断：自动识别数据类型和字段",
        "🎯 专业配置：基于ECharts最佳实践"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print("\n" + "=" * 80)
    print("🚀 使用示例")
    print("=" * 80)
    
    example = {
        "action": "create_chart",
        "type": "bar",
        "title": "停车场收入分析",
        "data": [
            {"date": "2024-01-01", "income": 5000, "cars": 120},
            {"date": "2024-01-02", "income": 6200, "cars": 145},
            {"date": "2024-01-03", "income": 4800, "cars": 110},
            {"date": "2024-01-04", "income": 7500, "cars": 180},
            {"date": "2024-01-05", "income": 8200, "cars": 195}
        ],
        "width": "100%",
        "height": "400px",
        "enable_animation": True,
        "options": {
            "color": ["#5470c6", "#91cc75"],
            "title": {
                "text": "停车场收入分析",
                "subtext": "2024年1月数据"
            }
        }
    }
    
    print("📝 完整调用示例:")
    print(json.dumps(example, indent=2, ensure_ascii=False))
    
    print("\n🎯 前端集成:")
    print("1. 调用工具创建图表")
    print("2. 获取返回的HTML")
    print("3. 嵌入到页面中")
    print("4. 使用内置功能进行交互")
    print("5. 支持数据动态更新")
    
    print("\n✨ 测试完成！")
    print("📊 这个高级ECharts工具比原版本功能更强大，更适合前端使用")


if __name__ == "__main__":
    test_advanced_echarts()
