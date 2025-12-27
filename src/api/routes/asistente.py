"""
Endpoints de la API para el Agente Asistente de Procedimientos AFP

Este módulo implementa los endpoints REST que exponen el Agente Asistente
para uso en producción desde frontends web/mobile.

PEDAGOGÍA:
- Demuestra cómo integrar agentes en APIs de producción
- Muestra transformación de AgentResponse a formato API enriquecido
- Incluye manejo de errores y logging estructurado
- Genera URLs de ejemplo para citas con enlaces

CASO DE USO:
Frontend React/Vue llama a estos endpoints y renderiza:
- Texto de respuesta como markdown
- Checklist como componente interactivo
- Citas como enlaces clickeables a PDFs
"""

# CRÍTICO: Cargar .env ANTES de inicializar componentes
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

# Encontrar .env subiendo desde este archivo hasta la raíz del proyecto
dotenv_path = find_dotenv()
if not dotenv_path:
    # Fallback: buscar .env manualmente
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent  # src/api/routes -> src/api -> src -> root
    dotenv_path = project_root / ".env"

load_dotenv(dotenv_path=dotenv_path, override=True)

# DEBUGGING: Verificar que se cargó
import os
print(f"[DEBUG] VERTEX_AI_PROJECT cargado: {os.getenv('VERTEX_AI_PROJECT')}")

import time
import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pathlib import Path

from src.api.models import (
    ChatRequest,
    ChatResponse,
    Citation,
    Checklist,
    ChecklistStep
)
from src.agents.asistente.agent import AgenteAsistente
from src.agents.asistente.intent_classifier import IntentClassifierAgent
from src.framework.model_provider import VertexAIProvider
from src.tools.retrieval_vector_tool import RetrievalVectorTool
from src.tools.retrieval_agent_tool import RetrievalAgentTool
from src.tools.checklist_tool import ChecklistTool
from src.rag.vector_based.retrieval import VectorRetrieval
from src.rag.vector_based.vector_store import VectorStore
from src.rag.vector_based.embeddings import EmbeddingGenerator
from src.rag.agent_based.retrieval import AgentRetrieval
from src.rag.agent_based.document_reader import DocumentReader
from src.rag.agent_based.chunk_evaluator import ChunkEvaluator


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/asistente",
    tags=["Agente Asistente"],
    responses={404: {"description": "Not found"}}
)


# ============================================================================
# Dependency Injection - Instancias globales de tools y agente
# ============================================================================

# NOTA: En producción, estas instancias deberían ser manejadas por un
# dependency injection container (ej: FastAPI Depends) para mejor testing
# y gestión de lifecycle.

# Model provider
model_provider = VertexAIProvider()

# Vector RAG components
vector_store = VectorStore()
embedding_generator = EmbeddingGenerator()  # Usa config de env vars (VERTEX_AI_PROJECT)
vector_retrieval = VectorRetrieval(
    vector_store=vector_store,
    embedding_generator=embedding_generator
)
retrieval_vector_tool = RetrievalVectorTool(vector_retrieval=vector_retrieval)

# Agent RAG components
document_reader = DocumentReader()
chunk_evaluator = ChunkEvaluator(model_provider=model_provider)
agent_retrieval = AgentRetrieval(
    document_reader=document_reader,
    chunk_evaluator=chunk_evaluator
)
retrieval_agent_tool = RetrievalAgentTool(agent_retrieval=agent_retrieval)

# Checklist tool
checklist_tool = ChecklistTool(model_provider=model_provider)

# Intent classifier
intent_classifier = IntentClassifierAgent(model_provider=model_provider)

# Main agent (se inicializará con agentic_rag según request)


# ============================================================================
# Helper Functions
# ============================================================================

def _generate_document_url(metadata: Dict[str, Any]) -> str:
    """
    Genera URL de ejemplo al documento fuente.

    PEDAGOGÍA:
    En producción, estas URLs apuntarían a:
    - Cloud Storage (GCS, S3): https://storage.googleapis.com/bucket/{filename}
    - SharePoint: https://sharepoint.afp.com/docs/{doc_id}
    - Sistema interno: https://docs.afp.com/api/documents/{doc_id}/download

    Para el curso, usamos URLs de ejemplo: https://example.com/docs/{filename}#page={page}

    Args:
        metadata: Metadata del chunk con 'source' y 'page'

    Returns:
        URL de ejemplo al documento
    """
    source_file = metadata.get("source", "unknown.pdf")
    page = metadata.get("page", 1)

    # URL de ejemplo - en producción reemplazar con storage real
    # Ejemplo: https://storage.googleapis.com/afp-documentos/{source_file}#page={page}
    base_url = "https://example.com/docs"
    return f"{base_url}/{source_file}#page={page}"


def _calculate_confidence(citations: list) -> float:
    """
    Calcula score de confianza basado en los scores de las citas.

    PEDAGOGÍA:
    Confianza = promedio de scores de los top-K chunks.
    Esto da una métrica simple de qué tan relevante fue la información encontrada.

    En producción, podrías usar métricas más sofisticadas:
    - Weighted average (más peso al top chunk)
    - Considerar distribución de scores
    - Incluir otras señales (consistencia entre chunks, etc.)

    Args:
        citations: Lista de Citation objects con scores

    Returns:
        Score de confianza promedio (0.0 a 1.0)
    """
    if not citations:
        return 0.0

    scores = [c.score for c in citations]
    return sum(scores) / len(scores)


def _transform_checklist(checklist_data: Dict[str, Any]) -> Checklist:
    """
    Transforma checklist del agente a modelo API.

    PEDAGOGÍA:
    Convierte el dict plano del agente en el modelo Pydantic estructurado
    que el frontend espera. Agrega campos adicionales como progress_percentage.

    Args:
        checklist_data: Dict con estructura del checklist

    Returns:
        Modelo Checklist con todos los campos
    """
    steps = [
        ChecklistStep(
            step_number=step.get("step_number", idx + 1),
            action=step.get("action", ""),
            required_documents=step.get("required_documents", []),
            completed=False  # Inicia sin completar
        )
        for idx, step in enumerate(checklist_data.get("steps", []))
    ]

    return Checklist(
        title=checklist_data.get("title", "Procedimiento"),
        procedure_code=checklist_data.get("procedure_code", "UNKNOWN"),
        steps=steps,
        estimated_time=checklist_data.get("estimated_time"),
        sla=checklist_data.get("sla"),
        progress_percentage=0  # Inicia en 0%
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_asistente(request: ChatRequest) -> ChatResponse:
    """
    Endpoint de chat con el Agente Asistente de Procedimientos AFP.

    Este endpoint recibe una query del usuario y retorna una respuesta estructurada
    que incluye:
    - Texto de respuesta (content)
    - Checklist interactivo (si aplica)
    - Citas con enlaces a documentos fuente
    - Metadata para analytics

    PEDAGOGÍA:
    Demuestra cómo integrar un agente de IA en una API REST de producción.
    El frontend puede renderizar la respuesta de forma rica:
    - Markdown para el content
    - Componente de checklist interactivo
    - Enlaces clickeables a PDFs

    FLUJO:
    1. Inicializar agente con estrategia RAG elegida
    2. Ejecutar agente con query del usuario
    3. Transformar AgentResponse a formato API enriquecido
    4. Generar URLs para citas
    5. Calcular metadata (confidence, tiempo)
    6. Retornar ChatResponse estructurado

    Args:
        request: ChatRequest con query, session_id, y configuración

    Returns:
        ChatResponse con respuesta estructurada para renderizado rico

    Raises:
        HTTPException: Si hay error en el procesamiento

    Ejemplo de uso:
        POST /asistente/chat
        {
            "query": "¿Cómo puedo jubilarme anticipadamente?",
            "session_id": "user-123-session-456",
            "use_agentic_rag": false
        }

        Response:
        {
            "message_id": "msg-abc123",
            "role": "assistant",
            "content": "Para jubilarte anticipadamente necesitas...",
            "checklist": {
                "title": "Jubilación Anticipada",
                "steps": [...]
            },
            "citations": [
                {
                    "text": "[Doc: PROC-JUBILACION-003, pág 3]",
                    "url": "https://example.com/docs/jubilacion.pdf#page=3",
                    "score": 0.95
                }
            ],
            "confidence_score": 0.92,
            "processing_time_ms": 1234
        }
    """
    start_time = time.time()

    try:
        # 1. Inicializar agente con estrategia RAG elegida
        agente = AgenteAsistente(
            model_provider=model_provider,
            retrieval_vector_tool=retrieval_vector_tool,
            retrieval_agent_tool=retrieval_agent_tool,
            checklist_tool=checklist_tool,
            agentic_rag=request.use_agentic_rag
        )

        # 2. Ejecutar agente
        agent_response = await agente.run(
            query=request.query,
            context={"session_id": request.session_id}
        )

        # 3. Transformar chunks a citations con URLs
        citations = []
        if agent_response.metadata.get("chunks"):
            for chunk in agent_response.metadata["chunks"]:
                citation = Citation(
                    text=chunk.get("citation", ""),
                    url=_generate_document_url(chunk.get("metadata", {})),
                    document_id=chunk.get("metadata", {}).get("procedure_code", "UNKNOWN"),
                    page=chunk.get("metadata", {}).get("page", 1),
                    score=chunk.get("score", 0.0)
                )
                citations.append(citation)

        # 4. Transformar checklist si existe
        checklist = None
        if agent_response.metadata.get("checklist"):
            checklist = _transform_checklist(agent_response.metadata["checklist"])

        # 5. Calcular metadata
        processing_time_ms = int((time.time() - start_time) * 1000)
        confidence_score = _calculate_confidence(citations)

        # 6. Construir respuesta
        return ChatResponse(
            message_id=str(uuid.uuid4()),
            role="assistant",
            content=agent_response.content,
            checklist=checklist,
            citations=citations,
            retrieval_method=agent_response.metadata.get("retrieval_method"),
            confidence_score=confidence_score,
            processing_time_ms=processing_time_ms,
            chunks_used=agent_response.metadata.get("chunks_used", 0)
        )

    except Exception as e:
        # DEBUGGING: Imprimir traceback completo
        import traceback
        tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))

        print(f"\n{'='*80}")
        print(f"ERROR EN ENDPOINT /asistente/chat")
        print(f"{'='*80}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"\nFull traceback:")
        print(tb_str)
        print(f"{'='*80}\n")

        # En producción, aquí iría logging estructurado (structlog)
        # y telemetría (OpenTelemetry, Prometheus)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar consulta: {str(e)}"
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint para monitoreo.

    PEDAGOGÍA:
    En producción, este endpoint es usado por:
    - Load balancers (para health checks)
    - Kubernetes liveness/readiness probes
    - Sistemas de monitoreo (Prometheus, Datadog, etc.)

    Returns:
        Dict con status del servicio
    """
    return {
        "status": "healthy",
        "service": "agente-asistente",
        "version": "1.0.0"
    }
