# 高级ECharts工具 (Advanced ECharts Tool)

## 概述

这是一个功能强大的ECharts可视化工具，专为前端应用设计，支持多种图表类型、数据分析和动态更新功能。

## 🚀 主要特性

### 📊 支持的图表类型
- **柱状图 (Bar)** - 适用于分类数据对比
- **折线图 (Line)** - 适用于趋势分析
- **饼图 (Pie)** - 适用于占比分析
- **散点图 (Scatter)** - 适用于相关性分析
- **面积图 (Area)** - 适用于累积趋势
- **雷达图 (Radar)** - 适用于多维度评估
- **热力图 (Heatmap)** - 适用于密度分析
- **仪表盘 (Gauge)** - 适用于KPI展示
- **漏斗图 (Funnel)** - 适用于转化率分析
- **树图 (Treemap)** - 适用于层级数据

### 🎨 前端友好特性
- **完整HTML输出** - 包含样式和交互的独立HTML页面
- **响应式设计** - 自适应不同屏幕尺寸
- **丰富交互** - 支持缩放、拖拽、数据视图
- **导出功能** - 一键导出PNG图片
- **动画效果** - 平滑的过渡和加载动画

### 📈 数据分析功能
- **摘要统计** - 均值、中位数、标准差、分位数
- **相关性分析** - 变量间相关系数和强度
- **分布分析** - 直方图、异常值检测、信息熵

### 🛠️ 图表管理
- **创建图表** - 支持自定义配置和样式
- **更新数据** - 动态更新图表数据
- **查询图表** - 获取图表HTML和配置
- **列表管理** - 批量管理多个图表
- **删除图表** - 清理不需要的图表

## 📋 API接口

### 1. 创建图表 (create_chart)

```json
{
  "action": "create_chart",
  "type": "bar",
  "title": "销售数据分析",
  "data": [
    {"month": "1月", "sales": 1200, "profit": 300},
    {"month": "2月", "sales": 1800, "profit": 450},
    {"month": "3月", "sales": 1500, "profit": 380}
  ],
  "width": "800px",
  "height": "400px",
  "enable_animation": true,
  "options": {
    "color": ["#5470c6", "#91cc75"],
    "title": {
      "subtext": "2024年第一季度"
    }
  }
}
```

**响应示例:**
```json
{
  "success": true,
  "chart_id": "chart_abc12345",
  "html": "<完整的HTML页面>",
  "config": "<ECharts配置对象>",
  "chart_url": "chart://chart_abc12345",
  "created_at": "2024-01-01T12:00:00"
}
```

### 2. 更新图表 (update_chart)

```json
{
  "action": "update_chart",
  "chart_id": "chart_abc12345",
  "data": [
    {"month": "4月", "sales": 2000, "profit": 520}
  ]
}
```

### 3. 获取图表 (get_chart)

```json
{
  "action": "get_chart",
  "chart_id": "chart_abc12345"
}
```

### 4. 列出图表 (list_charts)

```json
{
  "action": "list_charts"
}
```

### 5. 删除图表 (delete_chart)

```json
{
  "action": "delete_chart",
  "chart_id": "chart_abc12345"
}
```

### 6. 数据分析 (analyze_data)

#### 摘要分析
```json
{
  "action": "analyze_data",
  "analysis_type": "summary",
  "data": [
    {"age": 25, "salary": 50000},
    {"age": 30, "salary": 60000},
    {"age": 35, "salary": 75000}
  ]
}
```

#### 相关性分析
```json
{
  "action": "analyze_data",
  "analysis_type": "correlation",
  "data": [
    {"study_hours": 4, "score": 78},
    {"study_hours": 6, "score": 85}
  ]
}
```

## 🎯 使用场景

### 1. 停车场管理
```json
{
  "action": "create_chart",
  "type": "line",
  "title": "停车场使用率趋势",
  "data": [
    {"time": "08:00", "occupancy": 45},
    {"time": "10:00", "occupancy": 78},
    {"time": "12:00", "occupancy": 92},
    {"time": "14:00", "occupancy": 85},
    {"time": "16:00", "occupancy": 67},
    {"time": "18:00", "occupancy": 88}
  ]
}
```

### 2. 收费分析
```json
{
  "action": "create_chart",
  "type": "pie",
  "title": "收费类型分布",
  "data": [
    {"type": "临时停车", "amount": 15000},
    {"type": "月卡用户", "amount": 45000},
    {"type": "年卡用户", "amount": 28000},
    {"type": "VIP用户", "amount": 12000}
  ]
}
```

### 3. 运营报告
```json
{
  "action": "create_chart",
  "type": "bar",
  "title": "月度收入对比",
  "data": [
    {"month": "1月", "income": 85000, "cars": 3200},
    {"month": "2月", "income": 92000, "cars": 3450},
    {"month": "3月", "income": 78000, "cars": 2950}
  ]
}
```

## 🎨 前端集成

### 1. 直接嵌入HTML
```javascript
// 调用工具创建图表
const response = await fetch('/api/tools/advanced_echarts/execute', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(chartRequest)
});

const result = await response.json();

// 直接嵌入HTML
document.getElementById('chart-container').innerHTML = result.html;
```

### 2. 使用iframe嵌入
```html
<iframe 
  src="data:text/html;charset=utf-8,{encodeURIComponent(chartHtml)}"
  width="100%" 
  height="500px"
  frameborder="0">
</iframe>
```

### 3. 动态更新
```javascript
// 更新图表数据
const updateResponse = await fetch('/api/tools/advanced_echarts/execute', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    action: 'update_chart',
    chart_id: currentChartId,
    data: newData
  })
});

// 更新页面中的图表
const updateResult = await updateResponse.json();
document.getElementById('chart-container').innerHTML = updateResult.html;
```

## 📊 数据格式说明

### 通用数据格式
```json
[
  {"field1": "value1", "field2": numeric_value, "field3": "value3"},
  {"field1": "value2", "field2": numeric_value, "field3": "value3"}
]
```

### 特殊图表格式

#### 饼图数据
```json
[
  {"name": "分类名称", "value": 数值},
  {"name": "分类名称", "value": 数值}
]
```

#### 雷达图数据
```json
[
  {"name": "指标名称", "value": 数值, "max": 最大值},
  {"name": "指标名称", "value": 数值, "max": 最大值}
]
```

#### 热力图数据
```json
[
  {"x": "X轴标签", "y": "Y轴标签", "value": 数值},
  {"x": "X轴标签", "y": "Y轴标签", "value": 数值}
]
```

## ⚙️ 高级配置

### 自定义主题
```json
{
  "options": {
    "color": ["#5470c6", "#91cc75", "#fac858", "#ee6666"],
    "backgroundColor": "#ffffff",
    "textStyle": {
      "fontFamily": "Arial",
      "fontSize": 12
    }
  }
}
```

### 交互配置
```json
{
  "options": {
    "tooltip": {
      "trigger": "axis",
      "formatter": "自定义格式化函数"
    },
    "legend": {
      "show": true,
      "position": "top"
    },
    "grid": {
      "left": "10%",
      "right": "10%",
      "bottom": "15%"
    }
  }
}
```

## 🧪 测试示例

运行测试脚本查看完整示例：
```bash
cd mcp-service/src/python
python test/advanced_echarts_test.py
```

## 📈 性能优化

### 1. 大数据量处理
- 自动数据采样（超过1000个数据点）
- 虚拟滚动（超过500个数据点）
- 增量渲染（动画优化）

### 2. 内存管理
- 图表实例自动清理
- 30分钟无活动自动删除
- 最大100个图表限制

### 3. 缓存策略
- HTML模板缓存
- 配置对象缓存
- 数据分析结果缓存

## 🔧 故障排除

### 常见问题

1. **图表不显示**
   - 检查数据格式是否正确
   - 确认数值字段为数字类型
   - 验证必需字段是否存在

2. **样式异常**
   - 检查options配置格式
   - 确认CSS样式冲突
   - 验证颜色格式

3. **性能问题**
   - 减少数据点数量
   - 关闭复杂动画
   - 使用数据采样

### 调试模式
```json
{
  "action": "create_chart",
  "type": "bar",
  "title": "调试图表",
  "data": [...],
  "options": {
    "animation": false,
    "debug": true
  }
}
```

## 🎯 最佳实践

### 1. 数据准备
- 确保数据类型正确
- 处理缺失值
- 合理的数据范围

### 2. 图表选择
- 分类对比 → 柱状图
- 时间趋势 → 折线图
- 占比分析 → 饼图
- 相关性 → 散点图
- 多维评估 → 雷达图

### 3. 用户体验
- 提供清晰的标题和说明
- 使用合适的颜色方案
- 添加交互提示
- 支持导出和分享

## 📞 技术支持

- **文档**: 查看完整API文档
- **示例**: 参考测试用例
- **社区**: ECharts官方文档
- **更新**: 定期更新功能

---

🎉 **这个高级ECharts工具为你的前端应用提供了强大的可视化能力！**
