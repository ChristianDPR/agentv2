# Ejercicios - Function Calling

## Ejercicio 1: Agente con Tools Mock

Crear un agente usando las tools mock incluidas.

```python
from src.agents.ejercicios import AgenteGenerico, WeatherTool, CalculatorTool, TimeTool
from src.tools.finish_tool import FinishTool

agente = AgenteGenerico(
    model_provider=provider,
    system_prompt="Eres un asistente que puede consultar clima, hacer cálculos y ver la hora. Usa finish() cuando tengas la respuesta.",
    tools=[WeatherTool(), CalculatorTool(), TimeTool(), FinishTool()]
)

resultado = await agente.run("¿Qué hora es y cuánto es 15 * 7?")
```

---

## Ejercicio 2: Reutilizar Tools Existentes

Usar tools de los agentes del curso con el AgenteGenerico.

```python
from src.agents.ejercicios import AgenteGenerico
from src.tools.sql_query_tool import SQLQueryTool
from src.tools.document_search_tool import ListDocumentsTool
from src.tools.finish_tool import FinishTool

agente = AgenteGenerico(
    model_provider=provider,
    system_prompt="Eres un buscador. Puedes consultar SQL y listar documentos.",
    tools=[sql_tool, list_docs_tool, FinishTool()]
)
```

---

## Ejercicio 3: Crear una Tool Nueva

Crear una tool propia y agregarla al agente.

```python
from src.tools.checklist_tool import Tool, ToolDefinition

class MiTool(Tool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="mi_tool",
            description="Descripción para el LLM",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "..."}
                },
                "required": ["param1"]
            }
        )

    async def execute(self, param1: str):
        return {"resultado": f"Procesado: {param1}"}
```

---

## Ejercicio 4: Frankenstein Agent

Mezclar tools de diferentes agentes.

```python
from src.tools.classifier_tool import ClassifierTool  # De Reclamos
from src.tools.sql_query_tool import SQLQueryTool      # De Buscador
from src.agents.ejercicios import WeatherTool          # Mock

agente = AgenteGenerico(
    model_provider=provider,
    system_prompt="Eres un agente experimental con múltiples capacidades.",
    tools=[ClassifierTool(provider), sql_tool, WeatherTool(), FinishTool()]
)
```

---

## Ejercicio 5: Comparar Arquitecturas

Comparar el Agente Reclamos original vs la versión function calling.

```python
# Original (flujo fijo)
from src.agents.reclamos.agent import create_agente_reclamos

# Function calling
from src.agents.reclamos.agent_fc import create_agente_reclamos_fc

# Probar ambos con el mismo reclamo
reclamo = "Me cobraron comisiones que no reconozco"

resultado_fijo = await agente_original.run(reclamo)
resultado_fc = await agente_fc.run(reclamo)

# Comparar: ¿Mismas decisiones? ¿Mismo orden de tools?
```
