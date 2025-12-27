#!/usr/bin/env python3
"""
Demo interactivo del Agente Asistente

Permite comparar Vector RAG vs Agent RAG en tiempo real.
"""

import sys
import os
import asyncio
from pathlib import Path
import json

# Agregar el directorio raíz al PYTHONPATH
WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv(WORKSPACE_ROOT / ".env", override=True)

from src.framework.model_provider import VertexAIProvider
from src.rag.vector_based.embeddings import EmbeddingGenerator
from src.rag.vector_based.vector_store import VectorStore
from src.rag.vector_based.retrieval import VectorRetrieval
from src.rag.agent_based.document_reader import DocumentReader
from src.rag.agent_based.chunk_evaluator import ChunkEvaluator
from src.rag.agent_based.retrieval import AgentRetrieval
from src.tools.checklist_tool import ChecklistTool
from src.tools.retrieval_vector_tool import RetrievalVectorTool
from src.tools.retrieval_agent_tool import RetrievalAgentTool
from src.agents.asistente.agent import AgenteAsistente


class Colors:
    """ANSI colors para output colorido"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Imprime header colorido"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")


def print_section(text):
    """Imprime sección"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'-' * 70}{Colors.ENDC}")


def print_success(text):
    """Imprime mensaje de éxito"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Imprime mensaje de error"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_warning(text):
    """Imprime advertencia"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


async def initialize_components():
    """Inicializa todos los componentes necesarios"""
    print_section("Inicializando componentes...")

    # Verificar env vars
    required_vars = ["DATABASE_URL", "VERTEX_AI_PROJECT"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print_error(f"Faltan variables de entorno: {', '.join(missing)}")
        return None

    try:
        # Model Providers (diferentes modelos para diferentes tareas)
        # Fast: Para respuestas rápidas del agente principal
        model_provider_fast = VertexAIProvider(
            project_id=os.getenv("VERTEX_AI_PROJECT"),
            location=os.getenv("VERTEX_AI_LOCATION", "us-central1"),
            model_name=os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")
        )
        print_success(f"ModelProvider Fast inicializado ({model_provider_fast.model_name})")

        # Complex: Para Agent RAG y evaluación
        model_provider_complex = VertexAIProvider(
            project_id=os.getenv("VERTEX_AI_PROJECT"),
            location=os.getenv("VERTEX_AI_LOCATION", "us-central1"),
            model_name=os.getenv("DEFAULT_LLM_MODEL_COMPLEX", "gemini-2.5-pro")
        )
        print_success(f"ModelProvider Complex inicializado ({model_provider_complex.model_name})")

        # Vector RAG components
        embedding_generator = EmbeddingGenerator(
            project_id=os.getenv("VERTEX_AI_PROJECT"),
            location=os.getenv("VERTEX_AI_LOCATION", "us-central1")
        )
        print_success("EmbeddingGenerator inicializado")

        vector_store = VectorStore(database_url=os.getenv("DATABASE_URL"))
        await vector_store.connect()
        print_success("VectorStore conectado")

        vector_retrieval = VectorRetrieval(
            embedding_generator=embedding_generator,
            vector_store=vector_store
        )
        print_success("VectorRetrieval inicializado")

        # Agent RAG components (usa modelo complejo para evaluación)
        document_reader = DocumentReader()
        chunk_evaluator = ChunkEvaluator(model_provider=model_provider_complex)
        agent_retrieval = AgentRetrieval(
            document_reader=document_reader,
            chunk_evaluator=chunk_evaluator
        )
        print_success("AgentRetrieval inicializado")

        # Tools
        checklist_tool = ChecklistTool(model_provider=model_provider_fast)
        retrieval_vector_tool = RetrievalVectorTool(vector_retrieval=vector_retrieval)
        retrieval_agent_tool = RetrievalAgentTool(agent_retrieval=agent_retrieval)
        print_success("Tools inicializadas")

        # Agentes (ambas estrategias, usando modelo rápido para respuestas)
        agente_vector = AgenteAsistente(
            model_provider=model_provider_fast,
            retrieval_vector_tool=retrieval_vector_tool,
            retrieval_agent_tool=retrieval_agent_tool,
            checklist_tool=checklist_tool,
            agentic_rag=False  # Vector RAG
        )
        print_success("Agente con Vector RAG creado")

        agente_agent = AgenteAsistente(
            model_provider=model_provider_fast,
            retrieval_vector_tool=retrieval_vector_tool,
            retrieval_agent_tool=retrieval_agent_tool,
            checklist_tool=checklist_tool,
            agentic_rag=True  # Agent RAG
        )
        print_success("Agente con Agent RAG creado")

        return {
            "vector_store": vector_store,
            "agente_vector": agente_vector,
            "agente_agent": agente_agent
        }

    except Exception as e:
        print_error(f"Error al inicializar: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_query(components, query, compare=True):
    """Ejecuta una query en uno o ambos agentes"""

    if compare:
        print_section(f"Query: {query}")
        print(f"{Colors.YELLOW}Comparando Vector RAG vs Agent RAG...{Colors.ENDC}\n")

        # Vector RAG
        print(f"{Colors.BOLD}📊 VECTOR RAG{Colors.ENDC}")
        print("-" * 70)
        import time
        start = time.time()

        result_vector = await components["agente_vector"].run(query= query, use_checklist=False)

        vector_time = time.time() - start
        print(f"\n{Colors.CYAN}Respuesta:{Colors.ENDC}")
        print(result_vector.content)
        print(f"\n{Colors.YELLOW}Tiempo: {vector_time:.2f}s{Colors.ENDC}")
        print(f"{Colors.YELLOW}Chunks usados: {result_vector.metadata['chunks_used']}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Checklist generado: {result_vector.metadata['checklist_generated']}{Colors.ENDC}")

        # Agent RAG
        print(f"\n{Colors.BOLD}🤖 AGENT RAG{Colors.ENDC}")
        print("-" * 70)
        start = time.time()

        result_agent = await components["agente_agent"].run(query= query, use_checklist=False)

        agent_time = time.time() - start
        print(f"\n{Colors.CYAN}Respuesta:{Colors.ENDC}")
        print(result_agent.content)
        print(f"\n{Colors.YELLOW}Tiempo: {agent_time:.2f}s{Colors.ENDC}")
        print(f"{Colors.YELLOW}Chunks usados: {result_agent.metadata['chunks_used']}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Checklist generado: {result_agent.metadata['checklist_generated']}{Colors.ENDC}")

        # Comparación
        print(f"\n{Colors.BOLD}📈 COMPARACIÓN{Colors.ENDC}")
        print("-" * 70)
        print(f"Velocidad: Vector RAG {vector_time:.2f}s vs Agent RAG {agent_time:.2f}s")
        speedup = agent_time / vector_time if vector_time > 0 else 0
        print(f"Vector RAG es {speedup:.1f}x más rápido")

        # Mostrar reasoning si está disponible
        if result_agent.metadata.get('chunks'):
            print(f"\n{Colors.BOLD}🧠 REASONING (Agent RAG){Colors.ENDC}")
            for i, chunk in enumerate(result_agent.metadata['chunks'][:2], 1):
                if 'reasoning' in chunk:
                    print(f"\n{i}. {chunk['citation']}")
                    print(f"   Reasoning: {chunk['reasoning']}")

    else:
        # Solo Vector RAG (más rápido)
        print_section(f"Query: {query}")
        result = await components["agente_vector"].run(query)
        print(f"\n{Colors.CYAN}Respuesta:{Colors.ENDC}")
        print(result.content)

        if result.metadata.get('checklist'):
            print(f"\n{Colors.BOLD}✅ CHECKLIST{Colors.ENDC}")
            checklist = result.metadata['checklist']
            print(f"\nProcedimiento: {checklist.get('title', 'N/A')}")
            print(f"Código: {checklist.get('procedure_code', 'N/A')}")
            print(f"\nPasos:")
            for step in checklist.get('steps', []):
                print(f"\n{step['step_number']}. {step['action']}")
                if step.get('required_documents'):
                    print(f"   Documentos: {', '.join(step['required_documents'])}")


async def interactive_mode(components):
    """Modo interactivo de consultas"""
    print_header("MODO INTERACTIVO - AGENTE ASISTENTE AFP")

    print("Comandos disponibles:")
    print("  - Escribe tu consulta y presiona Enter")
    print("  - 'compare' - Comparar Vector vs Agent RAG en siguiente query")
    print("  - 'fast' - Solo Vector RAG (más rápido)")
    print("  - 'stats' - Ver estadísticas del vector store")
    print("  - 'quit' - Salir")
    print()

    compare_mode = True

    while True:
        try:
            query = input(f"\n{Colors.BOLD}{Colors.GREEN}Tu consulta > {Colors.ENDC}").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'salir']:
                print_warning("¡Hasta luego!")
                break

            elif query.lower() == 'compare':
                compare_mode = True
                print_success("Modo comparación activado")
                continue

            elif query.lower() == 'fast':
                compare_mode = False
                print_success("Modo rápido activado (solo Vector RAG)")
                continue

            elif query.lower() == 'stats':
                stats = await components["vector_store"].get_statistics()
                print_section("Estadísticas del Vector Store")
                print(f"Total chunks: {stats['total_chunks']}")
                print("\nChunks por categoría:")
                for cat in stats['chunks_by_category']:
                    print(f"  - {cat['category']}: {cat['count']}")
                continue

            # Ejecutar query
            await run_query(components, query, compare=compare_mode)

        except KeyboardInterrupt:
            print_warning("\n¡Hasta luego!")
            break
        except Exception as e:
            print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()


async def demo_mode(components):
    """Modo demo con queries predefinidas"""
    print_header("MODO DEMO - CONSULTAS PREDEFINIDAS")

    demo_queries = [
        "¿Cómo puedo jubilarme anticipadamente?",
        "¿Qué documentos necesito para afiliarme?",
        "¿Cuánto tiempo demora un traspaso de AFP?",
    ]

    for i, query in enumerate(demo_queries, 1):
        print(f"\n{Colors.BOLD}Demo {i}/{len(demo_queries)}{Colors.ENDC}")
        await run_query(components, query, compare=True)

        if i < len(demo_queries):
            input(f"\n{Colors.YELLOW}Presiona Enter para continuar...{Colors.ENDC}")


async def main():
    """Main function"""
    print_header("AGENTE ASISTENTE AFP - DEMO INTERACTIVO")

    # Inicializar componentes
    components = await initialize_components()
    if not components:
        return 1

    # Menú
    print(f"\n{Colors.BOLD}Selecciona modo:{Colors.ENDC}")
    print("  1. Interactivo (tú haces las queries)")
    print("  2. Demo (queries predefinidas)")
    print()

    choice = input(f"{Colors.GREEN}Opción (1/2): {Colors.ENDC}").strip()

    try:
        if choice == "1":
            await interactive_mode(components)
        elif choice == "2":
            await demo_mode(components)
            # Después del demo, ofrecer modo interactivo
            print()
            cont = input(f"{Colors.GREEN}¿Continuar en modo interactivo? (s/n): {Colors.ENDC}").strip()
            if cont.lower() in ['s', 'si', 'y', 'yes']:
                await interactive_mode(components)
        else:
            print_error("Opción inválida")

    finally:
        # Cleanup
        await components["vector_store"].close()
        print_success("\nConexiones cerradas")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
