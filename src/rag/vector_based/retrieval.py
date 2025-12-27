"""
Retrieval orquestado para Vector RAG

Integra ingestion, embeddings y vector store para búsqueda completa.
"""

from typing import List, Dict, Any
from .ingestion import DocumentIngestion
from .embeddings import EmbeddingGenerator
from .vector_store import VectorStore


class VectorRetrieval:
    """
    Orquestador del flujo completo de Vector RAG.

    PEDAGOGÍA:
    - RAG = Retrieval Augmented Generation
    - Flujo: query → embedding → búsqueda vectorial → contexto para LLM
    - Citas = anti-alucinación (el LLM cita fuentes reales)
    """

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        vector_store: VectorStore
    ):
        """
        Args:
            embedding_generator: Generador de embeddings
            vector_store: Almacenamiento vectorial
        """
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store
        self.ingestion = DocumentIngestion()

    async def ingest_and_index(
        self,
        documents_path: str,
        chunk_size: int = 512,
        overlap: int = 50
    ):
        """
        Ingesta e indexa documentos en el vector store.

        PEDAGOGÍA:
        - Este es el proceso de "preparación" del RAG
        - Se ejecuta UNA VEZ para cada conjunto de documentos
        - Después, las búsquedas son instantáneas

        Flujo:
        1. Cargar documentos .md
        2. Dividir en chunks
        3. Generar embeddings
        4. Guardar en vector store

        Args:
            documents_path: Ruta a documentos
            chunk_size: Tamaño de chunks
            overlap: Overlap entre chunks
        """
        # 1. Cargar documentos
        documents = await self.ingestion.load_documents(documents_path)
        print(f"📄 Cargados {len(documents)} documentos")

        # 2. Chunk documentos
        all_chunks = []
        for doc in documents:
            chunks = self.ingestion.chunk_document(doc, chunk_size, overlap)
            all_chunks.extend(chunks)

        print(f"📦 Creados {len(all_chunks)} chunks")

        # 3. Generar embeddings
        texts = [chunk["content"] for chunk in all_chunks]
        embeddings = await self.embedding_generator.generate_embeddings(texts)

        print(f"🔢 Generados {len(embeddings)} embeddings")

        # 4. Combinar chunks con embeddings
        chunks_with_embeddings = [
            {
                "content": chunk["content"],
                "metadata": chunk["metadata"],
                "embedding": embedding
            }
            for chunk, embedding in zip(all_chunks, embeddings)
        ]

        # 5. Guardar en vector store
        await self.vector_store.upsert_chunks(chunks_with_embeddings)

        print(f"✅ Indexados {len(chunks_with_embeddings)} chunks en vector store")

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Recupera chunks relevantes para una query.

        PEDAGOGÍA:
        - Esta es la "R" de RAG: Retrieval
        - El LLM usará estos chunks como contexto
        - Las citas permiten verificar la fuente de información

        Flujo:
        1. Generar embedding del query
        2. Buscar chunks similares en vector store
        3. Formatear con citas

        Args:
            query: Consulta del usuario
            k: Número de chunks a retornar
            filter_metadata: Filtros opcionales

        Returns:
            Dict con chunks y citas formateadas
        """
        # 1. Generar embedding del query
        query_embedding = await self.embedding_generator.generate_embedding(query)

        # 2. Buscar chunks similares
        chunks = await self.vector_store.similarity_search(
            query_embedding=query_embedding,
            k=k,
            filter_metadata=filter_metadata
        )

        # 3. Formatear con citas
        formatted_chunks = []
        for chunk in chunks:
            metadata = chunk["metadata"]
            score = chunk["score"]

            # Formatear citación
            citation = self._format_citation(metadata, score)

            formatted_chunks.append({
                "content": chunk["content"],
                "metadata": metadata,
                "score": score,
                "citation": citation
            })

        return {
            "chunks": formatted_chunks,
            "method": "vector_rag"
        }

    def _format_citation(self, metadata: Dict[str, Any], score: float) -> str:
        """
        Formatea una cita a partir de metadata.

        PEDAGOGÍA:
        - Las citas DEBEN ser específicas y verificables
        - Incluir nombre del archivo fuente y score de relevancia
        - Ejemplo: [Doc: proc-jubilacion-001.pdf, relevancia: 85%]
        """
        source = metadata.get("source", "documento-desconocido")
        score_pct = int(score * 100)

        return f"[Doc: {source}, relevancia: {score_pct}%]"
