"""
Retrieval Tool usando Agent RAG

Wrapper que expone el sistema Agent RAG como una tool para agentes.
"""

from typing import Dict, Any
from src.tools.checklist_tool import Tool, ToolDefinition
from src.rag.agent_based.retrieval import AgentRetrieval


class RetrievalAgentTool(Tool):
    """
    Tool de búsqueda usando Agent RAG (LLM como juez).

    PEDAGOGÍA:
    - Alternativa a RetrievalVectorTool
    - Más transparente: el LLM explica POR QUÉ es relevante
    - Más lento y costoso, pero más simple (no requiere vector store)
    """

    def __init__(self, agent_retrieval: AgentRetrieval):
        """
        Args:
            agent_retrieval: Sistema de retrieval con agentes
        """
        self.agent_retrieval = agent_retrieval

    @property
    def definition(self) -> ToolDefinition:
        """
        Define la tool para que el agente sepa usarla.

        PEDAGOGÍA:
        - Similar a RetrievalVectorTool pero menciona "evaluación inteligente"
        - El agente elegirá esta tool si necesita explicabilidad
        """
        return ToolDefinition(
            name="search_knowledge_base_agent",
            description="Busca información relevante en la base de conocimiento de procedimientos AFP usando evaluación inteligente por IA. Más transparente que la búsqueda vectorial, ya que explica por qué cada resultado es relevante.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta de búsqueda del usuario"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Número de resultados a retornar (default 3, máximo 5 para evitar lentitud)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        )

    async def execute(
        self,
        query: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Ejecuta búsqueda con Agent RAG.

        PEDAGOGÍA:
        - Similar a RetrievalVectorTool pero:
          * Default top_k=3 (más lento, así que menos resultados)
          * Incluye "reasoning" en cada resultado
          * No soporta filtros de categoría (evaluaría menos docs)

        Args:
            query: Consulta de búsqueda
            top_k: Número de resultados (max 5)

        Returns:
            Dict con:
            - chunks: Lista de chunks con reasoning del LLM
            - method: "agent_rag"
            - query: Query original
        """
        # Limitar top_k para evitar excesiva lentitud
        top_k = min(top_k, 5)

        # Delegar a AgentRetrieval
        result = await self.agent_retrieval.retrieve(
            query=query,
            k=top_k
        )

        # Agregar query original
        result["query"] = query

        return result
