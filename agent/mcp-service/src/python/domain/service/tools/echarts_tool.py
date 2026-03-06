from typing import Dict, Any, List
import json
from domain.model.tool import BaseTool, InterfaceType

class EChartsTool(BaseTool):
    def __init__(self):
        self.name = "echarts_tool"
        self.description = "A tool for generating ECharts configurations and performing basic data analysis. It can create line, bar, pie, and scatter charts, and calculate data summaries."

    def execute(self, arguments: Dict[str, Any]) -> Any:
        action = arguments.get("action")
        data = arguments.get("data")
        
        if not action:
            return {"error": "Action is required (generate_chart or analyze_data)"}
        # if not data:
        #     return {"error": "Data is required"}
            
        if action == "generate_chart":
            config = arguments.get("chart_config", {})
            if not data:
                data = self._generate_sample_data()
            return self._generate_chart(data, config)
        elif action == "analyze_data":
            if not data:
                return {"error": "Data is required for analysis"}
            config = arguments.get("analysis_config", {})
            return self._analyze_data(data, config)
        else:
            return {"error": f"Unknown action: {action}"}

    def _generate_sample_data(self) -> List[Dict[str, Any]]:
        """Generate sample data when no data is provided"""
        return [
            {"name": "Category A", "value": 120},
            {"name": "Category B", "value": 200},
            {"name": "Category C", "value": 150},
            {"name": "Category D", "value": 80},
            {"name": "Category E", "value": 70}
        ]

    def _generate_chart(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        chart_type = config.get("type", "bar")
        title = config.get("title", "Chart")
        x_field = config.get("x_field")
        y_fields = config.get("y_fields", [])
        
        if not x_field and chart_type in ["line", "bar", "scatter"]:
             # Try to infer x_field
             if data and len(data) > 0:
                 keys = list(data[0].keys())
                 # Heuristic: first key that looks like a name/date
                 x_field = keys[0]
        
        if not y_fields and chart_type in ["line", "bar", "scatter"]:
            # Try to infer y_fields (numeric columns)
             if data and len(data) > 0:
                 keys = list(data[0].keys())
                 y_fields = [k for k in keys if k != x_field and isinstance(data[0][k], (int, float))]

        option = {
            "title": {"text": title},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": y_fields},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "toolbox": {"feature": {"saveAsImage": {}}}
        }

        if chart_type in ["line", "bar", "scatter"]:
            x_data = [item.get(x_field, "") for item in data]
            option["xAxis"] = {"type": "category", "boundaryGap": False if chart_type == "line" else True, "data": x_data}
            option["yAxis"] = {"type": "value"}
            
            series = []
            for y_field in y_fields:
                series_data = [item.get(y_field, 0) for item in data]
                series.append({
                    "name": y_field,
                    "type": chart_type,
                    "data": series_data
                })
            option["series"] = series

        elif chart_type == "pie":
            # For pie chart, we typically need name and value
            # Assume x_field is name, first y_field is value
            if not y_fields and data and len(data) > 0:
                 keys = list(data[0].keys())
                 y_fields = [k for k in keys if isinstance(data[0][k], (int, float))]
            
            val_field = y_fields[0] if y_fields else None
            
            pie_data = []
            if val_field:
                for item in data:
                    pie_data.append({
                        "name": item.get(x_field, "Unknown"),
                        "value": item.get(val_field, 0)
                    })
            
            option["tooltip"] = {"trigger": "item"}
            option["series"] = [{
                "name": title,
                "type": "pie",
                "radius": "50%",
                "data": pie_data,
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
            # Remove axes for pie
            option.pop("xAxis", None)
            option.pop("yAxis", None)
            option.pop("grid", None)

        return {"echarts_option": option}

    def _analyze_data(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        # Basic summary statistics
        if not data:
            return {"error": "No data to analyze"}
            
        keys = list(data[0].keys())
        summary = {}
        
        for key in keys:
            values = [item.get(key) for item in data if item.get(key) is not None]
            if not values:
                continue
                
            # Check if numeric
            if isinstance(values[0], (int, float)):
                summary[key] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values)
                }
            else:
                # Categorical
                unique_vals = set(values)
                summary[key] = {
                    "count": len(values),
                    "unique": len(unique_vals),
                    "sample": values[:3]
                }
                
        return {"summary": summary}

    def get_definition(self, interface_type: InterfaceType = InterfaceType.FULL) -> Dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["generate_chart", "analyze_data"],
                    "description": "The action to perform."
                },
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "The dataset to process (list of JSON objects). If not provided for generate_chart, sample data will be used."
                },
                "chart_config": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["line", "bar", "pie", "scatter"], "description": "Chart type"},
                        "title": {"type": "string", "description": "Chart title"},
                        "x_field": {"type": "string", "description": "Field name for X-axis (category)"},
                        "y_fields": {"type": "array", "items": {"type": "string"}, "description": "Field names for Y-axis (values)"}
                    }
                },
                "analysis_config": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["summary"], "description": "Type of analysis"}
                    }
                }
            },
            "required": ["action"]
        }
        
        if interface_type == InterfaceType.COMPACT:
             return {
                "name": self.name,
                "description": "Generate ECharts or analyze data.",
                "input_schema": schema
            }
            
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": schema
        }
