"""
Demostración de soporte multi-formato en Agent RAG

Este script muestra cómo el DocumentReader refactorizado:
1. Lee múltiples formatos: .md, .pdf, .txt, .docx
2. Extrae metadata con fallbacks inteligentes
3. No depende de estructura específica de headers
4. Funciona incluso si agregas PDFs sin modificar código

PEDAGOGÍA:
- Los participantes ven que pueden agregar PDFs sin romper nada
- Metadata se infiere inteligentemente del path y contenido
- Sistema robusto y extensible
"""

import asyncio
from pathlib import Path
import sys

# Agregar src al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.agent_based.document_reader import DocumentReader


# ============================================================================
# Colores para terminal
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


# ============================================================================
# Demostración
# ============================================================================

async def demo_multi_format_support():
    """Demuestra el soporte multi-formato del DocumentReader"""

    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}DEMO: SOPORTE MULTI-FORMATO EN AGENT RAG{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    reader = DocumentReader()

    # Leer todos los documentos
    print(f"{Colors.CYAN}📂 Leyendo documentos de data/documentos/...{Colors.ENDC}\n")

    try:
        documents = await reader.read_all_documents("data/documentos")
    except FileNotFoundError:
        print(f"{Colors.RED}❌ Error: directorio data/documentos/ no existe{Colors.ENDC}")
        print("   Crea algunos archivos de prueba primero.\n")
        return

    if not documents:
        print(f"{Colors.YELLOW}⚠️  No se encontraron documentos en data/documentos/{Colors.ENDC}\n")
        return

    # Agrupar por formato
    by_format = {}
    for doc in documents:
        fmt = doc["metadata"]["format"]
        if fmt not in by_format:
            by_format[fmt] = []
        by_format[fmt].append(doc)

    # Mostrar resumen
    print(f"{Colors.GREEN}✅ Documentos encontrados: {len(documents)}{Colors.ENDC}\n")
    print(f"{Colors.CYAN}📊 Por formato:{Colors.ENDC}")
    for fmt, docs in sorted(by_format.items()):
        count = len(docs)
        print(f"   {fmt:6s} → {count:2d} documento(s)")
    print()

    # Mostrar detalles de cada documento
    print(f"{Colors.HEADER}{'─'*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}DETALLES DE CADA DOCUMENTO{Colors.ENDC}")
    print(f"{Colors.HEADER}{'─'*80}{Colors.ENDC}\n")

    for idx, doc in enumerate(documents, 1):
        metadata = doc["metadata"]
        content_preview = doc["content"][:200].replace("\n", " ").strip()

        print(f"{Colors.GREEN}{Colors.BOLD}Documento {idx} de {len(documents)}{Colors.ENDC}")
        print(f"{Colors.GREEN}{'─'*80}{Colors.ENDC}")

        # Metadata
        print(f"{Colors.CYAN}ID:{Colors.ENDC} {doc['id']}")
        print(f"{Colors.CYAN}Formato:{Colors.ENDC} {metadata['format']}")
        print(f"{Colors.CYAN}Fuente:{Colors.ENDC} {metadata['source']}")
        print(f"{Colors.CYAN}Categoría:{Colors.ENDC} {metadata['category']}")
        print(f"{Colors.CYAN}Código:{Colors.ENDC} {metadata.get('procedure_code', 'N/A')}")
        print(f"{Colors.CYAN}Nombre:{Colors.ENDC} {metadata.get('procedure_name', 'N/A')}")

        if metadata.get('version'):
            print(f"{Colors.CYAN}Versión:{Colors.ENDC} {metadata['version']}")
        if metadata.get('date'):
            print(f"{Colors.CYAN}Fecha:{Colors.ENDC} {metadata['date']}")

        # Preview del contenido
        print(f"\n{Colors.YELLOW}Preview:{Colors.ENDC}")
        print(f'"{content_preview}..."')

        # Tamaño
        content_len = len(doc["content"])
        words = len(doc["content"].split())
        print(f"\n{Colors.YELLOW}Tamaño:{Colors.ENDC} {content_len} caracteres, ~{words} palabras")

        print()

    # Explicación pedagógica
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}💡 VENTAJAS DEL SISTEMA ROBUSTO{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    print(f"{Colors.GREEN}✅ Soporte multi-formato:{Colors.ENDC}")
    print("   - Puedes agregar PDFs, DOCX, TXT sin modificar código")
    print("   - El sistema detecta el formato automáticamente\n")

    print(f"{Colors.GREEN}✅ Extracción inteligente de metadata:{Colors.ENDC}")
    print("   - Busca headers explícitos (PROCEDIMIENTO:, CÓDIGO:, etc.)")
    print("   - Si no encuentra, infiere del nombre de archivo")
    print("   - Categoría se infiere del path (carpeta parent)\n")

    print(f"{Colors.GREEN}✅ Fallbacks robustos:{Colors.ENDC}")
    print("   - Si falta procedure_code → usa nombre de archivo normalizado")
    print("   - Si falta procedure_name → busca primer título o humaniza nombre")
    print("   - Nunca falla por falta de headers específicos\n")

    print(f"{Colors.GREEN}✅ Extensible:{Colors.ENDC}")
    print("   - Agregar nuevo formato = agregar método _read_xxx()")
    print("   - Ejemplo: para Excel, agregar _read_xlsx() con pandas\n")


async def demo_metadata_inference():
    """Demuestra cómo se infiere metadata inteligentemente"""

    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}DEMO: INFERENCIA INTELIGENTE DE METADATA{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    reader = DocumentReader()

    # Ejemplos de inferencia
    examples = [
        ("proc-jub-002.md", "data/documentos/jubilacion"),
        ("Jubilacion_Anticipada.pdf", "data/documentos/jubilacion"),
        ("documento-sin-headers.txt", "data/documentos/general"),
        ("AFILIACION-NUEVO-TRABAJADOR.docx", "data/documentos/afiliacion"),
    ]

    print(f"{Colors.CYAN}🧠 EJEMPLOS DE INFERENCIA:{Colors.ENDC}\n")

    for filename, category_path in examples:
        file_path = Path(category_path) / filename

        # Simular inferencia
        inferred_code = reader._infer_procedure_code(file_path)
        inferred_category = reader._infer_category(file_path)
        inferred_name = reader._infer_procedure_name("", file_path)  # Sin contenido

        print(f"{Colors.GREEN}Archivo:{Colors.ENDC} {filename}")
        print(f"  Path: {category_path}/")
        print(f"  {Colors.YELLOW}→{Colors.ENDC} Código inferido: {Colors.BOLD}{inferred_code}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}→{Colors.ENDC} Categoría inferida: {Colors.BOLD}{inferred_category}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}→{Colors.ENDC} Nombre inferido: {Colors.BOLD}{inferred_name}{Colors.ENDC}")
        print()

    print(f"{Colors.CYAN}💡 CONCLUSIÓN:{Colors.ENDC}")
    print("   Incluso sin headers explícitos en el contenido,")
    print("   el sistema puede inferir metadata razonable del filesystem.\n")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Ejecuta todas las demos"""

    print(f"\n{Colors.BOLD}{'='*80}")
    print("🎓 DEMO: DOCUMENT READER ROBUSTO Y EXTENSIBLE")
    print(f"{'='*80}{Colors.ENDC}\n")

    # Demo 1: Soporte multi-formato
    await demo_multi_format_support()

    # Demo 2: Inferencia de metadata
    await demo_metadata_inference()

    # Resumen final
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}📚 RESUMEN PEDAGÓGICO{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    print("1. ROBUSTEZ: No depende de formato específico de headers")
    print("2. FLEXIBILIDAD: Soporta múltiples formatos out-of-the-box")
    print("3. INTELIGENCIA: Infiere metadata del filesystem y contenido")
    print("4. EXTENSIBILIDAD: Fácil agregar nuevos formatos")
    print()
    print(f"{Colors.GREEN}✅ Puedes agregar PDFs y otros formatos sin modificar código!{Colors.ENDC}\n")


if __name__ == "__main__":
    asyncio.run(main())
