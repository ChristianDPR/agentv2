"""
Retrieval Tool usando Vector RAG

Wrapper que expone el sistema Vector RAG como una tool para agentes.
"""

from typing import Dict, Any
from src.tools.checklist_tool import Tool, ToolDefinition
from src.rag.vector_based.retrieval import VectorRetrieval


class RetrievalVectorTool(Tool):
    """
    Tool de búsqueda semántica usando Vector RAG.

    PEDAGOGÍA:
    - Esta tool ENCAPSULA el Vector RAG completo
    - El agente solo necesita llamar esta tool, no saber cómo funciona internamente
    - Patrón Facade: interfaz simple para sistema complejo
    """

    def __init__(self, vector_retrieval: VectorRetrieval):
        """
        Args:
            vector_retrieval: Sistema de retrieval vectorial
        """
        self.vector_retrieval = vector_retrieval

    @property
    def definition(self) -> ToolDefinition:
        """
        Define la tool para que el agente sepa usarla.

        PEDAGOGÍA:
        - 'description' debe ser MUY clara: el agente decide basándose en esto
        - Mencionar que usa "base de conocimiento" es más comprensible que "vector search"
        - Los parámetros son simples: query + opciones
        """
        return ToolDefinition(
            name="search_knowledge_base",
            description="Busca información relevante en la base de conocimiento de procedimientos AFP usando búsqueda semántica vectorial. Úsala cuando necesites encontrar documentos o procedimientos relevantes para una consulta.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta de búsqueda del usuario"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Número de resultados a retornar (default 5)",
                        "default": 5
                    },
                    "category": {
                        "type": "string",
                        "description": "Filtrar por categoría específica (opcional): jubilacion, afiliacion, traspasos, aportes, devoluciones",
                        "enum": ["jubilacion", "afiliacion", "traspasos", "aportes", "devoluciones"]
                    }
                },
                "required": ["query"]
            }
        )

    async def execute(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None
    ) -> Dict[str, Any]:
        """
        Ejecuta búsqueda vectorial en la base de conocimiento.

        PEDAGOGÍA:
        - Esta es la "interfaz pública" de la tool
        - Delega todo el trabajo pesado a VectorRetrieval
        - Solo formatea el resultado para el agente

        Args:
            query: Consulta de búsqueda
            top_k: Número de resultados
            category: Filtro de categoría opcional

        Returns:
            Dict con:
            - chunks: Lista de chunks relevantes con citas
            - method: "vector_rag" (para debugging)
            - query: Query original (para contexto)
        """
        # Preparar filtros si hay categoría
        filter_metadata = None
        if category:
            filter_metadata = {"category": category}

        # Delegar a VectorRetrieval
        result = await self.vector_retrieval.retrieve(
            query=query,
            k=top_k,
            filter_metadata=filter_metadata
        )

        # Agregar query original al resultado (útil para logging)
        result["query"] = query

        return result

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la base de conocimiento.

        Útil para debugging y monitoring.
        """
        return await self.vector_retrieval.vector_store.get_statistics()
