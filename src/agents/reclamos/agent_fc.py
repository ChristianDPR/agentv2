"""
Agente de Reclamos con Function Calling

VERSIÓN ALTERNATIVA del Agente Reclamos que usa function calling
en lugar de flujo programático fijo.

PEDAGOGÍA - EJERCICIO 5:
Este archivo demuestra cómo el MISMO problema (gestionar reclamos)
puede resolverse con DOS arquitecturas diferentes:

1. agent.py (original): Flujo fijo programático
   - Código decide: clasificar → rutear → auditar
   - Predecible, auditable, compliance-friendly

2. agent_fc.py (este archivo): Function calling
   - LLM decide qué tools usar y en qué orden
   - Flexible, pero menos predecible

PREGUNTA PARA DISCUTIR:
¿Cuál es mejor para gestión de reclamos AFP? ¿Por qué?
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from src.framework.base_agent import BaseAgent, AgentResponse
from src.framework.model_provider import ModelProvider
from src.tools.classifier_tool import ClassifierTool
from src.tools.router_tool import RouterTool
from src.tools.audit_tool import AuditTool
from src.tools.finish_tool import FinishTool
from src.agents.reclamos.config import RESPONSE_TEMPLATES


# Constantes para el loop
MAX_ITERATIONS = 10
SYSTEM_PROMPT = """Eres un agente de gestión de reclamos de AFP Integra.

Tu trabajo es procesar reclamos de clientes siguiendo estos pasos:
1. CLASIFICAR el reclamo (categoría, prioridad, SLA)
2. RUTEAR a la cola correcta según la clasificación
3. AUDITAR la decisión para compliance
4. TERMINAR con un resumen para el cliente

IMPORTANTE:
- SIEMPRE debes clasificar primero
- SIEMPRE debes rutear después de clasificar
- SIEMPRE debes auditar antes de terminar
- Usa finish() cuando tengas toda la información

Tienes acceso a las siguientes herramientas:
- classify_claim: Clasifica el reclamo por categoría y prioridad
- route_claim: Determina el departamento destino
- audit_log: Registra la decisión para auditoría
- finish: Termina y genera respuesta al cliente
"""


class AgenteReclamosFunctionCalling(BaseAgent):
    """
    Versión del Agente Reclamos que usa function calling.

    DIFERENCIAS CON agent.py (flujo fijo):

    | Aspecto          | Flujo Fijo           | Function Calling      |
    |------------------|----------------------|-----------------------|
    | Quién decide     | Código Python        | LLM                   |
    | Orden garantizado| Sí, siempre igual    | No, LLM puede variar  |
    | Auditoría        | 100% garantizada     | Depende del LLM       |
    | Debugging        | Fácil, predecible    | Más complejo          |
    | Flexibilidad     | Baja                 | Alta                  |

    PEDAGOGÍA:
    - Compara este archivo con agent.py
    - ¿Cuáles son los trade-offs?
    - ¿Para qué casos usarías cada uno?
    """

    def __init__(
        self,
        model_provider: ModelProvider,
        classifier_tool: ClassifierTool,
        router_tool: RouterTool,
        audit_tool: AuditTool,
        finish_tool: Optional[FinishTool] = None
    ):
        """
        Inicializa el Agente con function calling.

        NOTA: A diferencia de agent.py, aquí necesitamos FinishTool
        para que el LLM pueda señalar cuándo terminar.
        """
        super().__init__(
            name="AgenteReclamosFunctionCalling",
            description="Gestiona reclamos AFP usando function calling"
        )

        self.model_provider = model_provider

        # Tools como atributos (register_tools las detecta automáticamente)
        self.classifier_tool = classifier_tool
        self.router_tool = router_tool
        self.audit_tool = audit_tool
        self.finish_tool = finish_tool or FinishTool()

        # CRÍTICO: Registrar tools para function calling
        # Esta línea es la diferencia clave con agent.py
        self.model_provider.register_tools(self)

        self.max_iterations = MAX_ITERATIONS

    async def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Procesa un reclamo usando function calling.

        FLUJO:
        1. Construir prompt con system + query
        2. Loop: LLM decide → ejecutar tool → observar
        3. Terminar cuando LLM use finish()

        PEDAGOGÍA:
        - Observa cómo el loop es genérico
        - El LLM decide el flujo, no el código
        - ¿Qué pasa si el LLM no clasifica primero?
        """
        context = context or {}
        claim_id = context.get("claim_id", self._generate_claim_id())
        channel = context.get("channel", "web")

        # Historial de acciones (para debugging y el prompt)
        observations: List[Dict[str, Any]] = []

        start_time = datetime.utcnow()

        for iteration in range(self.max_iterations):
            # Construir prompt con historial
            prompt = self._build_prompt(query, observations, claim_id, channel)

            # Llamar al LLM (puede retornar texto o tool call)
            result = await self.model_provider.generate(
                prompt=prompt,
                temperature=0.3,  # Baja para consistencia
                max_tokens=2000
            )

            # Si retorna string, el LLM respondió sin usar tool
            if isinstance(result, str):
                # Edge case: respuesta directa sin tools
                if observations:
                    # Extraer datos de las observaciones aunque no haya finish
                    classification = self._extract_classification(observations)
                    routing = self._extract_routing(observations)

                    return AgentResponse(
                        content=result if result.strip() else self._generate_fallback_content(
                            claim_id, classification, routing
                        ),
                        metadata={
                            "claim_id": claim_id,
                            "classification": classification,
                            "routing": routing,
                            "observations": observations,
                            "iterations": iteration + 1,
                            "mode": "function_calling",
                            "warning": "LLM respondió sin usar finish()"
                        }
                    )
                continue

            # Guardar observación
            observations.append({
                "step": iteration + 1,
                "tool": result["tool_name"],
                "input": result["arguments"],
                "output": result["result"]
            })

            # ¿Terminó con finish?
            if result["tool_name"] == "finish":
                processing_time_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )

                # Extraer datos de las observaciones
                classification = self._extract_classification(observations)
                routing = self._extract_routing(observations)

                return AgentResponse(
                    content=result["result"]["summary"],
                    metadata={
                        "claim_id": claim_id,
                        "classification": classification,
                        "routing": routing,
                        "observations": observations,
                        "iterations": iteration + 1,
                        "processing_time_ms": processing_time_ms,
                        "mode": "function_calling"
                    }
                )

        # Max iterations alcanzado
        return self._fallback_response(claim_id, observations)

    def _build_prompt(
        self,
        query: str,
        observations: List[Dict[str, Any]],
        claim_id: str,
        channel: str
    ) -> str:
        """Construye el prompt con system, query y historial."""

        # Formatear historial
        history_text = ""
        if observations:
            history_text = "\n\nACCIONES REALIZADAS:\n"
            for obs in observations:
                output_str = str(obs["output"])
                if len(output_str) > 300:
                    output_str = output_str[:300] + "..."
                history_text += f"""
Paso {obs['step']}:
- Tool: {obs['tool']}
- Input: {obs['input']}
- Resultado: {output_str}
"""

        return f"""{SYSTEM_PROMPT}

CONTEXTO:
- ID del reclamo: {claim_id}
- Canal: {channel}

RECLAMO DEL CLIENTE:
"{query}"
{history_text}

Ejecuta el siguiente paso necesario usando una de las tools disponibles.
Si ya tienes clasificación, routing y auditoría, usa finish() para terminar.
"""

    def _generate_claim_id(self) -> str:
        """Genera ID único para el reclamo."""
        year = datetime.utcnow().year
        unique_part = uuid.uuid4().hex[:5].upper()
        return f"CLM-{year}-{unique_part}"

    def _extract_classification(
        self,
        observations: List[Dict[str, Any]]
    ) -> Optional[Dict]:
        """Extrae clasificación de las observaciones."""
        for obs in observations:
            if obs["tool"] == "classify_claim":
                return obs["output"]
        return None

    def _extract_routing(
        self,
        observations: List[Dict[str, Any]]
    ) -> Optional[Dict]:
        """Extrae routing de las observaciones."""
        for obs in observations:
            if obs["tool"] == "route_claim":
                return obs["output"]
        return None

    def _generate_fallback_content(
        self,
        claim_id: str,
        classification: Optional[Dict],
        routing: Optional[Dict]
    ) -> str:
        """Genera contenido de respuesta cuando el LLM no usa finish()."""
        category = classification.get("category", "general") if classification else "general"
        priority = classification.get("priority", "normal") if classification else "normal"
        sla_hours = classification.get("sla_hours", 48) if classification else 48
        department = routing.get("department", "atención al cliente") if routing else "atención al cliente"

        return (
            f"Su reclamo ha sido registrado con el número {claim_id}. "
            f"Ha sido clasificado como '{category}' con prioridad '{priority}' "
            f"y derivado al departamento de {department.replace('_', ' ')}. "
            f"Será atendido en un plazo máximo de {sla_hours} horas."
        )

    def _fallback_response(
        self,
        claim_id: str,
        observations: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Respuesta cuando se alcanza max_iterations."""
        classification = self._extract_classification(observations)
        routing = self._extract_routing(observations)

        return AgentResponse(
            content=self._generate_fallback_content(claim_id, classification, routing),
            metadata={
                "claim_id": claim_id,
                "classification": classification,
                "routing": routing,
                "observations": observations,
                "error": "max_iterations_reached",
                "mode": "function_calling"
            }
        )


# ============================================================================
# Factory Function
# ============================================================================

def create_agente_reclamos_fc(model_provider: ModelProvider) -> AgenteReclamosFunctionCalling:
    """
    Factory para crear el agente con function calling.

    Uso:
        provider = VertexAIProvider(project_id="...")
        agente = create_agente_reclamos_fc(provider)
        resultado = await agente.run("Me cobraron de más...")
    """
    classifier_tool = ClassifierTool(model_provider=model_provider)
    router_tool = RouterTool()
    audit_tool = AuditTool()
    finish_tool = FinishTool()

    return AgenteReclamosFunctionCalling(
        model_provider=model_provider,
        classifier_tool=classifier_tool,
        router_tool=router_tool,
        audit_tool=audit_tool,
        finish_tool=finish_tool
    )
