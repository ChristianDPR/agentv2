#!/usr/bin/env python3
"""
Demo interactivo del Agente Buscador (BigQuery)

Permite probar búsquedas multi-fuente con el loop ReAct:
- Consultas SQL en BigQuery
- Búsqueda en filesystem
- Planeación y razonamiento iterativo
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Tuple

from dotenv import load_dotenv


WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

load_dotenv(WORKSPACE_ROOT / ".env", override=True)


class Colors:
    """ANSI colors para output colorido"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[35m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}{'=' * 70}{Colors.ENDC}\n")


def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'-' * 70}{Colors.ENDC}")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def print_step(step_num: int, tool: str, args: dict):
    """Imprime un paso del loop ReAct"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}[Paso {step_num}]{Colors.ENDC} Tool: {Colors.YELLOW}{tool}{Colors.ENDC}")
    print(f"  Args: {args}")


def print_observation(output: dict, verbose: bool = True):
    """Imprime el resultado de una observación"""
    if isinstance(output, dict):
        if output.get("error"):
            print(f"  {Colors.RED}Error: {output['error']}{Colors.ENDC}")
        elif output.get("finished"):
            print(f"  {Colors.GREEN}Búsqueda finalizada{Colors.ENDC}")
        elif output.get("count", 0) > 0:
            print(f"  {Colors.GREEN}Resultados: {output['count']}{Colors.ENDC}")
            if verbose and output.get("results"):
                for i, result in enumerate(output["results"][:3], 1):
                    print(f"  {Colors.CYAN}[{i}]{Colors.ENDC} ", end="")
                    if isinstance(result, dict):
                        items = list(result.items())[:3]
                        print(", ".join(f"{k}={v}" for k, v in items))
                    else:
                        print(str(result)[:100])
                if len(output.get("results", [])) > 3:
                    print(f"  {Colors.YELLOW}... y {len(output['results']) - 3} más{Colors.ENDC}")
            if verbose and output.get("documents"):
                for doc in output["documents"][:5]:
                    doc_type = doc.get('type', 'unknown')
                    size = doc.get('size_bytes', 0)
                    print(f"  {Colors.CYAN}📄{Colors.ENDC} {doc.get('filename', 'unknown')} ({doc_type}, {size} bytes)")
            if verbose and output.get("content"):
                content_preview = output["content"][:150].replace("\n", " ")
                print(f"  {Colors.CYAN}📄 Contenido:{Colors.ENDC} {content_preview}...")
        elif output.get("count", -1) == 0:
            print(f"  {Colors.YELLOW}Sin resultados{Colors.ENDC}")
        else:
            print(f"  Resultado: {str(output)[:200]}...")
    else:
        print(f"  {output}")


async def _select_chart_type(
    model_provider,
    query: str,
    label_field: str,
    value_field: str
) -> str:
    prompt = (
        "Elige el mejor tipo de gráfico para representar el resultado.\n"
        f"Pregunta: {query}\n"
        f"Etiqueta: {label_field}\n"
        f"Valor: {value_field}\n"
        "Opciones válidas: bar, line, pie.\n"
        "Responde solo con una palabra de la lista."
    )
    choice = await model_provider.generate(prompt)
    if isinstance(choice, dict):
        choice = ""
    if not isinstance(choice, str):
        return "bar"
    choice = choice.strip().lower()
    return choice if choice in {"bar", "line", "pie"} else "bar"


def _infer_chart_fields(rows: list[dict[str, Any]]) -> Tuple[str, str]:
    first = rows[0]
    numeric_keys = [k for k, v in first.items() if isinstance(v, (int, float))]
    non_numeric_keys = [k for k, v in first.items() if not isinstance(v, (int, float))]
    value_field = numeric_keys[0] if numeric_keys else list(first.keys())[0]
    label_field = non_numeric_keys[0] if non_numeric_keys else list(first.keys())[0]
    return label_field, value_field


def _render_ascii_bar(labels: Iterable[str], values: Iterable[float]) -> None:
    print_section("Gráfico (terminal)")
    max_value = max(values) if values else 0
    scale = 40 / max_value if max_value else 1
    for label, value in zip(labels, values):
        bar = "█" * max(1, int(value * scale))
        print(f"{label:20} | {bar} {value:,.2f}")


def _render_png_chart(chart_type: str, labels: list[str], values: list[float]) -> str | None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print_warning("matplotlib no está disponible; omitiendo gráfico PNG.")
        return None

    plots_dir = WORKSPACE_ROOT / "data" / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_path = plots_dir / "buscador_chart.png"

    plt.figure(figsize=(10, 6))
    if chart_type == "pie":
        plt.pie(values, labels=labels, autopct="%1.1f%%")
    elif chart_type == "line":
        plt.plot(labels, values, marker="o")
        plt.xticks(rotation=45, ha="right")
    else:
        plt.bar(labels, values)
        plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return str(output_path)


def _extract_sql_results(metadata: dict) -> list[dict[str, Any]]:
    observations = metadata.get("observations", [])
    for obs in reversed(observations):
        if obs.get("tool") == "sql_query":
            output = obs.get("output", {})
            if isinstance(output, dict) and output.get("results"):
                return output["results"]
    return []


def _ensure_bigquery_credentials() -> bool:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and not Path(credentials_path).exists():
        print_error("GOOGLE_APPLICATION_CREDENTIALS apunta a un archivo inexistente.")
        return False
    if not credentials_path:
        print_warning("GOOGLE_APPLICATION_CREDENTIALS no está definido. Usa ADC o exporta la variable.")
    return True


def _create_sample_documents(docs_path: Path):
    """Crea documentos de prueba si no existen"""
    docs_path.mkdir(parents=True, exist_ok=True)
    sample_file = docs_path / "nota_demo_buscador.txt"
    if not sample_file.exists():
        sample_file.write_text(
            "Documento de prueba para el Agente Buscador (BigQuery).\n"
            "Puedes listar y leer este archivo con las tools de documentos.\n",
            encoding="utf-8"
        )


async def initialize_components():
    """Inicializa el agente buscador con BigQuery"""
    from src.framework.model_provider import VertexAIProvider
    try:
        from src.agents.buscador.agent import create_agente_buscador_bigquery
    except ImportError:
        from google.cloud import bigquery
        from src.tools.bigquery_query_tool import BigQuerySQLQueryTool
        from src.tools.document_search_tool import ListDocumentsTool, ReadDocumentTool
        from src.tools.finish_tool import FinishTool
        from src.agents.buscador.agent import AgenteBuscador

        def create_agente_buscador_bigquery(
            model_provider: VertexAIProvider,
            documents_path: str | Path,
            bigquery_project: str | None = None,
            default_dataset: str | None = None
        ) -> AgenteBuscador:
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

    print_section("Inicializando componentes")

    if not _ensure_bigquery_credentials():
        return None

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEX_AI_PROJECT")
    if not project:
        print_error("Falta GOOGLE_CLOUD_PROJECT o VERTEX_AI_PROJECT.")
        return None

    model_provider = VertexAIProvider(
        project_id=os.getenv("VERTEX_AI_PROJECT", project),
        location=os.getenv("VERTEX_AI_LOCATION", "us-central1"),
        model_name=os.getenv("DEFAULT_LLM_MODEL", "gemini-2.0-flash")
    )
    print_success(f"ModelProvider inicializado: {model_provider.model_name}")

    docs_path = Path(os.getenv("BUSCADOR_DOCUMENTS_PATH", WORKSPACE_ROOT / "data" / "documentos_afiliados"))
    _create_sample_documents(docs_path)
    print_success(f"Directorio de documentos: {docs_path}")

    agente = create_agente_buscador_bigquery(
        model_provider=model_provider,
        documents_path=docs_path,
        bigquery_project=project,
        default_dataset=os.getenv("BIGQUERY_DEFAULT_DATASET")
    )
    print_success("AgenteBuscador (BigQuery) inicializado")

    registered = model_provider.get_registered_tools()
    print_info(f"Tools registradas en ModelProvider: {list(registered.keys())}")

    return {"agente": agente, "model_provider": model_provider}


async def run_demo():
    print_header("Demo Agente Buscador (BigQuery)")
    components = await initialize_components()
    if not components:
        return

    agente = components["agente"]
    model_provider = components["model_provider"]

    while True:
        query = input("\nConsulta (o 'salir'): ").strip()
        if not query:
            continue
        if query.lower() in {"salir", "exit", "quit"}:
            print_info("Saliendo del demo.")
            break

        print_section("Ejecutando búsqueda")
        response = await agente.run(query)

        print_success("Respuesta final:")
        print(response.content)

        results = _extract_sql_results(response.metadata)
        if results:
            label_field, value_field = _infer_chart_fields(results)
            chart_type = await _select_chart_type(
                model_provider=model_provider,
                query=query,
                label_field=label_field,
                value_field=value_field
            )
            labels = [str(row.get(label_field, ""))[:20] for row in results[:10]]
            values = [
                float(row.get(value_field, 0) or 0)
                for row in results[:10]
            ]
            _render_ascii_bar(labels, values)
            png_path = _render_png_chart(chart_type, labels, values)
            if png_path:
                print_info(f"PNG generado: {png_path}")

        if response.metadata.get("observations"):
            print_section("Observaciones")
            for obs in response.metadata["observations"]:
                print_step(obs["step"], obs["tool"], obs["input"])
                print_observation(obs["output"])


if __name__ == "__main__":
    asyncio.run(run_demo())
