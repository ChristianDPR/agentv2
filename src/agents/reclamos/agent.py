"""
Agente de Gestión de Reclamos AFP

Prototipo 2: Clasifica, prioriza y deriva reclamos automáticamente
con trazabilidad completa para auditoría.

PEDAGOGÍA:
- Demuestra flujo SECUENCIAL de tools (vs paralelo del Prototipo 1)
- Cada tool depende del resultado de la anterior
- Auditoría obligatoria en cada decisión
- Structured output para integración con sistemas AFP
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from src.framework.base_agent import BaseAgent, AgentResponse
from src.framework.model_provider import ModelProvider
from src.tools.classifier_tool import ClassifierTool
from src.tools.router_tool import RouterTool
from src.tools.audit_tool import AuditTool
from src.agents.reclamos.config import (
    SLA_RULES,
    RESPONSE_TEMPLATES,
    DEPARTMENTS
)


class AgenteReclamos(BaseAgent):
    """
    Agente que gestiona reclamos de clientes AFP.

    PEDAGOGÍA:
    - Este es el PROTOTIPO 2 del curso
    - Usa 3 tools en secuencia: Classifier → Router → Audit
    - Flujo: Reclamo → Clasificar → Rutear → Auditar → Respuesta

    Diferencias con Prototipo 1 (Asistente):
    - Flujo secuencial vs paralelo
    - Decisiones de negocio vs búsqueda de información
    - Auditoría obligatoria vs opcional
    """

    def __init__(
        self,
        model_provider: ModelProvider,
        classifier_tool: ClassifierTool,
        router_tool: RouterTool,
        audit_tool: AuditTool
    ):
        """
        Inicializa el Agente de Reclamos.

        Args:
            model_provider: Proveedor de LLM (Vertex AI, etc.)
            classifier_tool: Tool para clasificar reclamos
            router_tool: Tool para determinar routing
            audit_tool: Tool para registrar auditoría

        PEDAGOGÍA:
        - Inyección de dependencias: El agente no sabe qué LLM usa
        - Todas las tools son intercambiables
        - Facilita testing con mocks
        """
        super().__init__(
            name="AgenteReclamos",
            description="Clasifica, prioriza y deriva reclamos AFP con auditoría"
        )

        self.model_provider = model_provider
        self.classifier_tool = classifier_tool
        self.router_tool = router_tool
        self.audit_tool = audit_tool

    async def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Procesa un reclamo de cliente.

        PEDAGOGÍA - Flujo Secuencial:
        1. CLASIFICAR: Determinar categoría, prioridad y SLA
        2. RUTEAR: Determinar departamento destino
        3. AUDITAR: Registrar todas las decisiones
        4. RESPONDER: Generar mensaje para el cliente

        Args:
            query: Texto del reclamo del cliente
            context: Contexto adicional opcional
                - claim_id: ID del reclamo (se genera si no existe)
                - channel: Canal de origen (app, web, presencial, etc.)
                - customer_id: ID del cliente

        Returns:
            AgentResponse con:
                - content: Mensaje para el cliente
                - metadata: classification, routing, audit_log
        """
        # Extraer contexto o usar defaults
        context = context or {}
        claim_id = context.get("claim_id", self._generate_claim_id())
        channel = context.get("channel", "web")
        customer_id = context.get("customer_id", "anonymous")

        # Timestamp de inicio para medir latencia
        start_time = datetime.utcnow()

        # ====================================================================
        # PASO 1: CLASIFICAR EL RECLAMO
        # ====================================================================
        # PEDAGOGÍA: El ClassifierTool usa el LLM para entender el reclamo
        # y asignar categoría, prioridad y SLA.

        classification = await self.classifier_tool.execute(
            claim_text=query,
            channel=channel
        )

        # Validar que la clasificación sea válida
        if not classification or "category" not in classification:
            return self._error_response(
                claim_id=claim_id,
                error="classification_failed",
                message="No se pudo clasificar el reclamo. Por favor, intente de nuevo."
            )

        # ====================================================================
        # PASO 2: DETERMINAR ROUTING
        # ====================================================================
        # PEDAGOGÍA: El RouterTool aplica reglas de negocio determinísticas
        # basadas en la clasificación. No usa LLM, es pura lógica.

        routing = await self.router_tool.execute(
            category=classification["category"],
            priority=classification["priority"],
            channel=channel
        )

        # ====================================================================
        # PASO 3: REGISTRAR AUDITORÍA
        # ====================================================================
        # PEDAGOGÍA: TODA decisión del agente debe quedar registrada.
        # Esto es crítico para compliance y debugging.

        # Calcular tiempo de procesamiento
        processing_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        audit_log = await self.audit_tool.execute(
            action="classify_and_route",
            entity_id=claim_id,
            decision={
                "classification": classification,
                "routing": routing
            },
            metadata={
                "channel": channel,
                "customer_id": customer_id,
                "processing_time_ms": processing_time_ms,
                "agent_version": "1.0.0"
            }
        )

        # ====================================================================
        # PASO 4: GENERAR RESPUESTA
        # ====================================================================
        # PEDAGOGÍA: La respuesta combina información de clasificación
        # y routing en un mensaje amigable para el cliente.

        response_content = self._generate_response(
            claim_id=claim_id,
            classification=classification,
            routing=routing
        )

        # Preparar metadata completa
        metadata = {
            "claim_id": claim_id,
            "classification": classification,
            "routing": routing,
            "audit_log": audit_log,
            "processing_time_ms": processing_time_ms
        }

        return AgentResponse(
            content=response_content,
            metadata=metadata
        )

    def _generate_claim_id(self) -> str:
        """
        Genera un ID único para el reclamo.

        Formato: CLM-YYYY-XXXXX (ej: CLM-2025-00001)
        """
        year = datetime.utcnow().year
        unique_part = uuid.uuid4().hex[:5].upper()
        return f"CLM-{year}-{unique_part}"

    def _generate_response(
        self,
        claim_id: str,
        classification: Dict[str, Any],
        routing: Dict[str, Any]
    ) -> str:
        """
        Genera el mensaje de respuesta para el cliente.

        PEDAGOGÍA:
        - Usa templates predefinidos por prioridad
        - Personaliza con datos de la clasificación
        - Incluye información útil (ID, tiempo estimado, departamento)
        """
        priority = classification["priority"]
        sla_hours = classification["sla_hours"]
        department = routing["department"]

        # Obtener template según prioridad
        template = RESPONSE_TEMPLATES.get(
            priority,
            RESPONSE_TEMPLATES["normal"]
        )

        # Calcular días hábiles (aproximado)
        sla_days = max(1, sla_hours // 24)

        # Formatear nombre del departamento para mostrar
        department_display = department.replace("_", " ").title()

        # Generar mensaje
        message = template.format(
            sla_hours=sla_hours,
            sla_days=sla_days,
            department=department_display
        )

        # Agregar información de tracking
        tracking_info = f"\n\nNúmero de seguimiento: {claim_id}"

        # Agregar nota de escalamiento si aplica
        escalation_note = ""
        if routing.get("escalated"):
            escalation_note = (
                "\n\nNota: Su caso ha sido escalado para atención prioritaria."
            )

        return message + tracking_info + escalation_note

    def _error_response(
        self,
        claim_id: str,
        error: str,
        message: str
    ) -> AgentResponse:
        """
        Genera una respuesta de error estructurada.
        """
        return AgentResponse(
            content=message,
            metadata={
                "claim_id": claim_id,
                "error": error,
                "success": False
            }
        )


# ============================================================================
# Factory Function (para facilitar instanciación)
# ============================================================================

def create_agente_reclamos(model_provider: ModelProvider) -> AgenteReclamos:
    """
    Factory function para crear un AgenteReclamos con todas sus dependencias.

    PEDAGOGÍA:
    - Encapsula la creación de todas las tools
    - Facilita el uso del agente sin conocer las dependencias internas
    - Útil para testing y configuración

    Args:
        model_provider: Proveedor de LLM a usar

    Returns:
        AgenteReclamos configurado y listo para usar
    """
    # Crear tools
    classifier_tool = ClassifierTool(model_provider=model_provider)
    router_tool = RouterTool()
    audit_tool = AuditTool()

    # Crear y retornar agente
    return AgenteReclamos(
        model_provider=model_provider,
        classifier_tool=classifier_tool,
        router_tool=router_tool,
        audit_tool=audit_tool
    )
