#!/usr/bin/env python3
"""
Script de Indexación Masiva de Documentos

Indexa todos los PDFs en data/documentos/ usando AgentRAGIndexer.
Genera índices jerárquicos para acelerar el retrieval.

Uso:
    python scripts/index_documents.py
    python scripts/index_documents.py --reindex  # Forzar reindexación
"""

import sys
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Agregar src/ al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Cargar variables de entorno desde la raíz del proyecto
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from src.rag.agent_based.indexer import AgentRAGIndexer
from src.framework.model_provider import VertexAIProvider


class Colors:
    """Colores ANSI para terminal"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Imprime header con formato"""
    width = 60
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'═' * width}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text.center(width-4)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'═' * width}{Colors.END}\n")


def print_box(lines: List[str]):
    """Imprime un box con líneas de texto"""
    width = max(len(line) for line in lines) + 4

    print(f"{Colors.CYAN}╔{'═' * width}╗{Colors.END}")
    for line in lines:
        padding = width - len(line) - 2
        print(f"{Colors.CYAN}║{Colors.END}  {line}{' ' * padding}{Colors.CYAN}║{Colors.END}")
    print(f"{Colors.CYAN}╚{'═' * width}╝{Colors.END}")


def print_progress(current: int, total: int, doc_name: str, status: str = "Processing"):
    """Imprime progreso de indexación"""
    percent = (current / total) * 100 if total > 0 else 0
    bar_length = 30
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_length - filled)

    print(f"\r{Colors.BLUE}[{bar}]{Colors.END} {percent:5.1f}% | "
          f"{Colors.YELLOW}{status}:{Colors.END} {doc_name[:40]:<40}", end='', flush=True)


async def find_pdf_documents(base_path: Path) -> List[Path]:
    """Encuentra todos los PDFs en data/documentos/"""
    pdf_files = list(base_path.rglob("*.pdf"))
    return sorted(pdf_files)


async def index_documents(reindex: bool = False):
    """
    Indexa todos los documentos PDF encontrados.

    Args:
        reindex: Si True, regenera índices existentes
    """
    start_time = time.time()

    print_header("INDEXACIÓN MASIVA DE DOCUMENTOS")

    # Paths
    docs_path = project_root / "data" / "documentos"
    indices_path = project_root / "data" / "indices"

    # Crear directorio de índices si no existe
    indices_path.mkdir(parents=True, exist_ok=True)

    # Buscar PDFs
    print(f"{Colors.CYAN}Buscando documentos PDF...{Colors.END}")
    pdf_files = await find_pdf_documents(docs_path)

    if not pdf_files:
        print(f"{Colors.RED}No se encontraron documentos PDF en {docs_path}{Colors.END}")
        return

    print(f"{Colors.GREEN}Encontrados {len(pdf_files)} documentos{Colors.END}\n")

    # Inicializar indexer
    print(f"{Colors.CYAN}Inicializando AgentRAGIndexer...{Colors.END}")
    model_provider = VertexAIProvider()
    indexer = AgentRAGIndexer(model_provider=model_provider)

    # Contadores
    processed = 0
    generated = 0
    skipped = 0
    errors = 0
    error_details = []

    # Procesar cada documento
    for i, pdf_path in enumerate(pdf_files, 1):
        doc_name = pdf_path.name
        print_progress(i-1, len(pdf_files), doc_name, "Procesando")

        try:
            # Verificar si ya existe índice
            index_file = indices_path / f"{pdf_path.stem}_index.json"

            if index_file.exists() and not reindex:
                print_progress(i, len(pdf_files), doc_name, "Ya indexado")
                processed += 1
                skipped += 1
                time.sleep(0.1)  # Dar tiempo para ver el mensaje
                continue

            # Indexar documento
            print_progress(i-1, len(pdf_files), doc_name, "Indexando")
            index = await indexer.index_document(str(pdf_path), output_dir=str(indices_path))

            if index:
                processed += 1
                generated += 1
                print_progress(i, len(pdf_files), doc_name, "Completado")
            else:
                errors += 1
                error_details.append(f"Error desconocido: {doc_name}")
                print_progress(i, len(pdf_files), doc_name, "Error")

            time.sleep(0.1)  # Dar tiempo para ver el mensaje

        except Exception as e:
            errors += 1
            error_details.append(f"{doc_name}: {str(e)[:60]}")
            print_progress(i, len(pdf_files), doc_name, "Error")
            time.sleep(0.1)

    # Nueva línea después de la barra de progreso
    print("\n")

    # Tiempo total
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    # Reporte final
    print_header("INDEXACIÓN COMPLETA")

    report_lines = [
        f"Documentos procesados: {Colors.GREEN}{processed}{Colors.END}",
        f"Índices generados: {Colors.GREEN}{generated}{Colors.END}",
        f"Índices existentes (omitidos): {Colors.YELLOW}{skipped}{Colors.END}",
        f"Errores: {Colors.RED}{errors}{Colors.END}",
        f"Tiempo total: {Colors.CYAN}{minutes}m {seconds}s{Colors.END}"
    ]

    print_box(report_lines)

    # Mostrar detalles de errores si los hay
    if error_details:
        print(f"\n{Colors.RED}{Colors.BOLD}Detalles de errores:{Colors.END}")
        for error in error_details:
            print(f"  {Colors.RED}•{Colors.END} {error}")

    # Información adicional
    print(f"\n{Colors.CYAN}Índices guardados en:{Colors.END} {indices_path}")
    print(f"{Colors.CYAN}Uso:{Colors.END} Los índices se cargarán automáticamente en AgentRetrieval\n")


def main():
    """Punto de entrada del script"""
    # Parsear argumentos
    reindex = '--reindex' in sys.argv or '-r' in sys.argv

    if reindex:
        print(f"{Colors.YELLOW}Modo reindexación: Se regenerarán todos los índices{Colors.END}\n")

    # Ejecutar indexación
    asyncio.run(index_documents(reindex=reindex))


if __name__ == "__main__":
    main()
