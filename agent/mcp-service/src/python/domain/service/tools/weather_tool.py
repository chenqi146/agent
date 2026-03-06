from typing import Dict, Any
from domain.model.tool import BaseTool, InterfaceType

class WeatherTool(BaseTool):
    def __init__(self):
        self.name = "get_weather"
        self.description = "Get current weather information for a specific location."
        self.tags = ["weather"]

    def execute(self, arguments: Dict[str, Any]) -> Any:
        location = arguments.get("location")
        if not location:
            return {"error": "Location is required"}
        
        # Mock implementation
        weather_data = {
            "location": location,
            "temperature": "25°C",
            "condition": "Sunny",
            "humidity": "60%",
            "wind": "10 km/h NW"
        }
        return weather_data

    def get_definition(self, interface_type: InterfaceType = InterfaceType.FULL) -> Dict[str, Any]:
        if interface_type == InterfaceType.COMPACT:
             return {
                "name": self.name,
                "description": "Get weather for location.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    },
                    "required": ["location"]
                }
            }
        
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit of temperature"
                    }
                },
                "required": ["location"]
            }
        }
