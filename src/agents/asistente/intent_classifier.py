"""
Intent Classifier Agent - Decide si una query necesita checklist

PEDAGOGÍA:
- Demuestra uso de agentes para decisiones (no keywords primitivos!)
- Structured output: el LLM retorna JSON estructurado
- Agentes como componentes: este agente es usado por el Agente Asistente
"""

import json
import re
from typing import Dict, Any
from src.framework.model_provider import ModelProvider


class IntentClassifierAgent:
    """
    Agente que clasifica la intención de una query.

    PEDAGOGÍA:
    - Esto es un AGENTE, no una función con keywords
    - Usa el LLM para entender la intención semánticamente
    - Retorna decisión estructurada (JSON)
    - Mucho más robusto que keywords hardcodeados
    """

    def __init__(self, model_provider: ModelProvider):
        """
        Args:
            model_provider: Proveedor de LLM (puede ser fast, no necesita pro)
        """
        self.model_provider = model_provider

    async def classify(self, query: str) -> Dict[str, Any]:
        """
        Clasifica la intención de la query.

        PEDAGOGÍA:
        - El LLM entiende la intención mejor que keywords
        - Retorna JSON estructurado para parseo fácil
        - Incluye reasoning para transparencia

        Args:
            query: Consulta del usuario

        Returns:
            Dict con:
            - needs_checklist: bool
            - reasoning: str (por qué tomó esa decisión)
            - confidence: float (0-1)
        """
        prompt = self._build_classification_prompt(query)

        try:
            response = await self.model_provider.generate(
                prompt=prompt,
                temperature=0.3,  # Baja para decisiones consistentes
                max_tokens=1024
            )

            # Parsear respuesta JSON
            classification = self._parse_json_response(response)

            return classification

        except Exception as e:
            # Fallback conservador: si hay error, no generar checklist
            return {
                "needs_checklist": False,
                "reasoning": f"Error en clasificación: {e}",
                "confidence": 0.0
            }

    def _build_classification_prompt(self, query: str) -> str:
        """
        Construye el prompt para clasificación.

        PEDAGOGÍA:
        - Prompt claro y específico
        - Ejemplos en el prompt (few-shot learning)
        - Pedimos JSON para facilitar parsing
        """
        return f"""Eres un clasificador de intenciones para un asistente de AFP.

QUERY DEL USUARIO:
"{query}"

TAREA:
Determina si esta query requiere un CHECKLIST de pasos accionables.

Un checklist es apropiado cuando:
- Necesita pasos específicos para un trámite
- Pregunta sobre requisitos o documentos necesarios
- Quiere saber el proceso de algo

Un checklist NO es apropiado cuando:
- Solo pregunta por información general
- Busca definiciones o explicaciones
- Pregunta por plazos o tiempos
- Consulta sobre elegibilidad sin pedir el proceso

EJEMPLOS:
"¿Cómo tramitar jubilación anticipada?" → needs_checklist: true
"¿Qué es la jubilación anticipada?" → needs_checklist: false
"¿Cuánto demora un traspaso?" → needs_checklist: false
"¿Qué pasos debo seguir para afiliarme?" → needs_checklist: true

Responde SOLO con un JSON válido en este formato:
{{
  "needs_checklist": true,
  "reasoning": "Explicación breve de por qué",
  "confidence": 0.95
}}

JSON:"""

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parsea la respuesta JSON del LLM.

        PEDAGOGÍA:
        - LLMs a veces agregan texto extra
        - Necesitamos extraer SOLO el JSON válido
        - Manejo robusto de errores
        """
        # Intentar parsear directamente
        try:
            cleaned = response.strip()
            # Remover markdown code blocks si existen
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```json?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)

            return json.loads(cleaned)

        except json.JSONDecodeError:
            pass

        # Intentar extraer JSON con regex
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())

                # Validar estructura mínima
                if "needs_checklist" not in result:
                    result["needs_checklist"] = False
                if "reasoning" not in result:
                    result["reasoning"] = "Estructura de respuesta incompleta"
                if "confidence" not in result:
                    result["confidence"] = 0.5

                return result

            except json.JSONDecodeError:
                pass

        # Fallback: no generar checklist si no podemos parsear
        return {
            "needs_checklist": False,
            "reasoning": "No se pudo parsear la respuesta del LLM",
            "confidence": 0.0
        }

    def __repr__(self) -> str:
        return f"IntentClassifierAgent(model={self.model_provider.model_name})"
