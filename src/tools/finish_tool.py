"""
Finish Tool - Termina el loop ReAct

Tool para el Agente Buscador que señala el fin de la búsqueda
y genera la respuesta final consolidada.
"""

from typing import Any, Dict, List
from src.tools.checklist_tool import Tool, ToolDefinition


class FinishTool(Tool):
    """
    Tool para terminar el loop de búsqueda.

    Cuando el LLM llama a esta tool, indica que tiene
    suficiente información para responder al usuario.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="finish",
            description="Termina la búsqueda y genera la respuesta final con la información recopilada. Usa esta tool cuando tengas suficiente información para responder.",
            parameters={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Resumen de los hallazgos principales para el usuario"
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de fuentes consultadas (queries SQL, documentos)"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Nivel de confianza en la respuesta"
                    }
                },
                "required": ["summary"]
            }
        )

    async def execute(
        self,
        summary: str,
        sources: List[str] = None,
        confidence: str = "medium"
    ) -> Dict[str, Any]:
        """
        Procesa la señal de finalización.

        Esta tool simplemente retorna los datos estructurados
        que el agente usará para generar la respuesta final.

        Args:
            summary: Resumen de hallazgos
            sources: Fuentes consultadas
            confidence: Nivel de confianza

        Returns:
            Dict con summary, sources y confidence
        """
        return {
            "summary": summary,
            "sources": sources or [],
            "confidence": confidence,
            "finished": True
        }
