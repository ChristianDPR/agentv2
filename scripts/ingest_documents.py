#!/usr/bin/env python3
"""
Script de ejemplo para ingesta completa de documentos con Vector RAG

Este script demuestra cómo usar el pipeline completo:
1. Carga documentos (MD y PDF)
2. Hace chunking con overlap
3. Genera embeddings con Vertex AI
4. Almacena en PostgreSQL con pgvector

Uso:
    python scripts/ingest_documents.py --path data/documentos --chunk-size 512 --overlap 50
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Agregar src/ al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Cargar variables de entorno desde la raíz del proyecto
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from src.rag.vector_based.ingestion import DocumentIngestion
from src.rag.vector_based.embeddings import EmbeddingGenerator
from src.rag.vector_based.vector_store import VectorStore

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main(
    path: str,
    chunk_size: int = 512,
    overlap: int = 50,
    batch_size: int = 250
):
    """
    Pipeline completo de ingesta de documentos.

    Args:
        path: Directorio con documentos (MD y/o PDF)
        chunk_size: Tamaño máximo del chunk en caracteres
        overlap: Caracteres de superposición entre chunks
        batch_size: Tamaño del batch para embeddings
    """
    logger.info("=" * 80)
    logger.info("INICIANDO PIPELINE DE INGESTA - VECTOR RAG")
    logger.info("=" * 80)

    try:
        # 1. Inicializar componentes
        logger.info("\n[1/5] Inicializando componentes...")

        embedding_generator = EmbeddingGenerator()
        logger.info("  ✓ EmbeddingGenerator inicializado")

        vector_store = VectorStore()
        await vector_store.connect()
        logger.info("  ✓ VectorStore conectado")

        ingestion = DocumentIngestion(
            embedding_generator=embedding_generator,
            vector_store=vector_store
        )
        logger.info("  ✓ DocumentIngestion inicializado")

        # 2. Ejecutar pipeline completo
        logger.info(f"\n[2/5] Ejecutando pipeline de ingesta desde: {path}")
        stats = await ingestion.ingest_and_embed(
            path=path,
            chunk_size=chunk_size,
            overlap=overlap,
            batch_size=batch_size
        )

        # 3. Mostrar estadísticas
        logger.info("\n[3/5] Estadísticas del proceso:")
        logger.info(f"  • Documentos procesados: {stats['total_documents']}")
        logger.info(f"  • Chunks generados: {stats['total_chunks']}")
        logger.info(f"  • Embeddings creados: {stats['total_embeddings']}")
        logger.info(f"  • Chunk size: {stats['chunk_size']} caracteres")
        logger.info(f"  • Overlap: {stats['overlap']} caracteres")
        logger.info(f"  • Status: {stats['status']}")

        # 4. Obtener estadísticas de la base de datos
        logger.info("\n[4/5] Estadísticas de la base de datos:")
        db_stats = await vector_store.get_statistics()
        logger.info(f"  • Total chunks en DB: {db_stats['total_chunks']}")
        logger.info("  • Chunks por categoría:")
        for cat in db_stats['chunks_by_category']:
            logger.info(f"    - {cat['category']}: {cat['count']} chunks")

        # 5. Cleanup
        logger.info("\n[5/5] Cerrando conexiones...")
        await vector_store.close()
        logger.info("  ✓ Conexiones cerradas")

        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE COMPLETADO EXITOSAMENTE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ Error en el pipeline: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingesta de documentos con Vector RAG"
    )
    parser.add_argument(
        "--path",
        type=str,
        default="data/documentos",
        help="Directorio con documentos (MD y/o PDF) (default: data/documentos)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Tamaño máximo del chunk en caracteres (default: 512)"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Caracteres de superposición entre chunks (default: 50)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Tamaño del batch para embeddings (default: 50, reducido para evitar límites de tokens)"
    )

    args = parser.parse_args()

    # Validar que el path existe
    if not Path(args.path).exists():
        logger.error(f"❌ El directorio no existe: {args.path}")
        sys.exit(1)

    # Ejecutar pipeline
    asyncio.run(main(
        path=args.path,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        batch_size=args.batch_size
    ))
