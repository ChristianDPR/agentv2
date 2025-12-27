"""
Evaluación de relevancia usando LLM como juez

El LLM evalúa qué tan relevante es un documento para una query.
"""

import json
import re
from typing import Any, Dict

from src.framework.model_provider import ModelProvider


class ChunkEvaluator:
    """
    Usa el LLM para evaluar relevancia de documentos.

    PEDAGOGÍA:
    - "LLM como juez" = enfoque moderno de RAG
    - Ventajas:
      1. Transparencia: el LLM explica POR QUÉ es relevante
      2. No requiere embeddings
      3. Entiende contexto semántico complejo
    - Desventajas:
      1. Más lento (una llamada LLM por documento)
      2. Más caro (más tokens consumidos)
      3. No escala a miles de documentos
    """

    def __init__(self, model_provider: ModelProvider):
        """
        Args:
            model_provider: Proveedor de modelo LLM
        """
        self.model_provider = model_provider

    async def evaluate_relevance(
        self, query: str, document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evalúa qué tan relevante es un documento para una query.

        PEDAGOGÍA:
        - Temperature=0.3 para evaluaciones consistentes
        - Pedimos JSON estructurado para parsear fácilmente
        - El "reasoning" es clave: explica el por qué

        Args:
            query: Consulta del usuario
            document: Documento con content y metadata

        Returns:
            Dict con:
            - document_id: ID del documento
            - relevance_score: Score 0-1
            - reasoning: Explicación del LLM
            - relevant_sections: Secciones importantes
        """
        doc_id = document["id"]
        content = document["content"]
        metadata = document["metadata"]

        # Construir prompt estructurado
        prompt = self._build_evaluation_prompt(query, content, metadata)

        # Llamar al LLM
        try:
            response = await self.model_provider.generate(
                prompt=prompt, temperature=0.3, max_tokens=3000
            )

            # Parsear respuesta JSON
            evaluation = self._parse_json_response(response)

            # Agregar document_id
            evaluation["document_id"] = doc_id

            return evaluation

        except Exception as e:
            # Fallback en caso de error
            return {
                "document_id": doc_id,
                "relevance_score": 0.0,
                "reasoning": f"Error al evaluar: {str(e)}",
                "relevant_sections": [],
            }

    def _build_evaluation_prompt(
        self, query: str, content: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Construye el prompt para evaluación.

        PEDAGOGÍA:
        - Prompt claro y específico
        - Pedimos JSON para facilitar parsing
        - Incluimos metadata para contexto adicional
        """
        return f"""Evalúa la relevancia del siguiente documento para la consulta del usuario.

CONSULTA DEL USUARIO:
{query}

DOCUMENTO:
Categoría: {metadata.get('category', 'general')}
Procedimiento: {metadata.get('procedure_name', 'N/A')}
Código: {metadata.get('procedure_code', 'N/A')}

CONTENIDO:
{content}

INSTRUCCIONES:
1. Evalúa qué tan relevante es este documento para la consulta (score 0-1)
2. Explica brevemente por qué es o no relevante
3. Identifica las secciones más relevantes del documento

Responde SOLO con un JSON válido en este formato:
{{
  "relevance_score": 0.85,
  "reasoning": "Este documento es relevante porque...",
  "relevant_sections": ["REQUISITOS", "PASOS"]
}}

JSON:"""

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parsea la respuesta JSON del LLM de forma robusta.

        PEDAGOGÍA:
        - Los LLMs a veces usan bloques markdown (```json ... ```)
        - Necesitamos limpiar y extraer el JSON válido
        """
        # Limpiar respuesta
        cleaned = response.strip()

        # Limpiar bloques markdown si existen
        if "```" in cleaned:
            cleaned = re.sub(r'^```(?:json|JSON)?\s*\n?', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

        # Intento 1: Parse directo
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Intento 2: Extraer primer objeto JSON válido
        try:
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start:end+1])
        except json.JSONDecodeError:
            pass

        # Fallback: score bajo si no se puede parsear
        return {
            "relevance_score": 0.0,
            "reasoning": "No se pudo parsear la respuesta del LLM",
            "relevant_sections": [],
        }
