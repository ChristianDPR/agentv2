"""
Modelos Pydantic para la API REST del curso COE-IA-TRAINING

Define las estructuras de request/response para los endpoints de chat.
Estas estructuras permiten renderizado rico en el frontend (checklists, citas con enlaces, etc.)

PEDAGOGÍA:
- Separación de content (texto) y structured data (checklist, citations)
- Response models que habilitan UIs ricas en el frontend
- Metadata para analytics y debugging
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime


# ============================================================================
# Citation Models - Para citas con enlaces a documentos fuente
# ============================================================================

class Citation(BaseModel):
    """
    Representa una cita a un documento fuente con enlace clickeable.

    CASO DE USO:
    El frontend puede renderizar estas citas como enlaces que abren
    el documento PDF en la página específica mencionada.

    Ejemplo:
        {
            "text": "[Doc: PROC-JUBILACION-003, pág 3, relevancia: 95%]",
            "url": "https://example.com/docs/jubilacion_anticipada.pdf#page=3",
            "document_id": "PROC-JUBILACION-003",
            "page": 3,
            "score": 0.95
        }
    """
    text: str = Field(
        description="Texto de la cita formateado para mostrar al usuario"
    )
    url: Optional[str] = Field(
        default=None,
        description=(
            "URL al documento fuente. Ejemplo: "
            "https://example.com/docs/{filename}#page={page}"
        )
    )
    document_id: str = Field(
        description="ID único del procedimiento (ej: PROC-JUBILACION-003)"
    )
    page: int = Field(
        default=1,
        description="Número de página del documento fuente"
    )
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score de relevancia del chunk (0.0 a 1.0)"
    )


# ============================================================================
# Checklist Models - Para checklists interactivos
# ============================================================================

class ChecklistStep(BaseModel):
    """
    Un paso individual del checklist.

    CASO DE USO:
    El frontend puede renderizar esto como un checkbox con documentos requeridos.
    El campo 'completed' permite tracking de progreso del usuario.
    """
    step_number: int = Field(
        description="Número del paso (1, 2, 3, ...)"
    )
    action: str = Field(
        description="Descripción clara y accionable de qué hacer en este paso"
    )
    required_documents: List[str] = Field(
        default_factory=list,
        description="Lista de documentos necesarios para este paso"
    )
    completed: bool = Field(
        default=False,
        description="Si el usuario ya completó este paso (para tracking de progreso)"
    )


class Checklist(BaseModel):
    """
    Checklist completo de un procedimiento AFP.

    CASO DE USO:
    El frontend renderiza esto como un componente interactivo con:
    - Checkboxes para marcar steps completados
    - Barra de progreso
    - Lista de documentos requeridos
    - SLA y tiempo estimado

    Ejemplo de UI:
        ✅ Jubilación Anticipada
        ══════════════════════════════════
        ☐ 1. Solicitar certificado AFP
             📄 RUT, Certificado de afiliación
        ☐ 2. Completar formulario F-2021
             📄 Formulario F-2021

        Progreso: 0/2 (0%)
        Tiempo estimado: 15 días hábiles
        SLA: 20 días
    """
    title: str = Field(
        description="Título del procedimiento"
    )
    procedure_code: str = Field(
        description="Código del procedimiento (ej: PROC-JUBILACION-003)"
    )
    steps: List[ChecklistStep] = Field(
        description="Lista de pasos del procedimiento"
    )
    estimated_time: Optional[str] = Field(
        default=None,
        description="Tiempo estimado para completar (ej: '15 días hábiles')"
    )
    sla: Optional[str] = Field(
        default=None,
        description="SLA del procedimiento (ej: '20 días')"
    )
    progress_percentage: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Porcentaje de pasos completados (calculado)"
    )


# ============================================================================
# Chat Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    """
    Request para el endpoint de chat.

    PEDAGOGÍA:
    - query: La pregunta del usuario
    - session_id: Para mantener contexto entre conversaciones
    - use_agentic_rag: Permite al usuario elegir qué estrategia RAG usar
    """
    query: str = Field(
        min_length=1,
        max_length=2000,
        description="Pregunta o consulta del usuario"
    )
    session_id: str = Field(
        description="ID de sesión para tracking y contexto"
    )
    use_agentic_rag: bool = Field(
        default=False,
        description=(
            "Si True, usa Agent RAG (LLM evalúa relevancia). "
            "Si False, usa Vector RAG (embeddings + similitud coseno)."
        )
    )


class ChatResponse(BaseModel):
    """
    Response del endpoint de chat con estructura enriquecida.

    PEDAGOGÍA:
    Esta estructura permite al frontend renderizar:
    1. content: Como texto normal (markdown)
    2. checklist: Como componente interactivo (checkboxes, progress)
    3. citations: Como enlaces clickeables
    4. metadata: Para analytics y debugging

    VENTAJA SOBRE RESPUESTA SIMPLE DE TEXTO:
    - UI más rica y útil
    - Tracking de progreso del usuario
    - Trazabilidad a fuentes
    - Metadata para mejorar el sistema
    """
    message_id: str = Field(
        description="ID único de este mensaje (para tracking)"
    )
    role: str = Field(
        default="assistant",
        description="Rol del mensaje ('user' o 'assistant')"
    )
    content: str = Field(
        description=(
            "Respuesta en texto del agente. "
            "El frontend puede renderizarlo con markdown."
        )
    )

    # Structured data para renderizado rico
    checklist: Optional[Checklist] = Field(
        default=None,
        description=(
            "Checklist estructurado si el usuario pidió pasos. "
            "El frontend lo renderiza como componente interactivo."
        )
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description=(
            "Lista de citas a documentos fuente con enlaces. "
            "El frontend las renderiza como enlaces clickeables."
        )
    )

    # Metadata para analytics y debugging
    retrieval_method: Optional[str] = Field(
        default=None,
        description="Método de RAG usado: 'vector_rag' o 'agent_rag'"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score de confianza de la respuesta (0.0 a 1.0)"
    )
    processing_time_ms: Optional[int] = Field(
        default=None,
        description="Tiempo de procesamiento en milisegundos"
    )
    chunks_used: int = Field(
        default=0,
        description="Número de chunks de documentos usados para la respuesta"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp UTC de cuando se generó la respuesta"
    )


# ============================================================================
# Health Check Models
# ============================================================================

class HealthResponse(BaseModel):
    """Response para el endpoint de health check"""
    status: str = Field(description="Estado del servicio: 'healthy' o 'unhealthy'")
    version: str = Field(description="Versión de la API")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
