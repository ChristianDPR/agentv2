"""
Router Tool - Deriva reclamos a departamentos según reglas de negocio

Esta tool es parte del Prototipo 2 (Agente Reclamos) del curso COE-IA-TRAINING.
Aplica reglas determinísticas de routing basadas en la clasificación del reclamo.

PEDAGOGÍA:
- Demuestra lógica de negocio SIN LLM (reglas puras)
- Matriz de routing configurable
- Reglas de escalamiento automático
- Separación clara: LLM clasifica, reglas rutean
"""

from typing import Any, Dict, Optional

from src.tools.checklist_tool import Tool, ToolDefinition
from src.agents.reclamos.config import (
    ROUTING_MATRIX,
    ESCALATION_RULES,
    DEPARTMENTS,
    PRIORITY_LEVELS
)


class RouterTool(Tool):
    """
    Determina el departamento destino para un reclamo.

    CASO DE USO AFP:
    - Recibe categoría y prioridad del ClassifierTool
    - Aplica matriz de routing predefinida
    - Evalúa reglas de escalamiento
    - Retorna departamento, cola y flags de escalamiento

    PEDAGOGÍA:
    - NO usa LLM - son reglas de negocio determinísticas
    - La matriz de routing viene de config.py (fácil de cambiar)
    - Las reglas de escalamiento son evaluadas en orden
    - Esto es deliberado: separar "entender" (LLM) de "decidir" (reglas)

    ¿Por qué no usar LLM para routing?
    1. Las reglas de routing son políticas de negocio exactas
    2. No queremos variabilidad en decisiones de compliance
    3. Es más rápido y barato
    4. Es auditable y predecible
    """

    def __init__(self, routing_matrix: Optional[Dict] = None):
        """
        Inicializa el RouterTool.

        Args:
            routing_matrix: Matriz de routing personalizada (opcional).
                           Si no se proporciona, usa la de config.py

        PEDAGOGÍA:
        - Permite override de la matriz para testing
        - Facilita diferentes configuraciones por ambiente
        """
        self.routing_matrix = routing_matrix or ROUTING_MATRIX

    @property
    def definition(self) -> ToolDefinition:
        """
        Define la tool para el sistema.
        """
        return ToolDefinition(
            name="route_claim",
            description=(
                "Determina el departamento y cola destino para un reclamo "
                "basado en su categoría y prioridad."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Categoría del reclamo clasificado"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Prioridad asignada (critical, high, normal, low)"
                    },
                    "channel": {
                        "type": "string",
                        "description": "Canal de origen del reclamo",
                        "default": "web"
                    }
                },
                "required": ["category", "priority"]
            }
        )

    async def execute(
        self,
        category: str,
        priority: str,
        channel: str = "web"
    ) -> Dict[str, Any]:
        """
        Determina el routing para un reclamo.

        Args:
            category: Categoría del reclamo (de ClassifierTool)
            priority: Prioridad asignada (de ClassifierTool)
            channel: Canal de origen

        Returns:
            Dict con:
                - department: Departamento destino
                - queue: Cola específica dentro del departamento
                - escalated: Si requiere escalamiento
                - escalation_reason: Razón del escalamiento (si aplica)
                - routing_rule: Regla aplicada (para auditoría)

        PEDAGOGÍA:
        - El método es async para consistencia con otras tools
        - Pero la lógica es síncrona (no hay I/O)
        """
        # Obtener routing base de la matriz
        base_routing = self._get_base_routing(category)

        # Aplicar reglas de escalamiento
        final_routing = self._apply_escalation_rules(
            base_routing=base_routing,
            category=category,
            priority=priority,
            channel=channel
        )

        return final_routing

    def _get_base_routing(self, category: str) -> Dict[str, Any]:
        """
        Obtiene el routing base de la matriz de configuración.

        PEDAGOGÍA:
        - Lookup simple en diccionario
        - Fallback a servicio_cliente si categoría no existe
        """
        # Normalizar categoría
        category = category.lower()

        # Buscar en matriz
        if category in self.routing_matrix:
            routing_config = self.routing_matrix[category]
            return {
                "department": routing_config["department"],
                "queue": routing_config["queue"],
                "backup_department": routing_config.get("backup_department"),
                "requires_verification": routing_config.get(
                    "requires_verification", False
                ),
                "escalated": False,
                "escalation_reason": None,
                "routing_rule": f"matrix:{category}"
            }
        else:
            # Fallback
            return {
                "department": "servicio_cliente",
                "queue": "general",
                "backup_department": None,
                "requires_verification": False,
                "escalated": False,
                "escalation_reason": None,
                "routing_rule": "fallback:unknown_category"
            }

    def _apply_escalation_rules(
        self,
        base_routing: Dict[str, Any],
        category: str,
        priority: str,
        channel: str
    ) -> Dict[str, Any]:
        """
        Aplica reglas de escalamiento sobre el routing base.

        PEDAGOGÍA:
        - Las reglas se evalúan en orden de prioridad
        - Múltiples reglas pueden aplicar
        - Cada regla puede modificar el routing
        """
        routing = base_routing.copy()
        applied_rules = []

        # Regla 1: Prioridad crítica → escalamiento automático
        if priority == "critical":
            routing["escalated"] = True
            routing["queue"] = f"{routing['queue']}_supervisor"
            routing["escalation_reason"] = "Prioridad crítica requiere supervisor"
            applied_rules.append("priority_critical")

        # Regla 2: Legal con prioridad alta o crítica → gerencia legal
        if category == "legal" and priority in ["critical", "high"]:
            routing["department"] = "legal"
            routing["queue"] = "gerencia_legal"
            routing["escalated"] = True
            existing_reason = routing.get("escalation_reason") or ""
            routing["escalation_reason"] = (
                existing_reason + " Caso legal escalado a gerencia."
            ).strip()
            applied_rules.append("legal_critical")

        # Regla 3: Fraude → siempre protocolo de seguridad
        if category == "fraude":
            routing["escalated"] = True
            routing["requires_security_protocol"] = True
            routing["additional_notifications"] = ["antifraude", "seguridad"]
            if not routing.get("escalation_reason"):
                routing["escalation_reason"] = "Caso de fraude requiere protocolo de seguridad"
            applied_rules.append("fraude_always")

        # Regla 4: Canal presencial + crítico → atención inmediata
        if channel == "presencial" and priority == "critical":
            routing["immediate_attention"] = True
            routing["notify_supervisor_agencia"] = True
            routing["sla_override_hours"] = 1
            applied_rules.append("presencial_critical")

        # Registrar reglas aplicadas
        routing["applied_rules"] = applied_rules
        if applied_rules:
            routing["routing_rule"] = (
                f"{base_routing['routing_rule']}+{'+'.join(applied_rules)}"
            )

        return routing

    def get_available_departments(self) -> list:
        """
        Retorna lista de departamentos disponibles.

        PEDAGOGÍA:
        - Útil para validación y UI
        """
        return DEPARTMENTS.copy()

    def validate_routing(self, routing: Dict[str, Any]) -> bool:
        """
        Valida que el routing sea correcto.

        PEDAGOGÍA:
        - Verificación de integridad
        - Útil para tests
        """
        required_fields = ["department", "queue"]
        for field in required_fields:
            if field not in routing:
                return False

        if routing["department"] not in DEPARTMENTS:
            return False

        return True
