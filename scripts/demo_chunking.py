"""
Demostración didáctica de cómo funciona el chunking en Vector RAG

Este script muestra visualmente:
1. Cómo un documento se divide en chunks
2. El tamaño de cada chunk
3. El overlap entre chunks
4. Cómo se ven los embeddings (vectores)

PEDAGOGÍA:
- Los participantes pueden ver exactamente cómo se procesa un documento
- Entender por qué el chunking es importante (contexto vs tamaño)
- Ver la diferencia entre Vector RAG (chunks) y Agent RAG (documento completo)
"""

import asyncio
from pathlib import Path
from typing import List
import numpy as np


# ============================================================================
# Colores ANSI para terminal
# ============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# ============================================================================
# Demostración de Chunking
# ============================================================================

def read_sample_document() -> str:
    """Lee un documento de ejemplo de data/documentos/"""
    docs_path = Path("data/documentos")

    # Buscar el primer archivo .md
    for md_file in docs_path.rglob("*.md"):
        return md_file.read_text(encoding="utf-8")

    # Si no hay documentos, usar texto de ejemplo
    return """
**PROCEDIMIENTO**: Jubilación Anticipada
**CÓDIGO**: PROC-JUB-002
**VERSIÓN**: 1.0
**FECHA**: 2024-11-01

## OBJETIVO
Este procedimiento describe los pasos para tramitar una jubilación anticipada en AFP Integra.

## REQUISITOS PREVIOS
- Ser menor a la edad legal de jubilación
- Tener un saldo mínimo de CLP $150.000.000
- La pensión calculada debe ser al menos el 150% de la PBS

## PASOS DEL PROCEDIMIENTO

### 1. Solicitud de Simulación
El afiliado debe solicitar una simulación de pensión anticipada.

### 2. Evaluación de Viabilidad
El sistema evaluará automáticamente si cumple los requisitos.

### 3. Asesoría Obligatoria
Si es viable, debe asistir a una sesión de asesoría.

### 4. Confirmación de Decisión
Firmar el documento de consentimiento informado.

### 5. Tramitación
Procesamiento y emisión de la resolución.
"""


def simple_chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Divide texto en chunks con overlap.

    PEDAGOGÍA:
    - chunk_size: cuántos caracteres por chunk
    - overlap: cuántos caracteres se repiten entre chunks (para mantener contexto)
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        # Mover inicio con overlap
        start = end - overlap

        if end >= len(text):
            break

    return chunks


def visualize_chunking(text: str, chunk_size: int = 512, overlap: int = 50):
    """Visualiza cómo se divide un documento en chunks"""

    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}DEMOSTRACIÓN: CHUNKING EN VECTOR RAG{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    # Información del documento original
    print(f"{Colors.CYAN}📄 DOCUMENTO ORIGINAL:{Colors.ENDC}")
    print(f"   Longitud: {Colors.BOLD}{len(text)}{Colors.ENDC} caracteres")
    print(f"   Palabras: ~{len(text.split())} palabras\n")

    # Configuración de chunking
    print(f"{Colors.CYAN}⚙️  CONFIGURACIÓN DE CHUNKING:{Colors.ENDC}")
    print(f"   Tamaño de chunk: {Colors.BOLD}{chunk_size}{Colors.ENDC} caracteres")
    print(f"   Overlap: {Colors.BOLD}{overlap}{Colors.ENDC} caracteres")
    print(f"   {Colors.YELLOW}(El overlap mantiene contexto entre chunks){Colors.ENDC}\n")

    # Crear chunks
    chunks = simple_chunk_text(text, chunk_size, overlap)

    print(f"{Colors.CYAN}📊 RESULTADO:{Colors.ENDC}")
    print(f"   Total de chunks: {Colors.BOLD}{len(chunks)}{Colors.ENDC}\n")

    # Mostrar cada chunk
    for idx, chunk in enumerate(chunks, 1):
        print(f"{Colors.GREEN}{'─'*80}{Colors.ENDC}")
        print(f"{Colors.GREEN}{Colors.BOLD}CHUNK {idx} de {len(chunks)}{Colors.ENDC}")
        print(f"{Colors.GREEN}{'─'*80}{Colors.ENDC}")
        print(f"Longitud: {len(chunk)} caracteres\n")

        # Mostrar preview del chunk (primeros 200 chars)
        preview = chunk[:200].strip()
        if len(chunk) > 200:
            preview += f"... {Colors.YELLOW}[+{len(chunk)-200} caracteres más]{Colors.ENDC}"

        print(preview)
        print()

        # Mostrar overlap con chunk anterior
        if idx > 1:
            prev_chunk = chunks[idx-2]
            overlap_start = len(prev_chunk) - overlap
            overlapped_text = prev_chunk[overlap_start:]

            if overlapped_text in chunk:
                print(f"{Colors.YELLOW}🔗 OVERLAP con chunk anterior:{Colors.ENDC}")
                print(f'   "{overlapped_text[:50]}..."')
                print()

    print(f"{Colors.GREEN}{'─'*80}{Colors.ENDC}\n")


def visualize_embeddings(chunks: List[str]):
    """Muestra cómo se ven los embeddings (vectores numéricos)"""

    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}DEMOSTRACIÓN: EMBEDDINGS (VECTORES){Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    print(f"{Colors.CYAN}🧮 ¿QUÉ SON LOS EMBEDDINGS?{Colors.ENDC}")
    print("   Los embeddings son representaciones numéricas del significado del texto.")
    print("   Cada chunk se convierte en un vector de 768 números (dimensiones).")
    print("   Textos similares → vectores cercanos en el espacio vectorial.\n")

    # Simular embeddings (en realidad estos serían generados por el modelo)
    print(f"{Colors.CYAN}📐 EJEMPLO DE EMBEDDING (simulado):{Colors.ENDC}\n")

    for idx, chunk in enumerate(chunks[:2], 1):  # Solo primeros 2 para no saturar
        # Generar embedding fake (números aleatorios)
        fake_embedding = np.random.randn(768)  # 768 dimensiones

        print(f"{Colors.GREEN}Chunk {idx}:{Colors.ENDC} \"{chunk[:50]}...\"")
        print(f"{Colors.BLUE}Embedding (primeras 10 dimensiones de 768):{Colors.ENDC}")
        print(f"   [{', '.join([f'{x:.4f}' for x in fake_embedding[:10]])}...]")
        print(f"   {Colors.YELLOW}... [758 dimensiones más]{Colors.ENDC}")

        # Magnitud del vector (norma L2)
        magnitude = np.linalg.norm(fake_embedding)
        print(f"   Magnitud: {magnitude:.4f}\n")

    print(f"{Colors.CYAN}🔍 SIMILITUD COSENO:{Colors.ENDC}")
    print("   Para encontrar chunks relevantes, calculamos la similitud coseno")
    print("   entre el embedding de la query y los embeddings de los chunks.")
    print("   Valores cercanos a 1 = muy similar, cercanos a 0 = no relacionado.\n")


def compare_vector_vs_agent_rag(text: str):
    """Compara Vector RAG vs Agent RAG visualmente"""

    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}COMPARACIÓN: VECTOR RAG vs AGENT RAG{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    chunks = simple_chunk_text(text, chunk_size=512, overlap=50)

    print(f"{Colors.BLUE}{Colors.BOLD}📊 VECTOR RAG:{Colors.ENDC}")
    print(f"   ✓ Divide documento en {len(chunks)} chunks pequeños")
    print(f"   ✓ Genera embedding para cada chunk (768 dimensiones)")
    print(f"   ✓ Almacena en base de datos vectorial (PostgreSQL + pgvector)")
    print(f"   ✓ Búsqueda: similitud coseno entre embeddings")
    print(f"   {Colors.GREEN}Ventajas:{Colors.ENDC} Rápido, escala bien, barato")
    print(f"   {Colors.RED}Desventajas:{Colors.ENDC} Opaco (no explica por qué es relevante)\n")

    print(f"{Colors.CYAN}{Colors.BOLD}🤖 AGENT RAG:{Colors.ENDC}")
    print(f"   ✓ Lee documento COMPLETO (sin dividir en chunks)")
    print(f"   ✓ LLM evalúa relevancia y explica el 'por qué'")
    print(f"   ✓ No requiere embeddings ni base de datos vectorial")
    print(f"   ✓ Búsqueda: el LLM lee y juzga cada documento")
    print(f"   {Colors.GREEN}Ventajas:{Colors.ENDC} Transparente, explica razonamiento")
    print(f"   {Colors.RED}Desventajas:{Colors.ENDC} Lento, costoso, no escala a miles de docs\n")

    print(f"{Colors.YELLOW}💡 CUÁNDO USAR CADA UNO:{Colors.ENDC}")
    print(f"   Vector RAG → Miles de documentos, necesitas velocidad")
    print(f"   Agent RAG → Pocos documentos (<100), necesitas explicabilidad\n")


# ============================================================================
# Main
# ============================================================================

def main():
    """Ejecuta todas las demostraciones"""

    print(f"\n{Colors.BOLD}{'='*80}")
    print("🎓 DEMO DIDÁCTICA: CHUNKING Y EMBEDDINGS EN RAG")
    print(f"{'='*80}{Colors.ENDC}\n")

    # Leer documento de ejemplo
    document_text = read_sample_document()

    # 1. Demostración de chunking
    visualize_chunking(document_text, chunk_size=512, overlap=50)

    # 2. Demostración de embeddings
    chunks = simple_chunk_text(document_text, chunk_size=512, overlap=50)
    visualize_embeddings(chunks)

    # 3. Comparación Vector RAG vs Agent RAG
    compare_vector_vs_agent_rag(document_text)

    # Resumen final
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}📚 RESUMEN PEDAGÓGICO{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    print("1. CHUNKING: Divide documentos largos en fragmentos manejables")
    print("   - Permite procesar documentos más grandes que el context window del LLM")
    print("   - El overlap mantiene coherencia entre chunks\n")

    print("2. EMBEDDINGS: Convierten texto en números que representan el significado")
    print("   - 768 dimensiones capturan relaciones semánticas complejas")
    print("   - Similitud coseno = medida de relevancia\n")

    print("3. VECTOR RAG: Rápido, opaco, escalable")
    print("4. AGENT RAG: Lento, transparente, limitado\n")

    print(f"{Colors.GREEN}✅ Demo completada!{Colors.ENDC}\n")


if __name__ == "__main__":
    main()
