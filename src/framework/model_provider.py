"""
Framework Base: ModelProvider

PEDAGOGÍA:
- Abstracción vendor-neutral para LLMs
- Soporta tanto generación de texto como embeddings
- Fácil de extender a otros providers (Claude, GPT, etc.)

Mantenemos esto SIMPLE:
- Una interfaz clara
- Implementación concreta para Vertex AI (Gemini)
- Código fácil de leer y entender
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import os


class ModelProvider(ABC):
    """
    Interfaz abstracta para providers de modelos (LLMs).

    PEDAGOGÍA:
    - Define el contrato para cualquier provider
    - Permite cambiar de Gemini a Claude sin cambiar el resto del código
    - Dos métodos principales: generate (texto) y embed (vectores)
    - Soporta function calling: registra tools y el LLM decide cuáles usar
    """

    def __init__(self):
        self._registered_tools: Dict[str, Any] = {}  # name -> Tool instance

    def register_tools(self, agent) -> None:
        """
        Registra las tools de un agente para function calling.

        Args:
            agent: Instancia del agente. Se inspeccionan sus atributos
                   buscando instancias de Tool.

        Uso:
            self.model_provider.register_tools(self)
        """
        from src.tools.checklist_tool import Tool

        for attr_name in dir(agent):
            if attr_name.startswith('_'):
                continue
            try:
                attr = getattr(agent, attr_name)
                if isinstance(attr, Tool):
                    tool_def = attr.definition
                    self._registered_tools[tool_def.name] = attr
            except Exception:
                continue

    def get_registered_tools(self) -> Dict[str, Any]:
        """Retorna las tools registradas."""
        return self._registered_tools

    def clear_tools(self) -> None:
        """Limpia las tools registradas."""
        self._registered_tools = {}

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        Genera texto con el LLM.

        Args:
            prompt: Prompt para el modelo
            temperature: Creatividad (0.0 = determinista, 1.0 = creativo)
            max_tokens: Máximo de tokens a generar

        Returns:
            Texto generado por el modelo
        """
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Genera embedding vectorial del texto.

        NOTA: Solo para providers que soporten embeddings.
        En Vertex AI usamos text-embedding-004.

        Args:
            text: Texto a embedear

        Returns:
            Vector de embeddings (768 dimensiones para text-embedding-004)
        """
        pass


class VertexAIProvider(ModelProvider):
    """
    Implementación concreta para Vertex AI (Gemini).

    PEDAGOGÍA:
    - Ejemplo de cómo implementar la interfaz ModelProvider
    - Usa el SDK oficial de Google Cloud
    - Maneja dos modelos: Gemini (generate) y text-embedding-004 (embed)
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        model_name: Optional[str] = None
    ):
        """
        Args:
            project_id: ID del proyecto GCP (lee de env si no se provee)
            location: Región de Vertex AI
            model_name: Modelo de Gemini a usar (lee DEFAULT_LLM_MODEL de env si no se provee)
        """
        super().__init__()  # Inicializa _registered_tools
        self.project_id = project_id or os.getenv("VERTEX_AI_PROJECT")
        self.location = location
        self.model_name = model_name or os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")

        if not self.project_id:
            raise ValueError(
                "project_id es requerido. "
                "Provéelo como parámetro o configura VERTEX_AI_PROJECT en .env"
            )

        # Inicializar Vertex AI
        self._initialize_vertex_ai()

    def _initialize_vertex_ai(self):
        """Inicializa el SDK de Vertex AI"""
        try:
            import vertexai
            vertexai.init(project=self.project_id, location=self.location)
        except ImportError:
            raise ImportError(
                "google-cloud-aiplatform no está instalado. "
                "Ejecuta: pip install google-cloud-aiplatform"
            )

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> Any:
        """
        Genera texto con Gemini.

        Si hay tools registradas y el LLM decide usar una,
        ejecuta la tool y retorna su resultado directamente.

        Returns:
            - str: Si no hay tools o el LLM responde con texto
            - Any: Resultado de tool.execute() si el LLM usa una tool
        """
        try:
            from vertexai.generative_models import (
                GenerativeModel,
                GenerationConfig,
                Tool as GeminiTool,
                FunctionDeclaration
            )

            model = GenerativeModel(self.model_name)
            config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )

            # Si hay tools registradas, usar function calling
            if self._registered_tools:
                gemini_tools = self._build_gemini_tools()
                response = await model.generate_content_async(
                    prompt,
                    generation_config=config,
                    tools=gemini_tools
                )
                return await self._handle_response_with_tools(response)

            # Sin tools: comportamiento original
            response = await model.generate_content_async(
                prompt,
                generation_config=config
            )
            return response.text

        except Exception as e:
            raise RuntimeError(f"Error generando con Gemini: {e}")

    async def _handle_response_with_tools(self, response) -> Any:
        """
        Procesa respuesta de Gemini. Si hay tool_call, ejecuta la tool.

        Returns:
            - str: Si el LLM responde con texto
            - Dict: Si el LLM usa una tool:
                {
                    "tool_name": str,
                    "arguments": Dict,
                    "result": Any (output de tool.execute())
                }
        """
        candidate = response.candidates[0]

        for part in candidate.content.parts:
            # Si el LLM quiere usar una tool, ejecutarla
            if hasattr(part, 'function_call') and part.function_call:
                fc = part.function_call
                tool_name = fc.name
                arguments = dict(fc.args) if fc.args else {}

                # Buscar y ejecutar la tool
                if tool_name in self._registered_tools:
                    tool = self._registered_tools[tool_name]
                    result = await tool.execute(**arguments)
                    return {
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "result": result
                    }
                else:
                    raise ValueError(f"Tool '{tool_name}' no encontrada")

            # Si es texto, retornarlo
            if hasattr(part, 'text') and part.text:
                return part.text

        return ""

    def _build_gemini_tools(self) -> List:
        """Convierte las tools registradas al formato de Gemini."""
        from vertexai.generative_models import Tool as GeminiTool, FunctionDeclaration

        function_declarations = []
        for tool in self._registered_tools.values():
            tool_def = tool.definition
            func_decl = FunctionDeclaration(
                name=tool_def.name,
                description=tool_def.description,
                parameters=tool_def.parameters
            )
            function_declarations.append(func_decl)

        return [GeminiTool(function_declarations=function_declarations)]

    async def embed(self, text: str) -> List[float]:
        """
        Genera embedding con text-embedding-004.

        PEDAGOGÍA:
        - text-embedding-004 retorna vectores de 768 dimensiones
        - Es el embedding recomendado de Google (Dic 2024)
        - Compatible con pgvector
        """
        try:
            from vertexai.language_models import TextEmbeddingModel

            # Cargar modelo de embeddings
            model = TextEmbeddingModel.from_pretrained("text-embedding-004")

            # Generar embedding
            embeddings = model.get_embeddings([text])

            # Retornar el primer (y único) embedding
            return embeddings[0].values

        except Exception as e:
            raise RuntimeError(f"Error generando embedding: {e}")

    def __repr__(self) -> str:
        return f"VertexAIProvider(project={self.project_id}, model={self.model_name})"
