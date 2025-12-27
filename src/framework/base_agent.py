"""
Framework Base: BaseAgent

PEDAGOGÍA:
- Clase abstracta base para todos los agentes
- Define el contrato que todos los agentes deben cumplir
- Usa ABC (Abstract Base Class) para forzar implementación de run()

Mantenemos esto SIMPLE para que los participantes entiendan:
- Qué es un agente
- Cómo heredar de una clase base
- Por qué usamos abstracto
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class AgentResponse(BaseModel):
    """
    Respuesta estandarizada de un agente.

    PEDAGOGÍA: Usamos Pydantic para validación automática de tipos.
    """
    content: str
    metadata: Dict[str, Any] = {}

    class Config:
        """Permitir tipos arbitrarios en metadata"""
        arbitrary_types_allowed = True


class BaseAgent(ABC):
    """
    Clase base abstracta para todos los agentes.

    PEDAGOGÍA:
    - Todos los agentes heredan de esta clase
    - Deben implementar el método run()
    - Pueden tener un nombre y configuración propia

    Ejemplo de uso:
        class MiAgente(BaseAgent):
            async def run(self, query: str, **kwargs) -> AgentResponse:
                # Implementación específica
                return AgentResponse(content="...")
    """

    def __init__(self, name: str, description: str = ""):
        """
        Args:
            name: Nombre identificador del agente
            description: Descripción breve de qué hace el agente
        """
        self.name = name
        self.description = description

    @abstractmethod
    async def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Método principal que cada agente debe implementar.

        PEDAGOGÍA:
        - Este es el método que se llama para ejecutar el agente
        - Es async porque la mayoría de operaciones son I/O bound
        - context permite pasar información adicional si es necesario

        Args:
            query: Input del usuario (pregunta, comando, etc.)
            context: Contexto adicional opcional (historial, preferencias, etc.)

        Returns:
            AgentResponse con el resultado y metadata

        Raises:
            NotImplementedError: Si el agente hijo no implementa este método
        """
        pass

    def __repr__(self) -> str:
        """Representación string del agente"""
        return f"{self.__class__.__name__}(name='{self.name}')"
