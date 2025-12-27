"""
Script de demo para probar la API REST del Agente Asistente

Este script demuestra cómo consumir la API desde un cliente Python.
También sirve como ejemplo de integración para frontends.

PEDAGOGÍA:
- Muestra cómo llamar al endpoint /api/v1/asistente/chat
- Demuestra el formato de request/response
- Renderiza checklist y citas en consola

USO:
    1. Iniciar la API: uvicorn src.api.main:app --reload
    2. Ejecutar este script: python scripts/demo_api.py
"""

import asyncio
import httpx
import json
from typing import Dict, Any


# ============================================================================
# Configuración
# ============================================================================

API_BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{API_BASE_URL}/api/v1/asistente/chat"


# ============================================================================
# Cliente de API
# ============================================================================

async def call_asistente_api(
    query: str,
    session_id: str = "demo-session-001",
    use_agentic_rag: bool = False
) -> Dict[str, Any]:
    """
    Llama al endpoint de chat del Agente Asistente.

    Args:
        query: Pregunta del usuario
        session_id: ID de sesión
        use_agentic_rag: Si True, usa Agent RAG; si False, usa Vector RAG

    Returns:
        Dict con la respuesta completa del API
    """
    payload = {
        "query": query,
        "session_id": session_id,
        "use_agentic_rag": use_agentic_rag
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(API_ENDPOINT, json=payload)
        response.raise_for_status()
        return response.json()


# ============================================================================
# Renderizado de respuesta en consola
# ============================================================================

def render_response(response: Dict[str, Any]):
    """
    Renderiza la respuesta de la API en consola de forma legible.

    PEDAGOGÍA:
    Este renderizado simula cómo un frontend real mostraría:
    - Texto de respuesta
    - Checklist interactivo
    - Citas con enlaces
    """
    print("\n" + "=" * 80)
    print("RESPUESTA DEL AGENTE ASISTENTE")
    print("=" * 80)

    # 1. Contenido principal
    print("\n📝 RESPUESTA:\n")
    print(response["content"])

    # 2. Checklist (si existe)
    if response.get("checklist"):
        checklist = response["checklist"]
        print("\n" + "=" * 80)
        print(f"✅ CHECKLIST: {checklist['title']}")
        print(f"   Código: {checklist['procedure_code']}")
        print("=" * 80)

        for step in checklist["steps"]:
            checkbox = "☐"
            print(f"\n{checkbox} {step['step_number']}. {step['action']}")
            if step["required_documents"]:
                print(f"   📄 Documentos requeridos:")
                for doc in step["required_documents"]:
                    print(f"      - {doc}")

        print(f"\n⏱️  Tiempo estimado: {checklist.get('estimated_time', 'N/A')}")
        print(f"⚡ SLA: {checklist.get('sla', 'N/A')}")
        print(f"📊 Progreso: {checklist.get('progress_percentage', 0)}%")

    # 3. Citas (si existen)
    if response.get("citations"):
        print("\n" + "=" * 80)
        print("📚 FUENTES:")
        print("=" * 80)

        for idx, citation in enumerate(response["citations"], 1):
            score_pct = int(citation["score"] * 100)
            print(f"\n{idx}. {citation['text']}")
            print(f"   🔗 URL: {citation['url']}")
            print(f"   📄 Documento: {citation['document_id']}, página {citation['page']}")
            print(f"   📊 Relevancia: {score_pct}%")

    # 4. Metadata
    print("\n" + "=" * 80)
    print("ℹ️  METADATA")
    print("=" * 80)
    print(f"Método RAG: {response.get('retrieval_method', 'N/A')}")
    print(f"Confianza: {response.get('confidence_score', 0):.2%}")
    print(f"Tiempo de procesamiento: {response.get('processing_time_ms', 0)}ms")
    print(f"Chunks usados: {response.get('chunks_used', 0)}")
    print(f"Timestamp: {response.get('timestamp', 'N/A')}")
    print("=" * 80 + "\n")


# ============================================================================
# Ejemplos de uso
# ============================================================================

async def demo_basic_query():
    """Demo 1: Consulta básica sin checklist"""
    print("\n🔵 DEMO 1: Consulta básica")
    print("Query: ¿Qué es una AFP?\n")

    response = await call_asistente_api(
        query="¿Qué es una AFP?",
        use_agentic_rag=False  # Vector RAG (rápido)
    )

    render_response(response)


async def demo_checklist_query():
    """Demo 2: Consulta que genera checklist"""
    print("\n🟢 DEMO 2: Consulta con checklist")
    print("Query: ¿Cómo puedo jubilarme anticipadamente?\n")

    response = await call_asistente_api(
        query="¿Cómo puedo jubilarme anticipadamente?",
        use_agentic_rag=False  # Vector RAG
    )

    render_response(response)


async def demo_agentic_rag():
    """Demo 3: Misma query con Agent RAG (LLM evalúa relevancia)"""
    print("\n🟣 DEMO 3: Consulta con Agent RAG")
    print("Query: ¿Cómo tramitar un traspaso de AFP?\n")

    response = await call_asistente_api(
        query="¿Cómo tramitar un traspaso de AFP?",
        use_agentic_rag=True  # Agent RAG (lento pero transparente)
    )

    render_response(response)


async def demo_comparison():
    """Demo 4: Comparación Vector RAG vs Agent RAG"""
    print("\n🔴 DEMO 4: Comparación de métodos RAG")

    query = "¿Qué requisitos necesito para afiliarme?"

    # Vector RAG
    print("\n--- Vector RAG ---")
    response_vector = await call_asistente_api(
        query=query,
        use_agentic_rag=False
    )
    print(f"⏱️  Tiempo: {response_vector['processing_time_ms']}ms")
    print(f"📊 Confianza: {response_vector.get('confidence_score', 0):.2%}")

    # Agent RAG
    print("\n--- Agent RAG ---")
    response_agent = await call_asistente_api(
        query=query,
        use_agentic_rag=True
    )
    print(f"⏱️  Tiempo: {response_agent['processing_time_ms']}ms")
    print(f"📊 Confianza: {response_agent.get('confidence_score', 0):.2%}")

    # Comparación
    speedup = response_agent['processing_time_ms'] / response_vector['processing_time_ms']
    print(f"\n⚡ Vector RAG es {speedup:.1f}x más rápido que Agent RAG")


async def demo_health_check():
    """Demo 5: Health check del API"""
    print("\n🟡 DEMO 5: Health Check")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))


# ============================================================================
# Main
# ============================================================================

async def main():
    """
    Ejecuta todos los demos en secuencia.

    PEDAGOGÍA:
    - Demo 1: Muestra respuesta básica sin checklist
    - Demo 2: Muestra checklist estructurado
    - Demo 3: Muestra Agent RAG con reasoning
    - Demo 4: Compara performance Vector vs Agent RAG
    - Demo 5: Health check
    """
    print("=" * 80)
    print("DEMO: API REST del Agente Asistente de Procedimientos AFP")
    print("=" * 80)

    try:
        # Verificar que la API esté corriendo
        await demo_health_check()

        # Ejecutar demos
        await demo_basic_query()
        await demo_checklist_query()
        await demo_agentic_rag()
        await demo_comparison()

        print("\n✅ Demos completados exitosamente!")

    except httpx.ConnectError:
        print("\n❌ Error: No se pudo conectar a la API.")
        print("   Asegúrate de que el servidor esté corriendo:")
        print("   uvicorn src.api.main:app --reload")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
