"""
Demo: Retrieval con Índices JSON (3 Fases)

Demuestra cómo usar el nuevo sistema de retrieval basado en índices.

REQUISITOS:
1. Índices JSON generados en data/indices/
2. Documentos originales en data/documentos/
3. Credenciales de Vertex AI configuradas

COMPARACIÓN:
- retrieve_old(): Lee TODOS los documentos completos (lento)
- retrieve_with_index(): Lee solo índices → secciones específicas (rápido)
"""

import asyncio
import os
import sys
from pathlib import Path

# Agregar src/ al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.agent_based.document_reader import DocumentReader
from src.rag.agent_based.chunk_evaluator import ChunkEvaluator
from src.rag.agent_based.retrieval import AgentRetrieval
from src.framework.model_provider import VertexAIProvider


async def demo_indexed_retrieval():
    """
    Demo completo del retrieval con índices.
    """
    print("=" * 80)
    print("DEMO: RETRIEVAL CON ÍNDICES JSON (3 FASES)")
    print("=" * 80)
    print()

    # Verificar credenciales
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not Path(creds_path).exists():
        print("❌ Error: GOOGLE_APPLICATION_CREDENTIALS no configurado")
        print("   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json")
        return

    # Verificar que existan índices
    indices_dir = Path("data/indices")
    if not indices_dir.exists() or not list(indices_dir.glob("index-*.json")):
        print("❌ Error: No hay índices JSON en data/indices/")
        print("   Ejecuta primero: python scripts/generate_indices.py")
        return

    print(f"✅ Índices encontrados: {len(list(indices_dir.glob('index-*.json')))}")
    print()

    # Configurar componentes
    print("🔧 Configurando componentes...")
    project_id = os.getenv("VERTEX_AI_PROJECT", "rosy-sky-364021")
    location = os.getenv("VERTEX_AI_LOCATION", "us-central1")

    model_provider = VertexAIProvider(
        project_id=project_id,
        location=location,
        model_name="gemini-2.0-flash-001"
    )

    document_reader = DocumentReader()
    chunk_evaluator = ChunkEvaluator(model_provider=model_provider)
    retrieval = AgentRetrieval(
        document_reader=document_reader,
        chunk_evaluator=chunk_evaluator
    )

    print("✅ Componentes configurados")
    print()

    # Queries de prueba
    queries = [
        "¿Cómo puedo jubilarme anticipadamente?",
        "¿Qué requisitos necesito para jubilarme antes de tiempo?",
        "¿Cuáles son los riesgos de jubilar anticipadamente?"
    ]

    for i, query in enumerate(queries, 1):
        print("=" * 80)
        print(f"QUERY {i}/{len(queries)}")
        print("=" * 80)
        print(f"📝 {query}")
        print()

        # ========================================================================
        # MÉTODO NUEVO: Retrieval con índices (3 fases)
        # ========================================================================
        print("🚀 MÉTODO NUEVO: Retrieval con índices (3 fases)")
        print("-" * 80)

        try:
            result = await retrieval.retrieve_with_index(
                query=query,
                indices_dir="data/indices",
                documents_path="data/documentos"
            )

            print()
            print("📊 RESULTADOS:")
            print(f"   Método: {result.get('method', 'unknown')}")
            print(f"   Tiempo: {result.get('elapsed_ms', 0)}ms")
            print(f"   Secciones consultadas: {len(result.get('sections_consulted', []))}")
            print()

            if result.get('sections_consulted'):
                print("📄 Secciones consultadas:")
                for section in result.get('sections_consulted', []):
                    print(f"   - {section}")
                print()

            if result.get('response'):
                print("💬 Respuesta generada:")
                print("-" * 80)
                response_text = result['response']
                # Truncar si es muy largo
                if len(response_text) > 500:
                    print(response_text[:500] + "...")
                else:
                    print(response_text)
                print("-" * 80)
                print()

            if result.get('chunks'):
                print(f"📚 Chunks retornados: {len(result['chunks'])}")
                for j, chunk in enumerate(result['chunks'][:2], 1):  # Mostrar solo primeros 2
                    print(f"\n   Chunk {j}:")
                    print(f"   Citation: {chunk.get('citation', 'N/A')}")
                    print(f"   Score: {chunk.get('score', 0)}")
                    print(f"   Reasoning: {chunk.get('reasoning', 'N/A')}")
                    content_preview = chunk.get('content', '')[:150]
                    print(f"   Content: {content_preview}...")
                print()

        except Exception as e:
            print(f"❌ Error en retrieval con índices: {e}")
            import traceback
            traceback.print_exc()

        print()
        print("=" * 80)
        print()

        # Pequeña pausa entre queries
        if i < len(queries):
            await asyncio.sleep(2)


async def demo_comparison():
    """
    Compara retrieval CON índices vs SIN índices.
    """
    print("=" * 80)
    print("COMPARACIÓN: CON ÍNDICES vs SIN ÍNDICES")
    print("=" * 80)
    print()

    # Verificar credenciales
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not Path(creds_path).exists():
        print("❌ Error: GOOGLE_APPLICATION_CREDENTIALS no configurado")
        return

    # Configurar componentes
    project_id = os.getenv("VERTEX_AI_PROJECT", "rosy-sky-364021")
    location = os.getenv("VERTEX_AI_LOCATION", "us-central1")

    model_provider = VertexAIProvider(
        project_id=project_id,
        location=location,
        model_name="gemini-2.0-flash-001"
    )

    document_reader = DocumentReader()
    chunk_evaluator = ChunkEvaluator(model_provider=model_provider)
    retrieval = AgentRetrieval(
        document_reader=document_reader,
        chunk_evaluator=chunk_evaluator
    )

    query = "¿Cómo puedo jubilarme anticipadamente?"

    print(f"📝 Query: {query}")
    print()

    # MÉTODO SIN ÍNDICES
    print("🐢 MÉTODO SIN ÍNDICES (lee documentos completos)")
    print("-" * 80)
    try:
        result_old = await retrieval.retrieve_old(query=query, k=3)
        print(f"   ✅ Completado en {result_old.get('elapsed_ms', 'N/A')}ms")
        print(f"   📚 Chunks: {len(result_old.get('chunks', []))}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        result_old = None

    print()

    # MÉTODO CON ÍNDICES
    print("🚀 MÉTODO CON ÍNDICES (3 fases)")
    print("-" * 80)
    try:
        result_indexed = await retrieval.retrieve_with_index(query=query)
        print(f"   ✅ Completado en {result_indexed.get('elapsed_ms', 0)}ms")
        print(f"   📚 Chunks: {len(result_indexed.get('chunks', []))}")
        print(f"   📄 Secciones: {len(result_indexed.get('sections_consulted', []))}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        result_indexed = None

    print()

    # Comparación
    if result_old and result_indexed:
        print("📊 COMPARACIÓN:")
        print("-" * 80)
        old_time = result_old.get('elapsed_ms', 0)
        new_time = result_indexed.get('elapsed_ms', 0)

        if old_time and new_time:
            speedup = (old_time - new_time) / old_time * 100
            print(f"   Tiempo sin índices: {old_time}ms")
            print(f"   Tiempo con índices: {new_time}ms")
            print(f"   Mejora: {speedup:.1f}% más rápido")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Demo de retrieval con índices")
    parser.add_argument(
        "--mode",
        choices=["demo", "comparison"],
        default="demo",
        help="Modo de ejecución: demo (completo) o comparison (comparar métodos)"
    )

    args = parser.parse_args()

    if args.mode == "comparison":
        asyncio.run(demo_comparison())
    else:
        asyncio.run(demo_indexed_retrieval())
