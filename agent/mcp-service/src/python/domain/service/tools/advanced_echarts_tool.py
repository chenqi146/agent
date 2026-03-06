import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import uuid
import numpy as np
from jinja2 import Template
from domain.model.tool import BaseTool, InterfaceType

class ChartType:
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    RADAR = "radar"
    HEATMAP = "heatmap"
    MAP = "map"
    GAUGE = "gauge"
    FUNNEL = "funnel"
    TREEMAP = "treemap"

class ChartConfig:
    def __init__(self, 
                 type: str = ChartType.BAR,
                 title: str = None,
                 width: str = "800px",
                 height: str = "400px",
                 data: List[Dict] = None,
                 options: Dict = None):
        self.type = type
        self.title = title
        self.width = width
        self.height = height
        self.data = data or []
        self.options = options or {}

class AdvancedEChartsTool(BaseTool):
    def __init__(self):
        self.name = "advanced_echarts"
        self.description = "Advanced ECharts tool for generating complex, interactive charts with HTML output suitable for frontend applications. Supports multiple chart types, data analysis, and dynamic updates."
        self.tags = ["chart", "visualization", "data-analysis", "frontend"]
        
        # 存储图表实例
        self.charts = {}
        
        # HTML Template for frontend hydration
        self.template = Template("""
        <div id="{{ chart_id }}" class="echarts-chart" style="width: {{ width }}; height: {{ height }};" data-option="{{ options_json | e }}"></div>
        """)
    
    def execute(self, arguments: Dict[str, Any]) -> Any:
        print(f"\n[DEBUG] AdvancedEChartsTool.execute called with args: {json.dumps(arguments, default=str, ensure_ascii=False)}")
        action = arguments.get("action")
        
        if not action:
            print("[DEBUG] No action provided")
            return {"error": "Action is required"}
        
        try:
            if action == "create_chart":
                print("[DEBUG] Executing create_chart")
                return self.create_chart(arguments)
            elif action == "update_chart":
                return self.update_chart_data(arguments)
            elif action == "get_chart":
                return self.get_chart_html(arguments)
            elif action == "delete_chart":
                return self.delete_chart(arguments)
            elif action == "list_charts":
                return self.list_charts()
            elif action == "analyze_data":
                return self.analyze_data(arguments)
            else:
                print(f"[DEBUG] Unknown action: {action}")
                return {"error": f"Unknown action: {action}"}
        except Exception as e:
            print(f"[DEBUG] Execution failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Execution failed: {str(e)}"}
    
    def create_chart(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """创建图表"""
        chart_type = arguments.get("type", ChartType.BAR)
        title = arguments.get("title", f"{chart_type.title()} Chart")
        print(f"[DEBUG] Creating chart - Type: {chart_type}, Title: {title}")
        data = arguments.get("data", [])
        width = arguments.get("width", "800px")
        height = arguments.get("height", "400px")
        options = arguments.get("options", {})
        enable_animation = arguments.get("enable_animation", True)
        
        # 创建配置对象
        config = ChartConfig(
            type=chart_type,
            title=title,
            width=width,
            height=height,
            data=data,
            options=options
        )
        
        # 生成ECharts配置
        echarts_config = self._generate_echarts_config(config)
        
        # 生成图表ID
        chart_id = f"chart_{uuid.uuid4().hex[:8]}"
        
        # 生成HTML
        options_json = json.dumps(echarts_config, default=str, ensure_ascii=False)
        html = self.template.render(
            chart_id=chart_id,
            title=title,
            width=width,
            height=height,
            options_json=options_json,
            use_map=chart_type == ChartType.MAP,
            data_count=len(data),
            update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            enable_animation=enable_animation
        )
        
        # 存储图表
        self.charts[chart_id] = {
            "config": config,
            "echarts_config": echarts_config,
            "created_at": datetime.now(),
            "data": data,
            "echarts_html": html
        }
        
        return {
            "success": True,
            "chart_id": chart_id,
            "echarts_html": html,
            "config": echarts_config,
            "chart_url": f"chart://{chart_id}",
            "created_at": datetime.now().isoformat()
        }
    
    def _generate_echarts_config(self, config: ChartConfig) -> Dict:
        """根据配置生成ECharts配置"""
        base_config = {
            "title": {
                "text": config.title,
                "left": "center",
                "textStyle": {"fontSize": 16, "fontWeight": "bold"}
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "cross"},
                "backgroundColor": "rgba(50,50,50,0.9)",
                "borderColor": "#ccc",
                "borderWidth": 1,
                "textStyle": {"color": "#fff"}
            },
            "toolbox": {
                "show": True,
                "feature": {
                    "saveAsImage": {"show": True, "title": "保存为图片"},
                    "dataView": {"show": True, "title": "数据视图", "readOnly": False},
                    "magicType": {
                        "show": True, 
                        "type": ["line", "bar", "stack", "tiled"],
                        "title": {"line": "切换为折线图", "bar": "切换为柱状图"}
                    },
                    "restore": {"show": True, "title": "还原"},
                    "dataZoom": {"show": True, "title": {"zoom": "区域缩放", "back": "区域缩放还原"}}
                }
            },
            "grid": {
                "left": "3%",
                "right": "4%",
                "bottom": "3%",
                "containLabel": True
            },
            "animation": True,
            "animationDuration": 1000,
            "animationEasing": "cubicOut"
        }
        
        # 根据图表类型生成特定配置
        if config.type == ChartType.LINE:
            base_config.update(self._generate_line_config(config))
        elif config.type == ChartType.BAR:
            base_config.update(self._generate_bar_config(config))
        elif config.type == ChartType.PIE:
            base_config.update(self._generate_pie_config(config))
        elif config.type == ChartType.SCATTER:
            base_config.update(self._generate_scatter_config(config))
        elif config.type == ChartType.AREA:
            base_config.update(self._generate_area_config(config))
        elif config.type == ChartType.RADAR:
            base_config.update(self._generate_radar_config(config))
        elif config.type == ChartType.HEATMAP:
            base_config.update(self._generate_heatmap_config(config))
        elif config.type == ChartType.GAUGE:
            base_config.update(self._generate_gauge_config(config))
        elif config.type == ChartType.FUNNEL:
            base_config.update(self._generate_funnel_config(config))
        elif config.type == ChartType.TREEMAP:
            base_config.update(self._generate_treemap_config(config))
        
        # 合并用户自定义选项
        if config.options:
            self._deep_merge(base_config, config.options)
        
        # 应用数据
        if config.data:
            self._apply_data(base_config, config.data, config.type)
        
        return base_config
    
    def _generate_line_config(self, config: ChartConfig) -> Dict:
        """生成折线图配置"""
        return {
            "xAxis": {
                "type": "category",
                "boundaryGap": False,
                "data": [],
                "axisLine": {"lineStyle": {"color": "#8c8c8c"}},
                "axisTick": {"alignWithLabel": True}
            },
            "yAxis": {
                "type": "value",
                "axisLine": {"lineStyle": {"color": "#8c8c8c"}},
                "splitLine": {"lineStyle": {"color": "#f0f0f0"}}
            },
            "series": []
        }
    
    def _generate_bar_config(self, config: ChartConfig) -> Dict:
        """生成柱状图配置"""
        return {
            "xAxis": {
                "type": "category",
                "data": [],
                "axisLine": {"lineStyle": {"color": "#8c8c8c"}},
                "axisTick": {"alignWithLabel": True}
            },
            "yAxis": {
                "type": "value",
                "axisLine": {"lineStyle": {"color": "#8c8c8c"}},
                "splitLine": {"lineStyle": {"color": "#f0f0f0"}}
            },
            "series": []
        }
    
    def _generate_pie_config(self, config: ChartConfig) -> Dict:
        """生成饼图配置"""
        return {
            "legend": {
                "orient": "vertical",
                "left": "left",
                "data": []
            },
            "series": [{
                "name": config.title,
                "type": "pie",
                "radius": ["40%", "70%"],
                "center": ["50%", "60%"],
                "avoidLabelOverlap": False,
                "itemStyle": {
                    "borderRadius": 10,
                    "borderColor": "#fff",
                    "borderWidth": 2
                },
                "label": {
                    "show": True,
                    "position": "outside",
                    "formatter": "{b}: {c} ({d}%)"
                },
                "emphasis": {
                    "label": {"show": True, "fontSize": "16", "fontWeight": "bold"},
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                },
                "data": []
            }]
        }
    
    def _generate_scatter_config(self, config: ChartConfig) -> Dict:
        """生成散点图配置"""
        return {
            "xAxis": {
                "type": "value",
                "splitLine": {"lineStyle": {"color": "#f0f0f0"}}
            },
            "yAxis": {
                "type": "value",
                "splitLine": {"lineStyle": {"color": "#f0f0f0"}}
            },
            "series": []
        }
    
    def _generate_area_config(self, config: ChartConfig) -> Dict:
        """生成面积图配置"""
        return {
            "xAxis": {
                "type": "category",
                "boundaryGap": False,
                "data": []
            },
            "yAxis": {
                "type": "value"
            },
            "series": []
        }
    
    def _generate_radar_config(self, config: ChartConfig) -> Dict:
        """生成雷达图配置"""
        return {
            "radar": {
                "indicator": [],
                "shape": "polygon",
                "splitNumber": 5,
                "axisName": {"color": "rgb(96,98,102)"},
                "splitLine": {"lineStyle": {"color": "#8c8c8c"}},
                "splitArea": {"areaStyle": {"color": ["rgba(114,172,209,0.2)", "rgba(114,172,209,0.5)"]}}
            },
            "series": [{
                "name": config.title,
                "type": "radar",
                "data": []
            }]
        }
    
    def _generate_heatmap_config(self, config: ChartConfig) -> Dict:
        """生成热力图配置"""
        return {
            "xAxis": {
                "type": "category",
                "data": [],
                "splitArea": {"show": True}
            },
            "yAxis": {
                "type": "category",
                "data": [],
                "splitArea": {"show": True}
            },
            "visualMap": {
                "min": 0,
                "max": 100,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "15%"
            },
            "series": [{
                "name": config.title,
                "type": "heatmap",
                "data": [],
                "label": {"show": True},
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        }
    
    def _generate_gauge_config(self, config: ChartConfig) -> Dict:
        """生成仪表盘配置"""
        return {
            "series": [{
                "name": config.title,
                "type": "gauge",
                "progress": {"show": True, "width": 18},
                "axisLine": {"lineStyle": {"width": 18}},
                "axisTick": {"show": False},
                "splitLine": {"length": 15, "lineStyle": {"width": 2, "color": "#999"}},
                "axisLabel": {"distance": 25, "color": "#999", "fontSize": 20},
                "anchor": {"show": True, "showAbove": True, "size": 25, "itemStyle": {"borderWidth": 10}},
                "title": {"fontSize": 14},
                "detail": {
                    "fontSize": 50,
                    "formatter": "{value}%",
                    "offsetCenter": [0, "50%"]
                },
                "data": []
            }]
        }
    
    def _generate_funnel_config(self, config: ChartConfig) -> Dict:
        """生成漏斗图配置"""
        return {
            "legend": {"data": []},
            "series": [{
                "name": config.title,
                "type": "funnel",
                "left": "10%",
                "top": 60,
                "bottom": 60,
                "width": "80%",
                "min": 0,
                "max": 100,
                "minSize": "0%",
                "maxSize": "100%",
                "sort": "descending",
                "gap": 2,
                "label": {"show": True, "position": "inside"},
                "labelLine": {"length": 10, "lineStyle": {"width": 1, "type": "solid"}},
                "itemStyle": {"borderColor": "#fff", "borderWidth": 1},
                "emphasis": {"label": {"fontSize": 20}},
                "data": []
            }]
        }
    
    def _generate_treemap_config(self, config: ChartConfig) -> Dict:
        """生成树图配置"""
        return {
            "series": [{
                "name": config.title,
                "type": "treemap",
                "visibleMin": 300,
                "label": {"show": True, "formatter": "{b}"},
                "itemStyle": {"borderColor": "#fff"},
                "upperLabel": {"show": True, "height": 30},
                "data": []
            }]
        }
    
    def _apply_data(self, config: Dict, data: List[Dict], chart_type: str):
        """应用数据到配置"""
        if not data:
            return
        
        if chart_type in [ChartType.LINE, ChartType.BAR, ChartType.AREA]:
            self._apply_xy_data(config, data, chart_type)
        elif chart_type == ChartType.PIE:
            self._apply_pie_data(config, data)
        elif chart_type == ChartType.SCATTER:
            self._apply_scatter_data(config, data)
        elif chart_type == ChartType.RADAR:
            self._apply_radar_data(config, data)
        elif chart_type == ChartType.HEATMAP:
            self._apply_heatmap_data(config, data)
        elif chart_type == ChartType.GAUGE:
            self._apply_gauge_data(config, data)
        elif chart_type == ChartType.FUNNEL:
            self._apply_funnel_data(config, data)
        elif chart_type == ChartType.TREEMAP:
            self._apply_treemap_data(config, data)
    
    def _apply_xy_data(self, config: Dict, data: List[Dict], chart_type: str):
        """应用XY数据（折线图、柱状图、面积图）"""
        if not data:
            return
        
        # 推断X轴和Y轴字段
        keys = list(data[0].keys())
        x_field = keys[0] if keys else "x"
        y_fields = [k for k in keys[1:] if k != x_field and isinstance(data[0].get(k), (int, float))]
        
        if not y_fields:
            y_fields = [keys[1]] if len(keys) > 1 else ["value"]
        
        # 设置X轴数据
        x_data = [item.get(x_field, f"Item{i}") for i, item in enumerate(data)]
        if "xAxis" in config:
            config["xAxis"]["data"] = x_data
        
        # 生成系列数据
        series = []
        colors = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"]
        
        for i, y_field in enumerate(y_fields):
            y_data = [item.get(y_field, 0) for item in data]
            series_config = {
                "name": y_field,
                "type": chart_type,
                "data": y_data,
                "smooth": chart_type == ChartType.AREA,
                "areaStyle": {"opacity": 0.3} if chart_type == ChartType.AREA else None,
                "itemStyle": {"color": colors[i % len(colors)]},
                "lineStyle": {"width": 2}
            }
            
            # 移除None值
            if series_config["areaStyle"] is None:
                series_config.pop("areaStyle", None)
            
            series.append(series_config)
        
        config["series"] = series
        
        # 设置图例
        if "legend" not in config:
            config["legend"] = {"data": y_fields, "top": "top"}
    
    def _apply_pie_data(self, config: Dict, data: List[Dict]):
        """应用饼图数据"""
        if not data:
            return
        
        keys = list(data[0].keys())
        name_field = keys[0] if keys else "name"
        value_field = keys[1] if len(keys) > 1 else "value"
        
        # 确保value字段是数值型
        if not isinstance(data[0].get(value_field), (int, float)):
            for k in keys:
                if isinstance(data[0].get(k), (int, float)):
                    value_field = k
                    break
        
        pie_data = []
        legend_data = []
        colors = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"]
        
        for i, item in enumerate(data):
            name = item.get(name_field, f"Item{i}")
            value = item.get(value_field, 0)
            pie_data.append({
                "name": name,
                "value": value,
                "itemStyle": {"color": colors[i % len(colors)]}
            })
            legend_data.append(name)
        
        if "series" in config and len(config["series"]) > 0:
            config["series"][0]["data"] = pie_data
        
        if "legend" in config:
            config["legend"]["data"] = legend_data
    
    def _apply_scatter_data(self, config: Dict, data: List[Dict]):
        """应用散点图数据"""
        if not data:
            return
        
        keys = list(data[0].keys())
        x_field = keys[0] if keys else "x"
        y_field = keys[1] if len(keys) > 1 else "y"
        
        scatter_data = []
        for item in data:
            x_val = item.get(x_field, 0)
            y_val = item.get(y_field, 0)
            scatter_data.append([x_val, y_val])
        
        config["series"] = [{
            "name": f"{x_field} vs {y_field}",
            "type": "scatter",
            "data": scatter_data,
            "symbolSize": 8,
            "itemStyle": {
                "color": "#5470c6",
                "borderColor": "#fff",
                "borderWidth": 1
            }
        }]
    
    def _apply_radar_data(self, config: Dict, data: List[Dict]):
        """应用雷达图数据"""
        if not data:
            return
        
        # 假设数据格式: [{"name": "A", "value": 80, "max": 100}, ...]
        indicators = []
        values = []
        
        for item in data:
            name = item.get("name", f"Indicator{len(indicators)}")
            max_val = item.get("max", 100)
            indicators.append({"name": name, "max": max_val})
            values.append(item.get("value", 0))
        
        if "radar" in config:
            config["radar"]["indicator"] = indicators
        
        if "series" in config and len(config["series"]) > 0:
            config["series"][0]["data"] = [{"value": values, "name": "Data"}]
    
    def _apply_heatmap_data(self, config: Dict, data: List[Dict]):
        """应用热力图数据"""
        if not data:
            return
        
        # 假设数据格式: [{"x": "Mon", "y": "Hour1", "value": 10}, ...]
        x_values = sorted(set(item.get("x", "") for item in data))
        y_values = sorted(set(item.get("y", "") for item in data))
        
        heatmap_data = []
        for item in data:
            x_idx = x_values.index(item.get("x", "")) if item.get("x") in x_values else 0
            y_idx = y_values.index(item.get("y", "")) if item.get("y") in y_values else 0
            value = item.get("value", 0)
            heatmap_data.append([x_idx, y_idx, value])
        
        if "xAxis" in config:
            config["xAxis"]["data"] = x_values
        if "yAxis" in config:
            config["yAxis"]["data"] = y_values
        if "series" in config and len(config["series"]) > 0:
            config["series"][0]["data"] = heatmap_data
    
    def _apply_gauge_data(self, config: Dict, data: List[Dict]):
        """应用仪表盘数据"""
        if not data:
            data = [{"name": "Value", "value": 0}]
        
        if "series" in config and len(config["series"]) > 0:
            config["series"][0]["data"] = [{
                "name": item.get("name", "Value"),
                "value": item.get("value", 0)
            } for item in data]
    
    def _apply_funnel_data(self, config: Dict, data: List[Dict]):
        """应用漏斗图数据"""
        if not data:
            return
        
        keys = list(data[0].keys())
        name_field = keys[0] if keys else "name"
        value_field = keys[1] if len(keys) > 1 else "value"
        
        funnel_data = []
        legend_data = []
        
        for item in data:
            name = item.get(name_field, "")
            value = item.get(value_field, 0)
            funnel_data.append({"name": name, "value": value})
            legend_data.append(name)
        
        if "series" in config and len(config["series"]) > 0:
            config["series"][0]["data"] = funnel_data
        
        if "legend" in config:
            config["legend"]["data"] = legend_data
    
    def _apply_treemap_data(self, config: Dict, data: List[Dict]):
        """应用树图数据"""
        if not data:
            return
        
        # 假设数据格式: [{"name": "A", "value": 10, "children": [...]}, ...]
        if "series" in config and len(config["series"]) > 0:
            config["series"][0]["data"] = data
    
    def _deep_merge(self, target: Dict, source: Dict):
        """深度合并字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def update_chart_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """更新图表数据"""
        chart_id = arguments.get("chart_id")
        data = arguments.get("data", [])
        
        if not chart_id:
            return {"error": "chart_id is required"}
        
        if chart_id not in self.charts:
            return {"error": f"Chart {chart_id} not found"}
        
        chart = self.charts[chart_id]
        chart["data"] = data
        chart["config"].data = data
        
        # 重新生成配置
        echarts_config = self._generate_echarts_config(chart["config"])
        chart["echarts_config"] = echarts_config
        
        # 重新生成HTML
        options_json = json.dumps(echarts_config, default=str, ensure_ascii=False)
        html = self.template.render(
            chart_id=chart_id,
            title=chart["config"].title,
            width=chart["config"].width,
            height=chart["config"].height,
            options_json=options_json,
            use_map=chart["config"].type == ChartType.MAP,
            data_count=len(data),
            update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            enable_animation=True
        )
        
        chart["echarts_html"] = html
        
        return {
            "success": True,
            "chart_id": chart_id,
            "echarts_html": html,
            "config": echarts_config,
            "updated_at": datetime.now().isoformat()
        }
    
    def get_chart_html(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """获取图表HTML"""
        chart_id = arguments.get("chart_id")
        
        if not chart_id:
            return {"error": "chart_id is required"}
        
        if chart_id not in self.charts:
            return {"error": f"Chart {chart_id} not found"}
        
        chart = self.charts[chart_id]
        return {
            "success": True,
            "chart_id": chart_id,
            "echarts_html": chart.get("echarts_html", chart.get("html")),
            "config": chart["echarts_config"],
            "created_at": chart["created_at"].isoformat()
        }
    
    def delete_chart(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """删除图表"""
        chart_id = arguments.get("chart_id")
        
        if not chart_id:
            return {"error": "chart_id is required"}
        
        if chart_id in self.charts:
            del self.charts[chart_id]
            return {"success": True, "chart_id": chart_id}
        else:
            return {"error": f"Chart {chart_id} not found"}
    
    def list_charts(self) -> Dict[str, Any]:
        """列出所有图表"""
        charts_info = []
        for chart_id, chart in self.charts.items():
            charts_info.append({
                "chart_id": chart_id,
                "title": chart["config"].title,
                "type": chart["config"].type,
                "data_count": len(chart["data"]),
                "created_at": chart["created_at"].isoformat()
            })
        
        return {
            "success": True,
            "charts": charts_info,
            "total_count": len(charts_info)
        }
    
    def analyze_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """数据分析"""
        data = arguments.get("data", [])
        analysis_type = arguments.get("analysis_type", "summary")
        
        if not data:
            return {"error": "Data is required"}
        
        try:
            if analysis_type == "summary":
                return self._data_summary(data)
            elif analysis_type == "correlation":
                return self._correlation_analysis(data)
            elif analysis_type == "distribution":
                return self._distribution_analysis(data)
            else:
                return {"error": f"Unknown analysis type: {analysis_type}"}
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}
    
    def _data_summary(self, data: List[Dict]) -> Dict[str, Any]:
        """数据摘要分析"""
        if not data:
            return {"error": "No data to analyze"}
        
        keys = list(data[0].keys())
        summary = {}
        
        for key in keys:
            values = [item.get(key) for item in data if item.get(key) is not None]
            if not values:
                continue
            
            if isinstance(values[0], (int, float)):
                # 数值型数据
                summary[key] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values),
                    "median": np.median(values),
                    "std": np.std(values),
                    "quartiles": {
                        "q1": np.percentile(values, 25),
                        "q2": np.percentile(values, 50),
                        "q3": np.percentile(values, 75)
                    }
                }
            else:
                # 分类型数据
                unique_vals = list(set(values))
                value_counts = {}
                for val in values:
                    value_counts[val] = value_counts.get(val, 0) + 1
                
                summary[key] = {
                    "count": len(values),
                    "unique": len(unique_vals),
                    "most_common": max(value_counts.items(), key=lambda x: x[1]) if value_counts else None,
                    "value_distribution": value_counts
                }
        
        return {
            "success": True,
            "analysis_type": "summary",
            "total_records": len(data),
            "fields": summary
        }
    
    def _correlation_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """相关性分析"""
        if not data:
            return {"error": "No data to analyze"}
        
        numeric_fields = []
        keys = list(data[0].keys())
        
        for key in keys:
            values = [item.get(key) for item in data if isinstance(item.get(key), (int, float))]
            if len(values) > 0:
                numeric_fields.append(key)
        
        if len(numeric_fields) < 2:
            return {"error": "Need at least 2 numeric fields for correlation analysis"}
        
        correlations = {}
        for i, field1 in enumerate(numeric_fields):
            for field2 in numeric_fields[i+1:]:
                values1 = [item.get(field1) for item in data if isinstance(item.get(field1), (int, float))]
                values2 = [item.get(field2) for item in data if isinstance(item.get(field2), (int, float))]
                
                if len(values1) == len(values2) and len(values1) > 1:
                    correlation = np.corrcoef(values1, values2)[0, 1]
                    correlations[f"{field1}_vs_{field2}"] = {
                        "correlation": float(correlation) if not np.isnan(correlation) else 0,
                        "strength": self._interpret_correlation(abs(correlation)),
                        "direction": "positive" if correlation > 0 else "negative"
                    }
        
        return {
            "success": True,
            "analysis_type": "correlation",
            "numeric_fields": numeric_fields,
            "correlations": correlations
        }
    
    def _distribution_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """分布分析"""
        if not data:
            return {"error": "No data to analyze"}
        
        keys = list(data[0].keys())
        distributions = {}
        
        for key in keys:
            values = [item.get(key) for item in data if item.get(key) is not None]
            if not values:
                continue
            
            if isinstance(values[0], (int, float)):
                # 数值型分布
                distributions[key] = {
                    "type": "numeric",
                    "histogram": self._create_histogram(values),
                    "outliers": self._detect_outliers(values)
                }
            else:
                # 分类型分布
                value_counts = {}
                for val in values:
                    value_counts[val] = value_counts.get(val, 0) + 1
                
                distributions[key] = {
                    "type": "categorical",
                    "frequency": value_counts,
                    "entropy": self._calculate_entropy(list(value_counts.values()))
                }
        
        return {
            "success": True,
            "analysis_type": "distribution",
            "distributions": distributions
        }
    
    def _interpret_correlation(self, corr_value: float) -> str:
        """解释相关性强度"""
        abs_corr = abs(corr_value)
        if abs_corr >= 0.8:
            return "very_strong"
        elif abs_corr >= 0.6:
            return "strong"
        elif abs_corr >= 0.4:
            return "moderate"
        elif abs_corr >= 0.2:
            return "weak"
        else:
            return "very_weak"
    
    def _create_histogram(self, values: List[float], bins: int = 10) -> List[Dict]:
        """创建直方图数据"""
        if not values:
            return []
        
        min_val, max_val = min(values), max(values)
        bin_width = (max_val - min_val) / bins
        histogram = []
        
        for i in range(bins):
            bin_start = min_val + i * bin_width
            bin_end = bin_start + bin_width
            count = sum(1 for v in values if bin_start <= v < bin_end)
            
            if i == bins - 1:  # 最后一个bin包含最大值
                count = sum(1 for v in values if bin_start <= v <= bin_end)
            
            histogram.append({
                "range": f"{bin_start:.2f}-{bin_end:.2f}",
                "count": count,
                "frequency": count / len(values)
            })
        
        return histogram
    
    def _detect_outliers(self, values: List[float]) -> List[float]:
        """检测异常值"""
        if len(values) < 4:
            return []
        
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [v for v in values if v < lower_bound or v > upper_bound]
        return outliers
    
    def _calculate_entropy(self, counts: List[int]) -> float:
        """计算信息熵"""
        if not counts:
            return 0
        
        total = sum(counts)
        probabilities = [c / total for c in counts if c > 0]
        entropy = -sum(p * np.log2(p) for p in probabilities)
        return float(entropy)
    
    def get_definition(self, interface_type: InterfaceType = InterfaceType.FULL) -> Dict[str, Any]:
        """获取工具定义"""
        actions = [
            "create_chart", "update_chart", "get_chart", 
            "delete_chart", "list_charts", "analyze_data"
        ]
        
        chart_types = [
            ChartType.LINE, ChartType.BAR, ChartType.PIE, ChartType.SCATTER,
            ChartType.AREA, ChartType.RADAR, ChartType.HEATMAP,
            ChartType.GAUGE, ChartType.FUNNEL, ChartType.TREEMAP
        ]
        
        analysis_types = ["summary", "correlation", "distribution"]
        
        schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": actions,
                    "description": "The action to perform"
                },
                "type": {
                    "type": "string",
                    "enum": chart_types,
                    "description": "Chart type (for create_chart action)"
                },
                "title": {
                    "type": "string",
                    "description": "Chart title"
                },
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Chart data (list of JSON objects)"
                },
                "width": {
                    "type": "string",
                    "default": "800px",
                    "description": "Chart width (e.g., '800px', '100%')"
                },
                "height": {
                    "type": "string",
                    "default": "400px",
                    "description": "Chart height (e.g., '400px', '50%')"
                },
                "options": {
                    "type": "object",
                    "description": "Custom ECharts options to merge with default configuration"
                },
                "enable_animation": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable chart animations"
                },
                "chart_id": {
                    "type": "string",
                    "description": "Chart ID (for update_chart, get_chart, delete_chart actions)"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": analysis_types,
                    "description": "Type of data analysis (for analyze_data action)"
                }
            },
            "required": ["action"]
        }
        
        if interface_type == InterfaceType.COMPACT:
            return {
                "name": self.name,
                "description": "Advanced ECharts tool with HTML output and data analysis.",
                "input_schema": schema
            }
        
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "input_schema": schema,
            "examples": [
                {
                    "action": "create_chart",
                    "type": "bar",
                    "title": "Sales Data",
                    "data": [
                        {"month": "Jan", "sales": 100, "profit": 20},
                        {"month": "Feb", "sales": 150, "profit": 30},
                        {"month": "Mar", "sales": 120, "profit": 25}
                    ]
                },
                {
                    "action": "analyze_data",
                    "analysis_type": "summary",
                    "data": [
                        {"age": 25, "income": 50000},
                        {"age": 30, "income": 60000},
                        {"age": 35, "income": 75000}
                    ]
                }
            ]
        }
