#!/usr/bin/env python3
"""
Demo interactivo del Agente Buscador (ReAct)

Permite probar búsquedas multi-fuente con el loop ReAct:
- Consultas SQL a base de datos PostgreSQL real
- Búsqueda en filesystem
- Planeación y razonamiento iterativo
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime
from google.cloud import bigquery

gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEX_AI_PROJECT")
bq_client = bigquery.Client(project=gcp_project)

default_dataset = os.getenv("BIGQUERY_DEFAULT_DATASET")  # ej: "mi_proyecto.afp"

from src.tools.bigquery_query_tool import BigQuerySQLQueryTool

sql_tool = BigQuerySQLQueryTool(
    bq_client=bq_client,
    default_dataset=default_dataset
)


# Agregar el directorio raíz al PYTHONPATH
WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv(WORKSPACE_ROOT / ".env", override=True)

import asyncpg


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
            # Mostrar los resultados si verbose está activado
            if verbose and output.get("results"):
                for i, result in enumerate(output["results"][:3], 1):  # Max 3 resultados
                    print(f"  {Colors.CYAN}[{i}]{Colors.ENDC} ", end="")
                    # Formatear resultado de forma compacta
                    if isinstance(result, dict):
                        # Mostrar campos clave
                        display_fields = []
                        for key in ["rut", "nombre", "apellido_paterno", "estado", "monto", "tipo", "periodo", "filename"]:
                            if key in result:
                                val = result[key]
                                if isinstance(val, (int, float)) and key == "monto":
                                    display_fields.append(f"{key}=${val:,.0f}")
                                else:
                                    display_fields.append(f"{key}={val}")
                        if display_fields:
                            print(", ".join(display_fields[:5]))
                        else:
                            # Si no hay campos conocidos, mostrar los primeros 3
                            items = list(result.items())[:3]
                            print(", ".join(f"{k}={v}" for k, v in items))
                    else:
                        print(str(result)[:100])
                if len(output.get("results", [])) > 3:
                    print(f"  {Colors.YELLOW}... y {len(output['results']) - 3} más{Colors.ENDC}")
            # Mostrar documentos listados (list_documents)
            if verbose and output.get("documents"):
                for doc in output["documents"][:5]:
                    doc_type = doc.get('type', 'unknown')
                    size = doc.get('size_bytes', 0)
                    print(f"  {Colors.CYAN}📄{Colors.ENDC} {doc.get('filename', 'unknown')} ({doc_type}, {size} bytes)")
            # Mostrar contenido de documento (read_document)
            if verbose and output.get("content"):
                content_preview = output["content"][:150].replace("\n", " ")
                print(f"  {Colors.CYAN}📄 Contenido:{Colors.ENDC} {content_preview}...")
        elif output.get("count", -1) == 0:
            print(f"  {Colors.YELLOW}Sin resultados{Colors.ENDC}")
        else:
            print(f"  Resultado: {str(output)[:200]}...")
    else:
        print(f"  {output}")


# =============================================================================
# Inicialización de componentes
# =============================================================================

async def initialize_components():
    """Inicializa el agente buscador con sus dependencias"""
    from src.framework.model_provider import VertexAIProvider
    from src.tools.sql_query_tool import SQLQueryTool
    from src.tools.document_search_tool import ListDocumentsTool, ReadDocumentTool
    from src.tools.finish_tool import FinishTool
    from src.agents.buscador.agent import AgenteBuscador

    print_section("Inicializando componentes")

    # Verificar variables de entorno requeridas
    required_vars = ["DATABASE_URL", "VERTEX_AI_PROJECT"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print_error(f"Faltan variables de entorno: {', '.join(missing)}")
        return None

    # Model Provider
    try:
        model_provider = VertexAIProvider(
            project_id=os.getenv("VERTEX_AI_PROJECT"),
            location=os.getenv("VERTEX_AI_LOCATION", "us-central1"),
            model_name=os.getenv("DEFAULT_LLM_MODEL", "gemini-2.0-flash")
        )
        print_success(f"ModelProvider inicializado: {model_provider.model_name}")
    except Exception as e:
        print_error(f"Error inicializando ModelProvider: {e}")
        return None

    # Conexión a PostgreSQL real
    try:
        database_url = os.getenv("DATABASE_URL")
        db_pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10
        )
        print_success("Pool de conexiones PostgreSQL creado")

        # Verificar conexión y datos
        async with db_pool.acquire() as conn:
            afiliados_count = await conn.fetchval("SELECT COUNT(*) FROM afiliados")
            aportes_count = await conn.fetchval("SELECT COUNT(*) FROM aportes")
            traspasos_count = await conn.fetchval("SELECT COUNT(*) FROM traspasos")
        print_success(f"Base de datos conectada: {afiliados_count} afiliados, {aportes_count} aportes, {traspasos_count} traspasos")

    except Exception as e:
        print_error(f"Error conectando a PostgreSQL: {e}")
        print_info("Asegúrate de que el container de PostgreSQL esté corriendo")
        return None

    # Directorio de documentos (crear si no existe)
    docs_path = WORKSPACE_ROOT / "data" / "documentos_afiliados"
    docs_path.mkdir(parents=True, exist_ok=True)

    # Crear algunos documentos de prueba si no existen
    _create_sample_documents(docs_path)
    print_success(f"Directorio de documentos: {docs_path}")

    # Tools
    sql_tool = SQLQueryTool(db_pool)
    list_docs_tool = ListDocumentsTool(docs_path)
    read_doc_tool = ReadDocumentTool(docs_path)
    finish_tool = FinishTool()
    print_success("Tools inicializadas: sql_query, list_documents, read_document, finish")

    # Agente
    agente = AgenteBuscador(
        model_provider=model_provider,
        sql_tool=sql_tool,
        list_docs_tool=list_docs_tool,
        read_doc_tool=read_doc_tool,
        finish_tool=finish_tool
    )
    print_success("AgenteBuscador inicializado")

    # Mostrar tools registradas
    registered = model_provider.get_registered_tools()
    print_info(f"Tools registradas en ModelProvider: {list(registered.keys())}")

    return {
        "agente": agente,
        "model_provider": model_provider,
        "db_pool": db_pool,
        "docs_path": docs_path
    }


def _create_sample_documents(docs_path: Path):
    """Crea documentos de prueba para el demo (basados en seed data real)"""
    # Documentos basados en los RUTs reales del seed.sql
    samples = [
        # Certificados de aportes
        ("certificado_12345678-9_2024.txt",
         "CERTIFICADO DE APORTES PREVISIONALES\n"
         "========================================\n"
         "RUT: 12.345.678-9\n"
         "Nombre: Juan Pérez González\n"
         "Empleador: Minera Los Andes SpA\n"
         "Período: Enero - Octubre 2024\n"
         "Total aportes obligatorios: $1.850.000\n"
         "Total aportes voluntarios: $600.000\n"
         "Estado: Activo\n"
         "Fondo: B\n"
         "Fecha emisión: 15/11/2024"),

        ("certificado_98765432-1_2024.txt",
         "CERTIFICADO DE APORTES PREVISIONALES\n"
         "========================================\n"
         "RUT: 98.765.432-1\n"
         "Nombre: María Silva López\n"
         "Empleador: TechSolutions Chile SA\n"
         "Período: Enero - Octubre 2024\n"
         "Total aportes obligatorios: $2.200.000\n"
         "Total aportes voluntarios: $500.000\n"
         "Estado: Activo\n"
         "Fondo: C"),

        # Solicitudes de traspaso
        ("traspaso_12345678-9_2023.txt",
         "SOLICITUD DE TRASPASO\n"
         "========================================\n"
         "Número: TRP-2023-00156\n"
         "RUT: 12.345.678-9\n"
         "Nombre: Juan Pérez González\n"
         "AFP Origen: AFP Habitat\n"
         "AFP Destino: AFP Capital\n"
         "Monto trasladado: $46.500.000\n"
         "Fecha solicitud: 15/06/2023\n"
         "Fecha ejecución: 20/07/2023\n"
         "Estado: COMPLETADO"),

        ("traspaso_11111111-1_2024.txt",
         "SOLICITUD DE TRASPASO\n"
         "========================================\n"
         "Número: TRP-2024-00078\n"
         "RUT: 11.111.111-1\n"
         "Nombre: Pedro Rojas Muñoz\n"
         "AFP Origen: AFP Modelo\n"
         "AFP Destino: AFP PlanVital\n"
         "Monto trasladado: $31.800.000\n"
         "Estado: EN PROCESO"),

        # Reclamos
        ("reclamo_RCL-2024-00004.txt",
         "RECLAMO - TICKET RCL-2024-00004\n"
         "========================================\n"
         "RUT Afiliado: 44.444.444-4\n"
         "Nombre: Carmen Soto Díaz\n"
         "Tipo: Retraso en pago de cotizaciones\n"
         "Prioridad: URGENTE\n"
         "Canal: Web\n"
         "Fecha: 05/09/2024\n"
         "Descripción: Empleador Agrícola del Sur Ltda no ha pagado\n"
         "cotizaciones de los últimos 3 meses.\n"
         "Monto reclamado: $2.850.000\n"
         "Estado: EN REVISIÓN\n"
         "Agente asignado: Pedro Soto"),

        ("reclamo_RCL-2024-00006.txt",
         "RECLAMO - TICKET RCL-2024-00006\n"
         "========================================\n"
         "RUT Afiliado: 66.666.666-6\n"
         "Nombre: Patricia Ramírez Herrera\n"
         "Tipo: Retraso en pago de cotizaciones\n"
         "Prioridad: URGENTE\n"
         "Empleador: Retail MegaStore Chile\n"
         "Estado: ESCALADO\n"
         "Monto afectado: $4.200.000"),

        # Pensiones
        ("pension_77777777-7.txt",
         "CERTIFICADO DE PENSIÓN\n"
         "========================================\n"
         "RUT: 77.777.777-7\n"
         "Nombre: Diego Navarro Bravo\n"
         "Tipo: Vejez Normal\n"
         "Modalidad: Retiro Programado\n"
         "Monto mensual: $485.000\n"
         "Fecha inicio: 01/05/2023\n"
         "Estado: ACTIVA\n"
         "Beneficiario registrado: Marta Navarro López (cónyuge)"),

        # Beneficiarios
        ("beneficiarios_10101010-1.txt",
         "REGISTRO DE BENEFICIARIOS\n"
         "========================================\n"
         "Afiliado: Ricardo Fuentes Mora (FALLECIDO)\n"
         "RUT: 10.101.010-1\n"
         "\n"
         "Beneficiarios designados:\n"
         "1. Elena Fuentes Mora - Cónyuge - 60%\n"
         "2. Carlos Fuentes Torres - Hijo - 20%\n"
         "3. Andrea Fuentes Torres - Hijo - 20%\n"
         "\n"
         "Pensión de sobrevivencia: $420.000 mensuales\n"
         "Compañía: Seguros Consorcio"),

        # Empleador moroso
        ("cobranza_agricola_sur.txt",
         "INFORME DE COBRANZA\n"
         "========================================\n"
         "Empleador: Agrícola del Sur Ltda\n"
         "RUT: 76.000.004-4\n"
         "Estado: MOROSO\n"
         "Deuda total: $15.600.000\n"
         "Trabajadores afectados: 85\n"
         "Períodos adeudados: Agosto - Noviembre 2024\n"
         "Gestiones realizadas:\n"
         "- 15/09/2024: Carta de cobranza enviada\n"
         "- 01/10/2024: Llamada telefónica sin respuesta\n"
         "- 15/10/2024: Segunda carta certificada"),
    ]

    for filename, content in samples:
        filepath = docs_path / filename
        if not filepath.exists():
            filepath.write_text(content, encoding='utf-8')


# =============================================================================
# Procesamiento de queries
# =============================================================================

async def process_query(agente, query: str):
    """Procesa una query y muestra el resultado paso a paso"""
    print_section(f"Query: {query}")

    start_time = datetime.now()

    try:
        result = await agente.run(query)

        elapsed = (datetime.now() - start_time).total_seconds()

        # Mostrar pasos del loop ReAct
        print_section("Loop ReAct")
        observations = result.metadata.get("observations", [])

        if not observations:
            print_warning("No se registraron observaciones")
        else:
            for obs in observations:
                print_step(obs["step"], obs["tool"], obs["input"])
                print_observation(obs["output"])

        # Mostrar plan
        plan = result.metadata.get("plan")
        if plan:
            print_section("Plan generado")
            print(f"{Colors.CYAN}{plan}{Colors.ENDC}")

        # Mostrar resultado final
        print_section("Respuesta Final")
        print(f"{Colors.GREEN}{result.content}{Colors.ENDC}")

        # Metadata
        print_section("Metadata")
        print(f"  Iteraciones: {result.metadata.get('iterations', 'N/A')}")
        print(f"  Confianza: {result.metadata.get('confidence', 'N/A')}")
        print(f"  Tiempo: {elapsed:.2f}s")

        if result.metadata.get("error"):
            print_warning(f"Error: {result.metadata['error']}")

        sources = result.metadata.get("sources", [])
        if sources:
            print(f"  Fuentes: {', '.join(sources)}")

        return result

    except Exception as e:
        print_error(f"Error procesando query: {e}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# Casos de prueba (diseñados para mostrar capacidades avanzadas)
# =============================================================================

DEMO_QUERIES = [
    # Búsquedas simples
    {
        "id": "B001",
        "query": "Buscar información completa del afiliado con RUT 12.345.678-9",
        "description": "Búsqueda simple de afiliado (Juan Pérez - Minera Los Andes)"
    },
    {
        "id": "B002",
        "query": "¿Cuántos aportes ha realizado María Silva y cuál es su saldo total?",
        "description": "Búsqueda de aportes + cálculo agregado"
    },

    # Búsquedas multi-tabla (JOINs implícitos)
    {
        "id": "B003",
        "query": "¿Qué afiliados trabajan en empresas morosas y cuánto les deben?",
        "description": "Cruce afiliados + empleadores morosos"
    },
    {
        "id": "B004",
        "query": "Mostrar los reclamos urgentes abiertos y los datos del afiliado que los hizo",
        "description": "Reclamos + datos de afiliados"
    },

    # Escenarios complejos
    {
        "id": "B005",
        "query": "¿Cuáles son los beneficiarios del afiliado fallecido Ricardo Fuentes y qué pensión reciben?",
        "description": "Beneficiarios + pensión de sobrevivencia"
    },
    {
        "id": "B006",
        "query": "Buscar todos los traspasos rechazados y sus motivos",
        "description": "Traspasos con análisis de motivos"
    },

    # Análisis de negocio
    {
        "id": "B007",
        "query": "¿Cuántos afiliados tiene cada tipo de fondo (A, B, C, D, E) y cuál es el saldo promedio?",
        "description": "Análisis de distribución de fondos"
    },
    {
        "id": "B008",
        "query": "¿Qué afiliados tienen aportes en estado 'en_cobranza' y cuánto es el monto total adeudado?",
        "description": "Análisis de cobranza"
    },

    # Búsquedas multi-fuente (SQL + filesystem)
    {
        "id": "B009",
        "query": "Buscar toda la información del RUT 12345678-9: datos personales, aportes recientes, traspasos, reclamos y documentos",
        "description": "Búsqueda exhaustiva multi-fuente"
    },

    # Pensionados
    {
        "id": "B010",
        "query": "Listar todos los pensionados, su tipo de pensión, monto mensual y modalidad",
        "description": "Análisis de pensionados"
    },

    # Edge cases
    {
        "id": "B011",
        "query": "¿Hay afiliados con reclamos de prioridad urgente que aún no tienen agente asignado?",
        "description": "Detección de casos críticos sin atención"
    },
    {
        "id": "B012",
        "query": "Buscar afiliado con RUT 99999999-0",
        "description": "Búsqueda de RUT inexistente"
    },

    # Búsquedas específicas de documentos (filesystem)
    {
        "id": "D001",
        "query": "¿Qué documentos hay disponibles en el sistema?",
        "description": "Listar todos los documentos (list_documents)"
    },
    {
        "id": "D002",
        "query": "Buscar todos los certificados disponibles y mostrar su contenido",
        "description": "Filtrar documentos por tipo + leer contenido"
    },
    {
        "id": "D003",
        "query": "¿Hay algún documento de reclamo? Si existe, muéstrame el contenido completo",
        "description": "Buscar documentos de reclamos + leer"
    },
    {
        "id": "D004",
        "query": "Buscar documentos relacionados con cobranza o empleadores morosos",
        "description": "Búsqueda de documentos de cobranza"
    },
    {
        "id": "D005",
        "query": "¿Existe algún documento sobre el pensionado con RUT 77777777-7? Si hay, léelo",
        "description": "Documento de pensión específico"
    },
]


async def run_demo_mode(agente):
    """Ejecuta el modo demo con casos predefinidos"""
    print_header("MODO DEMO - Casos de Prueba")

    print("Casos disponibles:")
    for i, case in enumerate(DEMO_QUERIES, 1):
        print(f"  {i}. [{case['id']}] {case['description']}")
        print(f"     Query: {case['query'][:50]}...")

    print(f"\n  0. Ejecutar todos (con pausas)")
    print(f"  a. Ejecutar todos AUTOMÁTICO (sin pausas)")
    print(f"  q. Volver al menú principal")

    choice = input(f"\n{Colors.BOLD}Selecciona un caso: {Colors.ENDC}").strip().lower()

    if choice == 'q':
        return
    elif choice == '0':
        for case in DEMO_QUERIES:
            await process_query(agente, case["query"])
            input(f"\n{Colors.CYAN}Presiona Enter para continuar...{Colors.ENDC}")
    elif choice == 'a':
        await run_automatic_demo(agente)
    elif choice.isdigit() and 1 <= int(choice) <= len(DEMO_QUERIES):
        case = DEMO_QUERIES[int(choice) - 1]
        await process_query(agente, case["query"])
    else:
        print_error("Opción inválida")


async def run_automatic_demo(agente):
    """Ejecuta todas las queries automáticamente y genera un reporte"""
    print_header("DEMO AUTOMÁTICO - Ejecutando todas las queries")

    results_summary = []
    total_start = datetime.now()

    for i, case in enumerate(DEMO_QUERIES, 1):
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}[{i}/{len(DEMO_QUERIES)}] {case['id']}: {case['description']}{Colors.ENDC}")
        print(f"{Colors.CYAN}Query: {case['query']}{Colors.ENDC}")
        print("-" * 70)

        start_time = datetime.now()
        try:
            result = await agente.run(case["query"])
            elapsed = (datetime.now() - start_time).total_seconds()

            # Resumen compacto de observaciones
            observations = result.metadata.get("observations", [])
            tools_used = []
            for obs in observations:
                tool = obs["tool"]
                output = obs.get("output", {})
                if isinstance(output, dict):
                    if output.get("error"):
                        tools_used.append(f"{tool}:ERROR")
                    elif output.get("finished"):
                        tools_used.append(f"{tool}:OK")
                    elif output.get("content"):
                        # read_document devuelve content, no count
                        content_len = len(output.get("content", ""))
                        tools_used.append(f"{tool}:✓({content_len}c)")
                    elif output.get("count", 0) > 0:
                        tools_used.append(f"{tool}:{output['count']}")
                    elif output.get("documents"):
                        # list_documents sin count pero con documents
                        tools_used.append(f"{tool}:{len(output['documents'])}")
                    else:
                        tools_used.append(f"{tool}:∅")

            # Determinar estado
            has_error = result.metadata.get("error")
            has_content = bool(result.content.strip())

            if has_error:
                status = f"{Colors.RED}ERROR{Colors.ENDC}"
                status_code = "ERROR"
            elif has_content and len(result.content) > 50:
                status = f"{Colors.GREEN}OK{Colors.ENDC}"
                status_code = "OK"
            else:
                status = f"{Colors.YELLOW}PARCIAL{Colors.ENDC}"
                status_code = "PARCIAL"

            print(f"  Status: {status} | Tiempo: {elapsed:.1f}s | Iteraciones: {result.metadata.get('iterations', '?')}")
            print(f"  Tools: {' → '.join(tools_used)}")

            # Mostrar cada paso/observación
            if observations:
                print(f"\n  {Colors.BOLD}Pasos del agente:{Colors.ENDC}")
                for obs in observations:
                    step = obs.get("step", "?")
                    tool = obs.get("tool", "unknown")
                    args = obs.get("input", {})
                    output = obs.get("output", {})

                    # Formatear argumentos de forma compacta
                    if isinstance(args, dict):
                        args_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in args.items())
                    else:
                        args_str = str(args)[:50]

                    print(f"    {Colors.CYAN}[{step}]{Colors.ENDC} {Colors.YELLOW}{tool}{Colors.ENDC}({args_str})")

                    # Mostrar resultado de la observación
                    if isinstance(output, dict):
                        if output.get("error"):
                            print(f"        → {Colors.RED}Error: {output['error']}{Colors.ENDC}")
                        elif output.get("finished"):
                            print(f"        → {Colors.GREEN}Finalizado{Colors.ENDC}")
                        elif output.get("content"):
                            content_preview = output["content"][:100].replace('\n', ' ')
                            print(f"        → {Colors.GREEN}Contenido ({len(output['content'])} chars): {content_preview}...{Colors.ENDC}")
                        elif output.get("results"):
                            print(f"        → {Colors.GREEN}{len(output['results'])} resultados SQL{Colors.ENDC}")
                            for r in output["results"][:2]:
                                if isinstance(r, dict):
                                    preview = ", ".join(f"{k}={v}" for k, v in list(r.items())[:3])
                                    print(f"           {Colors.CYAN}{preview}{Colors.ENDC}")
                        elif output.get("documents"):
                            print(f"        → {Colors.GREEN}{len(output['documents'])} documentos{Colors.ENDC}")
                            for doc in output["documents"][:3]:
                                print(f"           {Colors.CYAN}📄 {doc.get('filename', '?')}{Colors.ENDC}")
                        elif output.get("count") == 0:
                            print(f"        → {Colors.YELLOW}Sin resultados{Colors.ENDC}")

            # Mostrar respuesta completa y bien formateada
            print(f"\n  {Colors.BOLD}Respuesta final:{Colors.ENDC}")
            print(f"  {Colors.CYAN}{'─' * 66}{Colors.ENDC}")
            # Indentar cada línea de la respuesta
            for line in result.content.strip().split('\n'):
                print(f"  {Colors.GREEN}{line}{Colors.ENDC}")
            print(f"  {Colors.CYAN}{'─' * 66}{Colors.ENDC}")

            results_summary.append({
                "id": case["id"],
                "description": case["description"],
                "status": status_code,
                "time": elapsed,
                "iterations": result.metadata.get("iterations", 0),
                "tools_used": tools_used,
                "error": result.metadata.get("error")
            })

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"  {Colors.RED}EXCEPCIÓN: {e}{Colors.ENDC}")
            results_summary.append({
                "id": case["id"],
                "description": case["description"],
                "status": "EXCEPTION",
                "time": elapsed,
                "iterations": 0,
                "tools_used": [],
                "error": str(e)
            })

    # Reporte final
    total_elapsed = (datetime.now() - total_start).total_seconds()
    print_header("REPORTE FINAL")

    ok_count = sum(1 for r in results_summary if r["status"] == "OK")
    partial_count = sum(1 for r in results_summary if r["status"] == "PARCIAL")
    error_count = sum(1 for r in results_summary if r["status"] in ["ERROR", "EXCEPTION"])

    print(f"{Colors.GREEN}✓ OK: {ok_count}{Colors.ENDC} | {Colors.YELLOW}⚠ Parcial: {partial_count}{Colors.ENDC} | {Colors.RED}✗ Error: {error_count}{Colors.ENDC}")
    print(f"Tiempo total: {total_elapsed:.1f}s | Promedio: {total_elapsed/len(DEMO_QUERIES):.1f}s por query")

    # Tabla de resultados
    print(f"\n{Colors.BOLD}Detalle:{Colors.ENDC}")
    print("-" * 90)
    print(f"{'ID':<8} {'Status':<10} {'Tiempo':<8} {'Iter':<5} {'Tools':<40}")
    print("-" * 90)

    for r in results_summary:
        status_color = {
            "OK": Colors.GREEN,
            "PARCIAL": Colors.YELLOW,
            "ERROR": Colors.RED,
            "EXCEPTION": Colors.RED
        }.get(r["status"], "")

        tools_str = " → ".join(r["tools_used"][:5])
        if len(r["tools_used"]) > 5:
            tools_str += "..."

        print(f"{r['id']:<8} {status_color}{r['status']:<10}{Colors.ENDC} {r['time']:<8.1f} {r['iterations']:<5} {tools_str:<40}")

    # Mostrar errores si los hay
    errors = [r for r in results_summary if r["status"] in ["ERROR", "EXCEPTION"]]
    if errors:
        print(f"\n{Colors.RED}Errores detectados:{Colors.ENDC}")
        for r in errors:
            print(f"  - {r['id']}: {r['error']}")


async def run_interactive_mode(agente):
    """Ejecuta el modo interactivo"""
    print_header("MODO INTERACTIVO")

    print("Escribe tus queries para el Agente Buscador.")
    print("Escribe 'salir' o 'q' para volver al menú principal.\n")

    while True:
        try:
            query = input(f"{Colors.BOLD}Tu query: {Colors.ENDC}").strip()

            if not query:
                continue

            if query.lower() in ['salir', 'q', 'exit', 'quit']:
                break

            await process_query(agente, query)

        except KeyboardInterrupt:
            print("\n")
            break


async def show_database_data(db_pool):
    """Muestra los datos disponibles en la base de datos"""
    print_section("Datos en Base de Datos PostgreSQL")

    async with db_pool.acquire() as conn:
        # Resumen general
        stats = await conn.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM afiliados) AS afiliados,
                (SELECT COUNT(*) FROM empleadores) AS empleadores,
                (SELECT COUNT(*) FROM aportes) AS aportes,
                (SELECT COUNT(*) FROM traspasos) AS traspasos,
                (SELECT COUNT(*) FROM reclamos) AS reclamos,
                (SELECT COUNT(*) FROM beneficiarios) AS beneficiarios,
                (SELECT COUNT(*) FROM pensiones) AS pensiones
        """)
        print(f"\n{Colors.BOLD}Resumen:{Colors.ENDC}")
        print(f"  Afiliados: {stats['afiliados']} | Empleadores: {stats['empleadores']}")
        print(f"  Aportes: {stats['aportes']} | Traspasos: {stats['traspasos']}")
        print(f"  Reclamos: {stats['reclamos']} | Beneficiarios: {stats['beneficiarios']}")
        print(f"  Pensiones: {stats['pensiones']}")

        # Afiliados por estado
        estados = await conn.fetch("""
            SELECT estado, COUNT(*) as total
            FROM afiliados GROUP BY estado ORDER BY total DESC
        """)
        print(f"\n{Colors.CYAN}Afiliados por estado:{Colors.ENDC}")
        for e in estados:
            print(f"  - {e['estado']}: {e['total']}")

        # Empleadores morosos
        morosos = await conn.fetch("""
            SELECT razon_social, estado, deuda_total, cantidad_trabajadores
            FROM empleadores WHERE estado IN ('moroso', 'en_cobranza')
            ORDER BY deuda_total DESC
        """)
        if morosos:
            print(f"\n{Colors.YELLOW}Empleadores morosos:{Colors.ENDC}")
            for m in morosos:
                print(f"  - {m['razon_social']}: ${m['deuda_total']:,.0f} ({m['cantidad_trabajadores']} trabajadores)")

        # Reclamos abiertos por prioridad
        reclamos = await conn.fetch("""
            SELECT prioridad, COUNT(*) as total
            FROM reclamos WHERE estado IN ('abierto', 'en_revision', 'escalado')
            GROUP BY prioridad ORDER BY
            CASE prioridad WHEN 'urgente' THEN 1 WHEN 'alta' THEN 2 WHEN 'media' THEN 3 ELSE 4 END
        """)
        if reclamos:
            print(f"\n{Colors.RED}Reclamos activos por prioridad:{Colors.ENDC}")
            for r in reclamos:
                print(f"  - {r['prioridad']}: {r['total']}")

        # Top 5 afiliados por saldo
        top_saldos = await conn.fetch("""
            SELECT rut, nombre, apellido_paterno, saldo_obligatorio + saldo_voluntario as saldo_total
            FROM afiliados WHERE estado = 'activo'
            ORDER BY saldo_total DESC LIMIT 5
        """)
        print(f"\n{Colors.GREEN}Top 5 afiliados por saldo:{Colors.ENDC}")
        for a in top_saldos:
            print(f"  - {a['nombre']} {a['apellido_paterno']}: ${a['saldo_total']:,.0f}")


# =============================================================================
# Main
# =============================================================================

async def main():
    """Punto de entrada principal"""
    print_header("AGENTE BUSCADOR - Demo ReAct")

    # Inicializar
    components = await initialize_components()
    if not components:
        print_error("No se pudieron inicializar los componentes")
        return 1

    agente = components["agente"]
    db_pool = components["db_pool"]

    try:
        # Menú principal
        while True:
            print_section("Menú Principal")
            print("  1. Modo Demo (casos predefinidos)")
            print("  2. Modo Interactivo")
            print("  3. Ver datos en base de datos")
            print("  q. Salir")

            choice = input(f"\n{Colors.BOLD}Selecciona una opción: {Colors.ENDC}").strip().lower()

            if choice == '1':
                await run_demo_mode(agente)
            elif choice == '2':
                await run_interactive_mode(agente)
            elif choice == '3':
                await show_database_data(db_pool)
            elif choice in ['q', 'quit', 'exit', 'salir']:
                print_success("¡Hasta luego!")
                break
            else:
                print_error("Opción inválida")

    finally:
        # Cleanup
        await db_pool.close()
        print_success("Conexiones cerradas")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
