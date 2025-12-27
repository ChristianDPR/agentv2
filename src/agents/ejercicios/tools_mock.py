"""
Tools Mock - Para ejercicios de function calling

Tools simples para experimentar sin dependencias externas.
"""

from typing import Any, Dict
from src.tools.checklist_tool import Tool, ToolDefinition


class WeatherTool(Tool):
    """Tool mock que retorna clima ficticio."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_weather",
            description="Obtiene el clima actual de una ciudad",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Nombre de la ciudad"}
                },
                "required": ["city"]
            }
        )

    async def execute(self, city: str) -> Dict[str, Any]:
        # Mock - siempre retorna datos ficticios
        return {"city": city, "temp": 22, "condition": "soleado"}


class CalculatorTool(Tool):
    """Tool que hace operaciones matemáticas básicas."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculate",
            description="Realiza operaciones matemáticas: sum, subtract, multiply, divide",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["sum", "subtract", "multiply", "divide"]},
                    "a": {"type": "number", "description": "Primer número"},
                    "b": {"type": "number", "description": "Segundo número"}
                },
                "required": ["operation", "a", "b"]
            }
        )

    async def execute(self, operation: str, a: float, b: float) -> Dict[str, Any]:
        ops = {
            "sum": a + b,
            "subtract": a - b,
            "multiply": a * b,
            "divide": a / b if b != 0 else "Error: división por cero"
        }
        return {"operation": operation, "a": a, "b": b, "result": ops.get(operation, "Unknown")}


class TimeTool(Tool):
    """Tool que retorna la hora actual."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_time",
            description="Obtiene la fecha y hora actual",
            parameters={"type": "object", "properties": {}, "required": []}
        )

    async def execute(self) -> Dict[str, Any]:
        from datetime import datetime
        now = datetime.now()
        return {"date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S")}
