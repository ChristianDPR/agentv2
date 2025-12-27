"""
Classifier Tool - Clasifica reclamos de clientes AFP

Esta tool es parte del Prototipo 2 (Agente Reclamos) del curso COE-IA-TRAINING.
Usa el LLM para clasificar reclamos por categoría, prioridad y calcular SLA.

PEDAGOGÍA:
- Demuestra clasificación con LLM (vs reglas hardcoded)
- Structured output con JSON
- Confidence scores para manejo de ambigüedad
- Explicabilidad: el LLM justifica su decisión
"""

from typing import Any, Dict, List
import json

from src.tools.checklist_tool import Tool, ToolDefinition
from src.agents.reclamos.config import (
    CATEGORIES,
    CATEGORY_NAMES,
    PRIORITY_LEVELS,
    SLA_RULES,
    LLM_CONFIG
)


class ClassifierTool(Tool):
    """
    Clasifica reclamos de clientes usando LLM.

    CASO DE USO AFP:
    - Recibe texto de reclamo del cliente
    - Determina categoría (fraude, legal, operaciones, etc.)
    - Asigna prioridad (critical, high, normal, low)
    - Calcula SLA en horas según reglas de negocio
    - Proporciona explicación de la decisión

    FLUJO:
    1. Recibe texto del reclamo
    2. Construye prompt con categorías disponibles
    3. LLM clasifica y justifica
    4. Parsea respuesta JSON
    5. Aplica reglas de SLA
    6. Retorna clasificación completa

    PEDAGOGÍA:
    - LLM para entender lenguaje natural (no keywords)
    - Temperature baja (0.3) para consistencia
    - Confidence score para manejar casos ambiguos
    - Reasoning para explicabilidad y debugging
    """

    def __init__(self, model_provider):
        """
        Inicializa el ClassifierTool.

        Args:
            model_provider: Instancia de ModelProvider para llamar al LLM

        PEDAGOGÍA:
        - Inyección de dependencias del model provider
        - Permite cambiar de Gemini a Claude sin modificar esta clase
        """
        self.model_provider = model_provider
        self.config = LLM_CONFIG.get("classifier", {})

    @property
    def definition(self) -> ToolDefinition:
        """
        Define la tool para el LLM.

        PEDAGOGÍA:
        - Description clara para que el orquestador sepa cuándo usarla
        - Parameters con tipos y descripciones
        """
        return ToolDefinition(
            name="classify_claim",
            description=(
                "Clasifica un reclamo de cliente según categoría, prioridad y SLA. "
                "Usa esta tool cuando necesites determinar cómo procesar un reclamo."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "claim_text": {
                        "type": "string",
                        "description": "Texto del reclamo del cliente"
                    },
                    "channel": {
                        "type": "string",
                        "description": "Canal de origen del reclamo (app, web, presencial, etc.)",
                        "default": "web"
                    }
                },
                "required": ["claim_text"]
            }
        )

    async def execute(
        self,
        claim_text: str,
        channel: str = "web"
    ) -> Dict[str, Any]:
        """
        Clasifica un reclamo de cliente.

        Args:
            claim_text: Texto del reclamo
            channel: Canal de origen (para ajustes de prioridad)

        Returns:
            Dict con:
                - category: Categoría del reclamo
                - priority: Nivel de prioridad
                - sla_hours: Horas para resolver según SLA
                - confidence: Score de confianza (0.0 - 1.0)
                - reasoning: Explicación de la clasificación
                - keywords_detected: Palabras clave encontradas

        PEDAGOGÍA:
        - El LLM hace el trabajo pesado de entender el lenguaje
        - Las reglas de SLA son determinísticas post-clasificación
        - Confidence permite escalar casos ambiguos a humanos
        """
        # Validar input
        if not claim_text or len(claim_text.strip()) < 10:
            return self._default_classification(
                reason="Reclamo muy corto o vacío"
            )

        # Construir prompt
        prompt = self._build_classification_prompt(claim_text)

        # Llamar al LLM
        response = await self.model_provider.generate(
            prompt=prompt,
            temperature=self.config.get("temperature", 0.3),
            max_tokens=self.config.get("max_tokens", 1000)
        )

        # Parsear respuesta
        classification = self._parse_classification_response(response)

        # Aplicar reglas de SLA
        classification = self._apply_sla_rules(classification)

        # Ajustar por canal si es necesario
        classification = self._adjust_for_channel(classification, channel)

        return classification

    def _build_classification_prompt(self, claim_text: str) -> str:
        """
        Construye el prompt para clasificación.

        PEDAGOGÍA:
        - Lista todas las categorías disponibles con descripciones
        - Solicita JSON estructurado
        - Pide justificación para explicabilidad
        """
        # Construir lista de categorías con descripciones
        categories_text = "\n".join([
            f"- {key}: {cat['description']}"
            for key, cat in CATEGORIES.items()
        ])

        return f"""Eres un clasificador de reclamos de AFP Integra.
Tu tarea es analizar el siguiente reclamo y clasificarlo.

RECLAMO DEL CLIENTE:
"{claim_text}"

CATEGORÍAS DISPONIBLES:
{categories_text}

NIVELES DE PRIORIDAD:
- critical: Emergencias, fraude, riesgo financiero inmediato
- high: Temas legales, pérdida de dinero potencial
- normal: Operaciones estándar, consultas de información
- low: Consultas generales, quejas menores

INSTRUCCIONES:
1. Analiza el reclamo cuidadosamente
2. Determina la categoría más apropiada
3. Asigna una prioridad basada en la urgencia y gravedad
4. Identifica palabras clave relevantes
5. Explica brevemente tu razonamiento

Responde SOLO con el siguiente JSON (sin texto adicional):
{{
    "category": "categoria_seleccionada",
    "priority": "nivel_de_prioridad",
    "confidence": 0.85,
    "reasoning": "Explicación breve de por qué elegiste esta categoría y prioridad",
    "keywords_detected": ["palabra1", "palabra2"]
}}

IMPORTANTE:
- category debe ser una de: {', '.join(CATEGORY_NAMES)}
- priority debe ser una de: critical, high, normal, low
- confidence es un número entre 0.0 y 1.0
- Si no estás seguro, usa confidence bajo y categoría "atencion"
"""

    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM extrayendo el JSON.

        PEDAGOGÍA:
        - Manejo robusto de respuestas malformadas
        - Fallback a clasificación default si falla
        """
        try:
            # Limpiar respuesta
            cleaned = response.strip()

            # Remover markdown si existe
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1]
            if "```" in cleaned:
                cleaned = cleaned.split("```")[0]

            # Extraer JSON
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}')

            if start_idx == -1 or end_idx == -1:
                return self._default_classification(
                    reason="No se encontró JSON en respuesta del LLM"
                )

            json_str = cleaned[start_idx:end_idx + 1]
            classification = json.loads(json_str)

            # Validar campos requeridos
            classification = self._validate_classification(classification)

            return classification

        except json.JSONDecodeError as e:
            return self._default_classification(
                reason=f"Error parseando JSON: {e}"
            )
        except Exception as e:
            return self._default_classification(
                reason=f"Error inesperado: {e}"
            )

    def _validate_classification(self, classification: Dict) -> Dict:
        """
        Valida y normaliza la clasificación.

        PEDAGOGÍA:
        - Asegura que category y priority sean valores válidos
        - Aplica defaults si faltan campos
        """
        # Validar category
        category = classification.get("category", "atencion").lower()
        if category not in CATEGORY_NAMES:
            category = "atencion"

        # Validar priority
        priority = classification.get("priority", "normal").lower()
        if priority not in PRIORITY_LEVELS:
            priority = "normal"

        # Validar confidence
        confidence = classification.get("confidence", 0.5)
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.5

        return {
            "category": category,
            "priority": priority,
            "confidence": confidence,
            "reasoning": classification.get("reasoning", "Sin explicación"),
            "keywords_detected": classification.get("keywords_detected", [])
        }

    def _apply_sla_rules(self, classification: Dict) -> Dict:
        """
        Aplica reglas de SLA basadas en la prioridad.

        PEDAGOGÍA:
        - Las reglas de SLA son determinísticas (no LLM)
        - Separar decisión (LLM) de política (reglas de negocio)
        """
        priority = classification["priority"]
        sla_config = SLA_RULES.get(priority, SLA_RULES["normal"])

        classification["sla_hours"] = sla_config["hours"]
        classification["sla_description"] = sla_config["description"]
        classification["requires_escalation"] = sla_config.get(
            "requires_escalation", False
        )

        return classification

    def _adjust_for_channel(
        self,
        classification: Dict,
        channel: str
    ) -> Dict:
        """
        Ajusta la clasificación según el canal de origen.

        PEDAGOGÍA:
        - El canal puede afectar la prioridad
        - Reclamos presenciales con prioridad alta → más urgentes
        """
        # Si es presencial y ya es high o critical, mantener
        # Si es presencial y es normal con confidence alto, subir a high
        if channel == "presencial":
            if (classification["priority"] == "normal" and
                classification["confidence"] >= 0.8):
                # Opcionalmente podríamos subir la prioridad
                # Por ahora solo lo marcamos
                classification["channel_adjustment"] = "presencial_boost_candidate"

        classification["channel"] = channel
        return classification

    def _default_classification(self, reason: str = "") -> Dict[str, Any]:
        """
        Retorna una clasificación por defecto cuando algo falla.

        PEDAGOGÍA:
        - Fail-safe: nunca dejar un reclamo sin clasificar
        - Usar categoría genérica con prioridad normal
        - Registrar razón del fallback para debugging
        """
        sla_config = SLA_RULES["normal"]

        return {
            "category": "atencion",
            "priority": "normal",
            "confidence": 0.0,
            "reasoning": f"Clasificación por defecto. {reason}",
            "keywords_detected": [],
            "sla_hours": sla_config["hours"],
            "sla_description": sla_config["description"],
            "requires_escalation": False,
            "fallback": True,
            "fallback_reason": reason
        }
