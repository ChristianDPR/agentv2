"""
Agente Genérico - Function Calling Puro

Un agente "shell" que ejecuta cualquier combinación de tools.
El comportamiento depende 100% del system_prompt y tools que reciba.
"""

from typing import Dict, Any, Optional, List
from src.framework.base_agent import BaseAgent, AgentResponse
from src.framework.model_provider import ModelProvider
from src.tools.checklist_tool import Tool


class AgenteGenerico(BaseAgent):

    def __init__(
        self,
        model_provider: ModelProvider,
        system_prompt: str,
        tools: List[Tool]
    ):
        super().__init__(name="AgenteGenerico", description="Agente configurable")

        self.model_provider = model_provider
        self.system_prompt = system_prompt

        # Registrar tools como atributos
        for i, tool in enumerate(tools):
            setattr(self, f"tool_{i}", tool)

        # Habilitar function calling
        self.model_provider.register_tools(self)

    async def run(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        observations = []

        for iteration in range(10):
            prompt = self._build_prompt(query, observations)
            result = await self.model_provider.generate(prompt=prompt)

            # Texto directo = terminar
            if isinstance(result, str):
                return AgentResponse(content=result, metadata={"observations": observations})

            # Tool call = ejecutar y guardar
            observations.append({
                "tool": result["tool_name"],
                "input": result["arguments"],
                "output": result["result"]
            })

            # Finish = terminar
            if result["tool_name"] == "finish":
                return AgentResponse(
                    content=result["result"].get("summary", str(result["result"])),
                    metadata={"observations": observations}
                )

        return AgentResponse(content="Max iterations", metadata={"observations": observations})

    def _build_prompt(self, query: str, observations: list) -> str:
        history = ""
        if observations:
            history = "\n\nHistorial:\n" + "\n".join(
                f"- {obs['tool']}: {str(obs['output'])[:200]}"
                for obs in observations
            )

        return f"{self.system_prompt}\n\nConsulta: {query}{history}"
