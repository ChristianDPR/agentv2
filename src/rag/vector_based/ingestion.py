"""
Ingesta y procesamiento de documentos Markdown y PDF para Vector RAG

Este módulo carga documentos, los divide en chunks con overlap,
genera embeddings y los almacena en el vector store.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class DocumentIngestion:
    """
    Carga y procesa documentos Markdown y PDF.

    PEDAGOGÍA:
    - Chunking = dividir documentos largos en fragmentos procesables
    - Overlap = chunks comparten texto para preservar contexto
    - Metadata = información adicional (categoría, source, etc.)
    """

    def __init__(
        self,
        embedding_generator=None,
        vector_store=None
    ):
        """
        Args:
            embedding_generator: Instancia de EmbeddingGenerator (opcional)
            vector_store: Instancia de VectorStore (opcional)
        """
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store

    async def load_documents(self, path: str) -> List[Dict[str, Any]]:
        """
        Carga todos los documentos .md y .pdf de un directorio.

        PEDAGOGÍA:
        - Soporta MD y PDF con el mismo método
        - MD se lee como texto plano
        - PDF se extrae con PyMuPDF (fitz)

        Args:
            path: Ruta al directorio de documentos

        Returns:
            Lista de dicts con content y metadata
        """
        docs_path = Path(path)
        if not docs_path.exists():
            raise FileNotFoundError(f"Directorio no existe: {path}")

        documents = []

        # Recorrer todos los .md recursivamente
        for md_file in docs_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")

                # Extraer metadata del archivo
                metadata = self._extract_metadata(content, md_file)

                documents.append({
                    "content": content,
                    "metadata": metadata
                })
                logger.info(f"Cargado MD: {md_file.name}")
            except Exception as e:
                logger.error(f"Error cargando MD {md_file}: {e}")

        # Recorrer todos los .pdf recursivamente
        for pdf_file in docs_path.rglob("*.pdf"):
            try:
                content = self._extract_pdf_text(pdf_file)

                # Extraer metadata del PDF
                metadata = self._extract_pdf_metadata(pdf_file)

                documents.append({
                    "content": content,
                    "metadata": metadata
                })
                logger.info(f"Cargado PDF: {pdf_file.name}")
            except Exception as e:
                logger.error(f"Error cargando PDF {pdf_file}: {e}")

        logger.info(f"Total documentos cargados: {len(documents)}")
        return documents

    def chunk_document(
        self,
        doc: Dict[str, Any],
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Divide un documento en chunks con overlap.

        PEDAGOGÍA:
        - chunk_size = longitud máxima del chunk (en caracteres)
        - overlap = cuántos caracteres compartir entre chunks
        - ¿Por qué overlap? Para preservar contexto entre chunks
          Ejemplo: "...edad mínima 65 años" → siguiente chunk empieza en "65 años..."

        Args:
            doc: Documento con content y metadata
            chunk_size: Tamaño máximo del chunk
            overlap: Caracteres de superposición

        Returns:
            Lista de chunks con content y metadata
        """
        content = doc["content"]
        metadata = doc["metadata"]

        chunks = []
        start = 0

        while start < len(content):
            # Calcular fin del chunk
            end = start + chunk_size

            # Extraer chunk
            chunk_text = content[start:end]

            # Crear chunk con metadata heredada
            chunks.append({
                "content": chunk_text.strip(),
                "metadata": {
                    **metadata,
                    "chunk_index": len(chunks),
                    "start_char": start,
                    "end_char": min(end, len(content))
                }
            })

            # Avanzar con overlap
            start += chunk_size - overlap

        return chunks

    async def ingest_and_embed(
        self,
        path: str,
        chunk_size: int = 512,
        overlap: int = 50,
        batch_size: int = 250
    ) -> Dict[str, Any]:
        """
        Pipeline completo de ingesta:
        1. Carga documentos (MD y PDF)
        2. Hace chunking con overlap
        3. Genera embeddings
        4. Almacena en vector store

        PEDAGOGÍA:
        - Este es el método "todo-en-uno" del pipeline RAG
        - Los participantes llaman solo este método para ingestar
        - Internamente coordina load → chunk → embed → store

        Args:
            path: Directorio con documentos
            chunk_size: Tamaño máximo del chunk
            overlap: Caracteres de superposición
            batch_size: Tamaño del batch para embeddings

        Returns:
            Dict con estadísticas del proceso
        """
        if not self.embedding_generator:
            raise ValueError("EmbeddingGenerator requerido para ingest_and_embed()")
        if not self.vector_store:
            raise ValueError("VectorStore requerido para ingest_and_embed()")

        logger.info(f"Iniciando ingesta desde: {path}")

        # 1. Cargar documentos
        documents = await self.load_documents(path)
        logger.info(f"Documentos cargados: {len(documents)}")

        # 2. Hacer chunking
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_document(doc, chunk_size, overlap)
            all_chunks.extend(chunks)
        logger.info(f"Chunks generados: {len(all_chunks)}")

        # 3. Generar embeddings
        texts = [chunk["content"] for chunk in all_chunks]
        try:
            embeddings = await self.embedding_generator.generate_embeddings(
                texts,
                batch_size=batch_size
            )
            logger.info(f"Embeddings generados: {len(embeddings)}")
        except Exception as e:
            logger.error(f"Error generando embeddings: {e}")
            raise

        # 4. Asociar embeddings a chunks
        for chunk, embedding in zip(all_chunks, embeddings):
            chunk["embedding"] = embedding

        # 5. Almacenar en vector store
        try:
            await self.vector_store.upsert_chunks(all_chunks)
            logger.info(f"Chunks almacenados en vector store: {len(all_chunks)}")
        except Exception as e:
            logger.error(f"Error almacenando en vector store: {e}")
            raise

        # 6. Retornar estadísticas
        return {
            "total_documents": len(documents),
            "total_chunks": len(all_chunks),
            "total_embeddings": len(embeddings),
            "chunk_size": chunk_size,
            "overlap": overlap,
            "status": "success"
        }

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """
        Extrae texto de un PDF usando PyMuPDF.

        PEDAGOGÍA:
        - PyMuPDF (fitz) es más rápido y confiable que pdfplumber
        - Extrae texto página por página
        - Preserva estructura básica del texto

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Texto completo del PDF
        """
        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Página {page_num + 1} ---\n{text}")

            doc.close()
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"Error extrayendo texto de PDF {pdf_path}: {e}")
            raise

    def _extract_pdf_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extrae metadata de un PDF usando PyMuPDF.

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Dict con metadata
        """
        metadata = {
            "source": pdf_path.name,
            "category": pdf_path.parent.name,
            "path": str(pdf_path),
            "type": "pdf"
        }

        try:
            doc = fitz.open(pdf_path)

            # Extraer metadata del PDF si existe
            pdf_metadata = doc.metadata
            if pdf_metadata:
                if pdf_metadata.get("title"):
                    metadata["title"] = pdf_metadata["title"]
                if pdf_metadata.get("author"):
                    metadata["author"] = pdf_metadata["author"]
                if pdf_metadata.get("subject"):
                    metadata["subject"] = pdf_metadata["subject"]

            # Número de páginas
            metadata["page_count"] = len(doc)

            doc.close()

        except Exception as e:
            logger.error(f"Error extrayendo metadata de PDF {pdf_path}: {e}")

        return metadata

    def _extract_metadata(self, content: str, file_path: Path) -> Dict[str, Any]:
        """
        Extrae metadata del contenido y path del archivo.

        Busca patrones en el Markdown:
        - # PROCEDIMIENTO: xxx
        - **CÓDIGO**: xxx (formato Markdown con negrita)
        - CATEGORÍA: xxx (del path)
        """
        metadata = {
            "source": file_path.name,
            "category": file_path.parent.name,
            "path": str(file_path),
            "type": "markdown"
        }

        # Extraer metadata de las líneas
        for line in content.split("\n"):
            # Limpiar espacios y remover markdown bold (**) si existe
            clean_line = line.strip().replace("**", "")

            if "PROCEDIMIENTO:" in clean_line:
                metadata["procedure_name"] = clean_line.split(":", 1)[1].strip()

            elif "CÓDIGO:" in clean_line:
                metadata["procedure_code"] = clean_line.split(":", 1)[1].strip()

            elif "VERSIÓN:" in clean_line:
                metadata["version"] = clean_line.split(":", 1)[1].strip()

        return metadata
