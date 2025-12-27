"""
Checklist Tool - Genera checklists estructurados de procedimientos AFP

Esta tool es parte del Prototipo 1 (Agente Asistente) del curso COE-IA-TRAINING.
Convierte texto de procedimientos en checklists accionables con formato JSON.

PEDAGOGÍA:
- Demuestra structured generation con LLMs
- Muestra el uso de temperatura baja para consistencia
- Enseña parsing robusto de JSON
- Ilustra el patrón Tool reutilizable
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel
import json
import re


# ============================================================================
# Clases Base Reutilizables
# ============================================================================

class ToolDefinition(BaseModel):
    """
    Define una tool para el LLM.

    Esta clase se usa para describir la tool al modelo de lenguaje,
    siguiendo el formato JSON Schema para los parámetros.

    PEDAGOGÍA:
    - name: Identificador único de la tool
    - description: El LLM usa esto para decidir cuándo llamar la tool
    - parameters: JSON Schema que valida los argumentos
    """
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema


class Tool(ABC):
    """
    Clase base abstracta para todas las tools del framework.

    PEDAGOGÍA:
    - Esta clase define el contrato que todas las tools deben cumplir
    - Separa la definición (para el LLM) de la ejecución (la lógica)
    - Es reutilizada por todas las tools del curso (Retrieval, Classifier, etc.)

    Métodos abstractos:
    - definition: Retorna la definición para el LLM
    - execute: Implementa la lógica de la tool
    """

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """
        Definición de la tool para el LLM.

        El LLM usa esta información para decidir:
        1. ¿Cuándo usar esta tool?
        2. ¿Qué parámetros necesita?
        3. ¿Qué tipo de datos espera?
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Ejecuta la lógica de la tool.

        Este método contiene la implementación real de lo que hace la tool.
        Debe ser async para soportar operaciones I/O (DB, API, LLM).
        """
        pass


# ============================================================================
# Checklist Tool Implementation
# ============================================================================

class ChecklistTool(Tool):
    """
    Genera checklists estructurados a partir de procedimientos AFP.

    CASO DE USO AFP:
    Convierte documentos de procedimientos (jubilación, traspasos, etc.)
    en listas de tareas accionables con documentos requeridos y tiempos.

    FLUJO:
    1. Recibe texto del procedimiento
    2. Construye prompt estructurado para el LLM
    3. Solicita JSON en formato específico
    4. Parsea y valida la respuesta
    5. Retorna checklist estructurado

    PEDAGOGÍA:
    - Structured Generation: Pedimos JSON al LLM con formato específico
    - Temperature Baja (0.3): Para outputs consistentes y predecibles
    - Error Handling: Manejo robusto de respuestas no-JSON
    """

    def __init__(self, model_provider):
        """
        Inicializa la Checklist Tool.

        Args:
            model_provider: Instancia de ModelProvider (abstracción vendor-neutral)
                           que puede ser VertexAI, Anthropic, etc.

        PEDAGOGÍA:
        - Inyección de dependencias: La tool no sabe qué LLM usa internamente
        - Esto permite cambiar de Gemini a Claude sin modificar esta clase
        """
        self.model_provider = model_provider

    @property
    def definition(self) -> ToolDefinition:
        """
        Define la tool para el LLM.

        PEDAGOGÍA:
        - La descripción es CRÍTICA: el LLM la lee para decidir usar esta tool
        - Los parámetros siguen JSON Schema estándar
        - required: lista los parámetros obligatorios
        """
        return ToolDefinition(
            name="generate_checklist",
            description=(
                "Genera un checklist de pasos accionables a partir de un procedimiento AFP. "
                "Usa esta tool cuando el usuario necesite una guía paso a paso de cómo "
                "completar un trámite o procedimiento."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "procedure_text": {
                        "type": "string",
                        "description": (
                            "Texto completo del procedimiento AFP que será convertido "
                            "en un checklist estructurado"
                        )
                    }
                },
                "required": ["procedure_text"]
            }
        )

    async def execute(self, procedure_text: str) -> Dict:
        """
        Genera checklist estructurado usando el LLM.

        Args:
            procedure_text: Texto del procedimiento AFP a convertir

        Returns:
            Dict con estructura:
            {
                "title": "Nombre del procedimiento",
                "procedure_code": "PROC-XXX-NNN",
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Descripción clara",
                        "required_documents": ["Doc1", "Doc2"]
                    },
                    ...
                ],
                "estimated_time": "X días hábiles",
                "sla": "X días hasta completar"
            }

        Raises:
            ValueError: Si el LLM no retorna JSON válido

        PEDAGOGÍA:
        - Prompt engineering: Estructura clara con ejemplo de formato esperado
        - Temperature 0.3: Baja para consistencia (vs 0.7-1.0 para creatividad)
        - JSON parsing robusto: Intenta extraer JSON incluso si hay texto extra
        """

        # Construir prompt estructurado
        prompt = self._build_prompt(procedure_text)

        # Llamar al LLM con temperatura baja para consistencia
        # PEDAGOGÍA: Temperature baja = outputs más predecibles y estructurados
        response = await self.model_provider.generate(
            prompt=prompt,
            temperature=0.3,  # Baja para structured generation
            max_tokens=6000   # Aumentado para procedimientos largos y retrieval completo
        )

        # Parsear respuesta JSON
        checklist = self._parse_json_response(response)

        return checklist

    def _build_prompt(self, procedure_text: str) -> str:
        """
        Construye el prompt para el LLM.

        PEDAGOGÍA:
        - Few-shot prompting: Damos ejemplo exacto del formato esperado
        - Instrucciones claras: "SOLO JSON, sin texto adicional"
        - Formato explícito: Mostramos la estructura completa
        """
        return f"""Genera un checklist de pasos accionables a partir del siguiente procedimiento AFP.

Procedimiento:
{procedure_text}

Formato de salida (JSON válido):
{{
  "title": "Título del procedimiento",
  "procedure_code": "PROC-XXX-NNN",
  "steps": [
    {{
      "step_number": 1,
      "action": "Descripción clara y accionable de la tarea",
      "required_documents": ["Documento 1", "Documento 2"]
    }},
    {{
      "step_number": 2,
      "action": "Siguiente paso del procedimiento",
      "required_documents": ["Documento 3"]
    }}
  ],
  "estimated_time": "X días hábiles",
  "sla": "X días hasta completar el proceso"
}}

IMPORTANTE:
- Retorna SOLO el JSON, sin texto adicional antes o después
- Asegúrate de que sea JSON válido (comillas dobles, sin trailing commas)
- Los pasos deben ser claros y accionables
- Incluye todos los documentos mencionados en el procedimiento"""

    def _parse_json_response(self, response: str) -> Dict:
        """
        Parsea la respuesta del LLM extrayendo JSON válido.

        Estrategia simple y robusta:
        1. Si hay ```json, eliminar todo antes (incluyendo eso)
        2. Si hay ``` (cierre), eliminar eso y todo después
        3. Buscar primer { y último }
        4. Parse JSON

        Args:
            response: Texto retornado por el LLM

        Returns:
            Dict con el checklist parseado

        Raises:
            ValueError: Si no se encuentra JSON válido
        """
        cleaned = response.strip()

        # 1. Si hay ```json, eliminar todo antes incluyendo eso
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1]
        elif "```" in cleaned:
            # Por si usa ``` sin la palabra json
            cleaned = cleaned.split("```", 1)[1]

        # 2. Si hay ``` de cierre, eliminar eso y todo después
        if "```" in cleaned:
            cleaned = cleaned.split("```")[0]

        # 3. Extraer JSON (primer { hasta último })
        cleaned = cleaned.strip()
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}')

        if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
            raise ValueError(
                f"No se encontró JSON válido en la respuesta.\n"
                f"Respuesta (primeros 500 chars): {response[:500]}"
            )

        json_str = cleaned[start_idx:end_idx+1]

        # 4. Parse JSON
        try:
            checklist = json.loads(json_str)
            self._validate_checklist(checklist)
            return checklist
        except json.JSONDecodeError as e:
            raise ValueError(
                f"JSON inválido: {e}\n"
                f"JSON extraído (primeros 500 chars): {json_str[:500]}"
            )

    def _validate_checklist(self, checklist: Dict) -> None:
        """
        Valida que el checklist tenga la estructura esperada.

        PEDAGOGÍA:
        - Defensive programming: Verificar estructura antes de retornar
        - Mensajes de error claros para debugging

        Args:
            checklist: Diccionario a validar

        Raises:
            ValueError: Si falta algún campo requerido
        """
        required_fields = ["title", "steps"]
        missing_fields = [f for f in required_fields if f not in checklist]

        if missing_fields:
            raise ValueError(
                f"Checklist inválido. Faltan campos requeridos: {missing_fields}"
            )

        # Validar que steps sea una lista
        if not isinstance(checklist["steps"], list):
            raise ValueError("Campo 'steps' debe ser una lista")

        # Validar estructura de cada step
        for idx, step in enumerate(checklist["steps"]):
            if not isinstance(step, dict):
                raise ValueError(f"Step {idx} no es un diccionario")

            if "action" not in step:
                raise ValueError(f"Step {idx} no tiene campo 'action'")
