"""
Agente Asistente de Procedimientos AFP

Prototipo 1: Combina retrieval (RAG) + generación de checklists
Usa un agente clasificador para decisiones inteligentes
"""

from typing import Dict, Any, Literal
from src.framework.base_agent import BaseAgent, AgentResponse
from src.framework.model_provider import ModelProvider
from src.tools.checklist_tool import ChecklistTool
from src.tools.retrieval_vector_tool import RetrievalVectorTool
from src.tools.retrieval_agent_tool import RetrievalAgentTool
from src.agents.asistente.intent_classifier import IntentClassifierAgent


class AgenteAsistente(BaseAgent):
    """
    Agente que asiste con consultas sobre procedimientos AFP.

    PEDAGOGÍA:
    - Este es el PROTOTIPO 1 del curso
    - Usa 2 tools: Retrieval + Checklist
    - Puede elegir entre 2 estrategias de RAG: vector o agent
    - Flujo: Query → Retrieval → Checklist → Respuesta con citas
    """

    def __init__(
        self,
        model_provider: ModelProvider,
        retrieval_vector_tool: RetrievalVectorTool,
        retrieval_agent_tool: RetrievalAgentTool,
        checklist_tool: ChecklistTool,
        agentic_rag: bool = False
    ):
        """
        Args:
            model_provider: Proveedor de LLM
            retrieval_vector_tool: Tool de retrieval vectorial
            retrieval_agent_tool: Tool de retrieval con agente
            checklist_tool: Tool de generación de checklists
            agentic_rag: Si True, usa Agent RAG; si False, usa Vector RAG
        """
        super().__init__(
            name="AgenteAsistente",
            description="Asistente para consultas sobre procedimientos AFP"
        )

        self.model_provider = model_provider
        self.retrieval_vector_tool = retrieval_vector_tool
        self.retrieval_agent_tool = retrieval_agent_tool
        self.checklist_tool = checklist_tool
        self.agentic_rag = agentic_rag

        # PEDAGOGÍA: Usamos un AGENTE para clasificación, no keywords!
        # Esto demuestra composición de agentes
        self.intent_classifier = IntentClassifierAgent(model_provider=model_provider)

    async def run(
        self,
        query: str,
        context: Dict[str, Any] | None = None,
        use_checklist: bool = True
    ) -> AgentResponse:
        """
        Procesa una consulta del usuario.

        PEDAGOGÍA:
        - Flujo simplificado (sin orchestration loop complejo):
          1. Retrieval para encontrar procedimientos relevantes
          2. Si la query pide pasos, generar checklist
          3. Generar respuesta final con citas

        Args:
            query: Consulta del usuario
            context: Contexto adicional (opcional)

        Returns:
            AgentResponse con content y metadata
        """
        # 1. Seleccionar tool de retrieval según estrategia
        retrieval_tool = (
            self.retrieval_agent_tool if self.agentic_rag
            else self.retrieval_vector_tool
        )

        # 2. Buscar información relevante
        retrieval_result = await retrieval_tool.execute(
            query=query,
            top_k=5 if not self.agentic_rag else 3
        )

        chunks = retrieval_result["chunks"]

        # 3. VALIDACIÓN CRÍTICA: Si no hay chunks, NO inventar respuestas
        # PEDAGOGÍA: Anti-alucinación - RAG sin grounding = No respuesta
        if not chunks or len(chunks) == 0:
            return AgentResponse(
                content=(
                    "Lo siento, no encontré información específica sobre tu consulta "
                    "en la base de conocimiento de procedimientos AFP. "
                    "Por favor, reformula tu pregunta o contacta al área correspondiente."
                ),
                metadata={
                    "retrieval_method": retrieval_result["method"],
                    "chunks_used": 0,
                    "checklist_generated": False,
                    "error": "no_chunks_found"
                }
            )

        # 4. Determinar si necesita checklist usando AGENTE clasificador
        # PEDAGOGÍA: Esto es un agente tomando decisión, no keywords!

        checklist = None
        if use_checklist:
            classification = await self.intent_classifier.classify(query)
            needs_checklist = classification["needs_checklist"]

            if needs_checklist and chunks:
                # Generar checklist 
                procedure_text = "".join(chunk.page_content for chunk in chunks)
                checklist = await self.checklist_tool.execute(
                    procedure_text=procedure_text
                )

        # 5. Generar respuesta final
        response_content = await self._generate_response(
            query=query,
            chunks=chunks,
            checklist=checklist,
            method=retrieval_result["method"]
        )

        # 6. Preparar metadata
        metadata = {
            "retrieval_method": retrieval_result["method"],
            "chunks_used": len(chunks),
            "checklist_generated": checklist is not None,
            "chunks": chunks,  # Para debugging
        }

        if checklist:
            metadata["checklist"] = checklist

        return AgentResponse(
            content=response_content,
            metadata=metadata
        )

    def _needs_checklist(self, query: str) -> bool:
        """
        Determina si la query requiere un checklist.

        PEDAGOGÍA:
        - Heurística simple: buscar palabras clave
        - Alternativa avanzada: usar LLM para clasificar (más costoso)
        """
        keywords = [
            "cómo", "como", "pasos", "paso a paso",
            "proceso", "procedimiento", "requisitos",
            "qué necesito", "que necesito"
        ]

        query_lower = query.lower()
        return any(keyword in query_lower for keyword in keywords)

    async def _generate_response(
        self,
        query: str,
        chunks: list,
        checklist: Dict[str, Any] | None,
        method: str
    ) -> str:
        """
        Genera la respuesta final usando el LLM.

        PEDAGOGÍA:
        - Prompt estructurado con contexto claro
        - Incluye chunks con citas
        - Incluye checklist si existe
        - Instrucciones claras para el LLM
        """
        # Construir contexto de chunks con citas
        context_text = "\n\n".join([
            f"Fragmento {i+1}:\n{chunk['content']}\n{chunk['citation']}"
            for i, chunk in enumerate(chunks[:3])  # Top 3
        ])

        # Agregar checklist si existe
        checklist_text = ""
        if checklist and "steps" in checklist:
            steps_text = "\n".join([
                f"{step['step_number']}. {step['action']}"
                for step in checklist["steps"]
            ])
            checklist_text = f"""

CHECKLIST DE PASOS:
{steps_text}
"""

        # Construir prompt para el LLM
        prompt = f"""Eres un asistente experto en procedimientos AFP Integra.

CONSULTA DEL USUARIO:
{query}

INFORMACIÓN RELEVANTE ENCONTRADA (método: {method}):
{context_text}
{checklist_text}

INSTRUCCIONES:
1. Responde la consulta del usuario de forma clara y precisa
2. IMPORTANTE: Cuando cites información, usa EXACTAMENTE las citas que aparecen después de cada fragmento (ej: [Doc: PROC-JUB-001 (jubilacion), relevancia: 85%]). NO uses "[Fragmento 1]" ni inventesnúmeros.
3. Si hay checklist, preséntalo de forma ordenada
4. Si no encuentras información suficiente, di "No encontré información específica sobre esto en la base de conocimiento"
5. Sé conciso pero completo

RESPUESTA:"""

        # Generar respuesta
        response = await self.model_provider.generate(
            prompt=prompt,
            temperature=0.7,  # Balance entre creatividad y consistencia
            max_tokens=3000
        )

        return response.strip()
