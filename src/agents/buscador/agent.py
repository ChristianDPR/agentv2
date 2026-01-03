from __future__ import annotations

"""
Agente Buscador - Prototipo 3

Agente con arquitectura ReAct (Reasoning + Acting) para búsquedas
multi-fuente en bases de datos y filesystem.

PEDAGOGÍA:
- Demuestra loop ReAct con planeación dinámica
- Muestra function calling automático con register_tools()
- Implementa detección de loops infinitos
- Fusión de evidencias de múltiples fuentes
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from google.cloud import bigquery

from src.framework.base_agent import BaseAgent, AgentResponse
from src.framework.model_provider import ModelProvider
# from src.tools.sql_query_tool import SQLQueryTool
from src.tools.bigquery_query_tool import BigQuerySQLQueryTool
from src.tools.document_search_tool import ListDocumentsTool, ReadDocumentTool
from src.tools.finish_tool import FinishTool
from src.agents.buscador.prompts import PLAN_SYSTEM_PROMPT, REACT_SYSTEM_PROMPT
from src.agents.buscador.config import MAX_ITERATIONS, MAX_LOOP_REPEATS


class AgenteBuscador(BaseAgent):
    """
    Agente con loop ReAct para búsqueda multi-fuente.

    Flujo:
    1. PLAN: Genera estrategia de búsqueda (2-4 pasos)
    2. ACT: Ejecuta siguiente paso usando una tool
    3. OBSERVE: Guarda resultado en historial
    4. DECIDE: ¿Terminar? ¿Replanificar? ¿Continuar?
    5. REPEAT hasta finish o max_iterations
    """

    def __init__(
        self,
        model_provider: ModelProvider,
        sql_tool: BigQuerySQLQueryTool,
        list_docs_tool: ListDocumentsTool,
        read_doc_tool: ReadDocumentTool,
        finish_tool: FinishTool
    ):
        """
        Args:
            model_provider: Proveedor de LLM con function calling
            sql_tool: Tool para consultas SQL en BigQuery
            list_docs_tool: Tool para listar documentos (como ls/tree)
            read_doc_tool: Tool para leer contenido de documentos
            finish_tool: Tool para terminar el loop
        """
        super().__init__(
            name="AgenteBuscador",
            description="Búsqueda multi-fuente con razonamiento ReAct"
        )
        self.model_provider = model_provider
        self.sql_tool = sql_tool
        self.list_docs_tool = list_docs_tool
        self.read_doc_tool = read_doc_tool
        self.finish_tool = finish_tool
        self.max_iterations = MAX_ITERATIONS

        # Registrar tools para function calling automático
        self.model_provider.register_tools(self)

    async def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Ejecuta búsqueda con loop ReAct.

        Args:
            query: Consulta del usuario
            context: Contexto adicional (opcional)

        Returns:
            AgentResponse con resultados y metadata del proceso
        """
        observations: List[Dict[str, Any]] = []
        current_plan: Optional[str] = None

        for iteration in range(self.max_iterations):
            # ============================================
            # PASO 1: PLAN (si no hay plan o hay que replanificar)
            # ============================================
            if current_plan is None or self._should_replan(observations):
                current_plan = await self._generate_plan(query, observations)

            # ============================================
            # PASO 2: ACT (el LLM elige y ejecuta una tool)
            # ============================================
            prompt = self._build_action_prompt(query, current_plan, observations)
            result = await self.model_provider.generate(prompt)

            # Si el LLM responde sin usar tool (edge case)
            if isinstance(result, str):
                # Si hay observaciones y el texto no está vacío, usarlo como respuesta
                if observations and result.strip():
                    return AgentResponse(
                        content=result,
                        metadata={
                            "plan": current_plan,
                            "observations": observations,
                            "iterations": iteration + 1,
                            "finished_by": "text_response"
                        }
                    )
                # Si el texto está vacío pero tenemos observaciones, generar resumen
                elif observations:
                    return AgentResponse(
                        content=self._build_summary_from_observations(query, observations),
                        metadata={
                            "plan": current_plan,
                            "observations": observations,
                            "iterations": iteration + 1,
                            "finished_by": "auto_summary"
                        }
                    )
                continue

            # ============================================
            # PASO 3: OBSERVE (guardar resultado)
            # ============================================
            observations.append({
                "step": iteration + 1,
                "tool": result["tool_name"],
                "input": result["arguments"],
                "output": result["result"]
            })

            # ============================================
            # PASO 4: DECIDE (¿terminar? ¿loop?)
            # ============================================

            # Detectar loop infinito
            if self._detect_loop(observations):
                return AgentResponse(
                    content=self._build_partial_summary(query, observations),
                    metadata={
                        "plan": current_plan,
                        "observations": observations,
                        "iterations": iteration + 1,
                        "error": "loop_detected"
                    }
                )

            # ¿Terminó con finish?
            if result["tool_name"] == "finish":
                return AgentResponse(
                    content=result["result"]["summary"],
                    metadata={
                        "plan": current_plan,
                        "observations": observations,
                        "iterations": iteration + 1,
                        "sources": result["result"].get("sources", []),
                        "confidence": result["result"].get("confidence", "medium")
                    }
                )

        # Max iterations alcanzado
        return self._fallback_response(query, observations, current_plan)

    async def _generate_plan(
        self,
        query: str,
        observations: List[Dict[str, Any]]
    ) -> str:
        """
        Genera un plan de búsqueda (sin ejecutar tools).

        El prompt indica claramente que solo debe planificar,
        no ejecutar acciones.
        """
        obs_text = self._format_observations(observations)

        prompt = f"""{PLAN_SYSTEM_PROMPT}

Query del usuario: {query}

{obs_text}

Genera un plan con 2-4 pasos concretos. NO ejecutes ninguna acción, solo planifica.

Formato:
1. [Acción específica usando sql_query o document_search]
2. [Acción específica]
...
"""
        plan = await self.model_provider.generate(prompt)

        # Si retorna dict (usó tool), extraer texto o usar default
        if isinstance(plan, dict):
            return "1. Buscar información relevante\n2. Consolidar resultados"

        return plan

    def _build_action_prompt(
        self,
        query: str,
        plan: str,
        observations: List[Dict[str, Any]]
    ) -> str:
        """Construye el prompt para que el LLM ejecute el siguiente paso."""
        obs_text = self._format_observations(observations)

        return f"""{REACT_SYSTEM_PROMPT}

Query del usuario: {query}

Plan actual:
{plan}

{obs_text}

Ejecuta el siguiente paso del plan usando una tool.
Si ya tienes suficiente información, usa "finish" para generar la respuesta final.
"""

    def _format_observations(self, observations: List[Dict[str, Any]]) -> str:
        """Formatea el historial de observaciones para el contexto."""
        if not observations:
            return "Aún no has realizado ninguna acción."

        formatted = "Historial de acciones:\n"
        for obs in observations:
            # Truncar output si es muy largo
            output = obs["output"]
            if isinstance(output, dict):
                output_str = str(output)
                if len(output_str) > 500:
                    output_str = output_str[:500] + "..."
            else:
                output_str = str(output)

            formatted += f"""
Paso {obs['step']}:
- Tool: {obs['tool']}
- Input: {obs['input']}
- Resultado: {output_str}
"""
        return formatted

    def _should_replan(self, observations: List[Dict[str, Any]]) -> bool:
        """Decide si hay que replanificar (resultado vacío, error, etc.)"""
        if not observations:
            return False

        last_obs = observations[-1]
        output = last_obs.get("output", {})

        # Replanificar si el último resultado fue error
        if isinstance(output, dict):
            if output.get("error"):
                return True
            # Replanificar si no hubo resultados
            if output.get("count", -1) == 0:
                return True

        return False

    def _detect_loop(
        self,
        observations: List[Dict[str, Any]],
        max_repeats: int = MAX_LOOP_REPEATS
    ) -> bool:
        """
        Detecta si el agente está en un loop infinito.

        Args:
            observations: Lista de observaciones
            max_repeats: Máximo de repeticiones permitidas (default 3)

        Returns:
            True si se detecta loop
        """
        if len(observations) < max_repeats:
            return False

        # Crear firma de cada observación (tool + args)
        def signature(obs):
            args = obs.get("input", {})
            if isinstance(args, dict):
                return f"{obs['tool']}:{sorted(args.items())}"
            return f"{obs['tool']}:{args}"

        signatures = [signature(obs) for obs in observations]

        # Detectar si la última acción se repitió demasiadas veces
        last_sig = signatures[-1]
        repeat_count = signatures.count(last_sig)

        return repeat_count >= max_repeats

    def _build_partial_summary(
        self,
        query: str,
        observations: List[Dict[str, Any]]
    ) -> str:
        """Construye un resumen parcial cuando hay loop o timeout."""
        summary = f"Búsqueda parcial para: {query}\n\n"

        # Recopilar resultados útiles
        results = []
        for obs in observations:
            output = obs.get("output", {})
            if isinstance(output, dict) and not output.get("error"):
                if output.get("count", 0) > 0:
                    results.append(f"- {obs['tool']}: {output.get('count', 0)} resultados")

        if results:
            summary += "Resultados encontrados:\n" + "\n".join(results)
        else:
            summary += "No se encontraron resultados relevantes."

        return summary

    def _build_summary_from_observations(
        self,
        query: str,
        observations: List[Dict[str, Any]]
    ) -> str:
        """Construye un resumen estructurado a partir de las observaciones."""
        summary_parts = [f"Resultados de búsqueda para: {query}\n"]

        for obs in observations:
            tool = obs.get("tool", "unknown")
            output = obs.get("output", {})

            if isinstance(output, dict):
                if output.get("error"):
                    continue  # Ignorar errores en el resumen

                count = output.get("count", 0)
                if count > 0:
                    if tool == "sql_query":
                        results = output.get("results", [])
                        if results:
                            # Extraer info clave del primer resultado
                            first = results[0]
                            if "nombre" in first:
                                summary_parts.append(f"\n📋 Datos del afiliado:")
                                nombre = f"{first.get('nombre', '')} {first.get('apellido_paterno', '')}"
                                summary_parts.append(f"  - Nombre: {nombre}")
                                if "estado" in first:
                                    summary_parts.append(f"  - Estado: {first['estado']}")
                                if "saldo_obligatorio" in first:
                                    saldo = first.get('saldo_obligatorio', 0) + first.get('saldo_voluntario', 0)
                                    summary_parts.append(f"  - Saldo total: ${saldo:,.0f}")
                            elif "monto" in first and "periodo" in first:
                                summary_parts.append(f"\n💰 Aportes encontrados: {count}")
                            elif "afp_origen" in first:
                                summary_parts.append(f"\n🔄 Traspasos encontrados: {count}")
                            else:
                                summary_parts.append(f"\n📊 {count} registros encontrados en {tool}")

                    elif tool == "document_search":
                        docs = output.get("documents", [])
                        if docs:
                            summary_parts.append(f"\n📁 Documentos encontrados: {len(docs)}")
                            for doc in docs[:3]:
                                summary_parts.append(f"  - {doc.get('filename', 'unknown')}")

        if len(summary_parts) == 1:
            summary_parts.append("\nNo se encontraron resultados relevantes.")

        return "\n".join(summary_parts)

    def _fallback_response(
        self,
        query: str,
        observations: List[Dict[str, Any]],
        plan: Optional[str]
    ) -> AgentResponse:
        """Respuesta cuando se alcanza max_iterations."""
        summary = self._build_partial_summary(query, observations)
        summary += f"\n\n(Búsqueda terminada por límite de {self.max_iterations} iteraciones)"

        return AgentResponse(
            content=summary,
            metadata={
                "plan": plan,
                "observations": observations,
                "iterations": self.max_iterations,
                "completed": False,
                "error": "max_iterations_reached"
            }
        )


def create_agente_buscador_bigquery(
    model_provider: ModelProvider,
    documents_path: str | Path,
    bigquery_project: str | None = None,
    default_dataset: str | None = None
) -> AgenteBuscador:
    """
    Crea un AgenteBuscador configurado para BigQuery.

    Args:
        model_provider: Proveedor de LLM con function calling.
        documents_path: Ruta base para documentos locales.
        bigquery_project: Proyecto de BigQuery (opcional).
        default_dataset: Dataset por defecto para consultas (opcional).
    """
    bq_client = bigquery.Client(project=bigquery_project)
    sql_tool = BigQuerySQLQueryTool(
        bq_client=bq_client,
        default_dataset=default_dataset
    )
    list_docs_tool = ListDocumentsTool(base_path=documents_path)
    read_doc_tool = ReadDocumentTool(base_path=documents_path)
    finish_tool = FinishTool()

    return AgenteBuscador(
        model_provider=model_provider,
        sql_tool=sql_tool,
        list_docs_tool=list_docs_tool,
        read_doc_tool=read_doc_tool,
        finish_tool=finish_tool
    )
