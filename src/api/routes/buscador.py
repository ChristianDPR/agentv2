"""
Endpoints de la API para el Agente Buscador (BigQuery)

Este módulo expone un endpoint REST que permite ejecutar búsquedas
multi-fuente (BigQuery + documentos) usando el Agente Buscador.
"""

from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import os
import time
import uuid

from fastapi import APIRouter, HTTPException, status

from src.api.models import ChatRequest, ChatResponse
from src.agents.buscador import create_agente_buscador_bigquery
from src.framework.model_provider import VertexAIProvider


# =============================================================================
# Configuración de entorno
# =============================================================================

dotenv_path = find_dotenv()
if not dotenv_path:
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    dotenv_path = project_root / ".env"

load_dotenv(dotenv_path=dotenv_path, override=True)


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(
    prefix="/buscador",
    tags=["Agente Buscador"],
    responses={404: {"description": "Not found"}}
)


# =============================================================================
# Inicialización del agente y dependencias
# =============================================================================

def _get_documents_path() -> Path:
    default_path = Path(__file__).resolve().parent.parent.parent / "data" / "documentos_afiliados"
    return Path(os.getenv("BUSCADOR_DOCUMENTS_PATH", default_path)).resolve()


def _get_bigquery_project() -> str | None:
    return os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEX_AI_PROJECT")


def _ensure_bigquery_credentials() -> None:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and not Path(credentials_path).exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_APPLICATION_CREDENTIALS apunta a un archivo inexistente."
        )


model_provider = VertexAIProvider()

agente_buscador = create_agente_buscador_bigquery(
    model_provider=model_provider,
    documents_path=_get_documents_path(),
    bigquery_project=_get_bigquery_project(),
    default_dataset=os.getenv("BIGQUERY_DEFAULT_DATASET")
)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_buscador(request: ChatRequest) -> ChatResponse:
    """
    Endpoint de chat para el Agente Buscador.

    Ejecuta la consulta usando BigQuery + documentos locales.
    """
    _ensure_bigquery_credentials()
    start_time = time.time()

    try:
        result = await agente_buscador.run(query=request.query)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc

    processing_time_ms = int((time.time() - start_time) * 1000)

    return ChatResponse(
        message_id=str(uuid.uuid4()),
        content=result.content,
        checklist=None,
        citations=[],
        retrieval_method=None,
        confidence_score=result.metadata.get("confidence"),
        processing_time_ms=processing_time_ms,
        chunks_used=0
    )
