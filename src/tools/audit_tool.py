"""
Audit Tool - Registra decisiones del agente para trazabilidad

Esta tool es parte del Prototipo 2 (Agente Reclamos) del curso COE-IA-TRAINING.
Genera logs estructurados en JSON para auditoría y compliance.

PEDAGOGÍA:
- Demuestra la importancia de la trazabilidad en agentes de IA
- Logs estructurados (JSON) vs texto plano
- Información necesaria para auditoría: quién, qué, cuándo, por qué
- Separación de concerns: el agente decide, la tool registra
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import uuid
import json
import structlog

from src.tools.checklist_tool import Tool, ToolDefinition


# Configurar logger estructurado
logger = structlog.get_logger("audit")


class AuditTool(Tool):
    """
    Registra todas las decisiones del agente en formato auditable.

    CASO DE USO AFP:
    - Compliance: toda decisión de IA debe ser trazable
    - Debugging: entender por qué el agente tomó una decisión
    - Métricas: analizar patrones de clasificación y routing
    - Legal: evidencia de cómo se procesó cada reclamo

    PEDAGOGÍA:
    - Los agentes de IA en producción DEBEN ser auditables
    - El log incluye: qué se decidió, por qué, cuándo, quién
    - Formato JSON para fácil parseo y análisis
    - Separado del agente: Single Responsibility Principle
    """

    def __init__(
        self,
        log_to_file: bool = False,
        log_file_path: Optional[str] = None
    ):
        """
        Inicializa el AuditTool.

        Args:
            log_to_file: Si True, también escribe a archivo
            log_file_path: Ruta del archivo de log (si log_to_file=True)

        PEDAGOGÍA:
        - Por defecto solo usa structlog (stdout)
        - Opcionalmente puede persistir a archivo
        - En producción: enviar a sistema de logging centralizado
        """
        self.log_to_file = log_to_file
        self.log_file_path = log_file_path or "logs/audit.jsonl"

    @property
    def definition(self) -> ToolDefinition:
        """
        Define la tool para el sistema.
        """
        return ToolDefinition(
            name="audit_log",
            description=(
                "Registra una acción o decisión del agente para auditoría. "
                "Debe llamarse después de cada decisión importante."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Tipo de acción (classify_and_route, etc.)"
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "ID de la entidad afectada (claim_id, etc.)"
                    },
                    "decision": {
                        "type": "object",
                        "description": "Diccionario con las decisiones tomadas"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Metadatos adicionales (opcional)"
                    }
                },
                "required": ["action", "entity_id", "decision"]
            }
        )

    async def execute(
        self,
        action: str,
        entity_id: str,
        decision: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Registra una decisión del agente.

        Args:
            action: Tipo de acción realizada
            entity_id: ID de la entidad (reclamo, usuario, etc.)
            decision: Diccionario con las decisiones tomadas
            metadata: Información adicional opcional

        Returns:
            Dict con el log entry creado:
                - trace_id: UUID único para este log
                - timestamp: Momento del registro
                - logged: True si se registró correctamente

        PEDAGOGÍA:
        - Genera trace_id único para correlacionar logs
        - Timestamp en UTC para consistencia
        - Retorna el log entry para incluir en response
        """
        # Generar identificadores
        trace_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        # Construir entry de auditoría
        audit_entry = {
            "trace_id": trace_id,
            "timestamp": timestamp,
            "action": action,
            "entity_id": entity_id,
            "entity_type": self._infer_entity_type(entity_id),
            "actor": {
                "type": "agent",
                "agent_name": "AgenteReclamos",
                "agent_version": metadata.get("agent_version", "1.0.0") if metadata else "1.0.0"
            },
            "decision": self._sanitize_decision(decision),
            "metadata": metadata or {}
        }

        # Registrar en structlog
        self._log_entry(audit_entry)

        # Opcionalmente escribir a archivo
        if self.log_to_file:
            self._write_to_file(audit_entry)

        # Retornar resumen para incluir en response
        return {
            "trace_id": trace_id,
            "timestamp": timestamp,
            "logged": True,
            "action": action,
            "entity_id": entity_id
        }

    def _infer_entity_type(self, entity_id: str) -> str:
        """
        Infiere el tipo de entidad basado en el ID.

        PEDAGOGÍA:
        - Convención de naming: CLM-* = claim, USR-* = user, etc.
        - Útil para filtrar logs por tipo de entidad
        """
        if entity_id.startswith("CLM"):
            return "claim"
        elif entity_id.startswith("USR"):
            return "user"
        elif entity_id.startswith("TRX"):
            return "transaction"
        else:
            return "unknown"

    def _sanitize_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitiza la decisión antes de loggear.

        PEDAGOGÍA:
        - Remover datos sensibles (PII, tokens, etc.)
        - Truncar campos muy largos
        - Asegurar que sea serializable a JSON
        """
        sanitized = {}

        for key, value in decision.items():
            # Saltar campos sensibles
            if key in ["password", "token", "secret", "credit_card"]:
                sanitized[key] = "[REDACTED]"
                continue

            # Truncar strings muy largos
            if isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "...[TRUNCATED]"
                continue

            # Recursivamente sanitizar dicts anidados
            if isinstance(value, dict):
                sanitized[key] = self._sanitize_decision(value)
                continue

            # Asegurar que sea serializable
            try:
                json.dumps(value)
                sanitized[key] = value
            except (TypeError, ValueError):
                sanitized[key] = str(value)

        return sanitized

    def _log_entry(self, entry: Dict[str, Any]) -> None:
        """
        Registra el entry usando structlog.

        PEDAGOGÍA:
        - structlog produce JSON estructurado automáticamente
        - Incluye contexto (trace_id) para correlación
        - Nivel INFO para decisiones normales
        """
        logger.info(
            "audit_event",
            trace_id=entry["trace_id"],
            action=entry["action"],
            entity_id=entry["entity_id"],
            entity_type=entry["entity_type"],
            decision_summary=self._summarize_decision(entry["decision"])
        )

    def _summarize_decision(self, decision: Dict[str, Any]) -> str:
        """
        Genera un resumen corto de la decisión para el log.
        """
        parts = []

        if "classification" in decision:
            cls = decision["classification"]
            parts.append(
                f"classified:{cls.get('category', '?')}/{cls.get('priority', '?')}"
            )

        if "routing" in decision:
            rt = decision["routing"]
            parts.append(f"routed:{rt.get('department', '?')}")
            if rt.get("escalated"):
                parts.append("escalated:true")

        return " ".join(parts) if parts else "decision_logged"

    def _write_to_file(self, entry: Dict[str, Any]) -> None:
        """
        Escribe el entry a un archivo JSONL.

        PEDAGOGÍA:
        - JSONL = un JSON por línea, fácil de parsear
        - Append mode para no perder logs anteriores
        - En producción: usar sistema de logging distribuido
        """
        try:
            with open(self.log_file_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(
                "audit_file_write_failed",
                error=str(e),
                trace_id=entry.get("trace_id")
            )

    async def query_logs(
        self,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """
        Consulta logs de auditoría (si están en archivo).

        PEDAGOGÍA:
        - Útil para debugging y análisis
        - En producción: usar Elasticsearch, CloudWatch, etc.

        Args:
            entity_id: Filtrar por ID de entidad
            action: Filtrar por tipo de acción
            limit: Máximo de resultados

        Returns:
            Lista de entries que coinciden con los filtros
        """
        if not self.log_to_file:
            return []

        results = []
        try:
            with open(self.log_file_path, "r") as f:
                for line in f:
                    if len(results) >= limit:
                        break

                    entry = json.loads(line.strip())

                    # Aplicar filtros
                    if entity_id and entry.get("entity_id") != entity_id:
                        continue
                    if action and entry.get("action") != action:
                        continue

                    results.append(entry)

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error("audit_query_failed", error=str(e))

        return results
