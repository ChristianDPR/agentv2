"""
Almacenamiento y búsqueda vectorial con PostgreSQL + pgvector

Este módulo maneja la persistencia de embeddings y búsqueda por similitud.
"""

import os
import json
from typing import List, Dict, Any
import asyncpg
from pgvector.asyncpg import register_vector


class VectorStore:
    """
    Almacena y busca vectores en PostgreSQL con pgvector.

    PEDAGOGÍA:
    - pgvector = extensión de PostgreSQL para vectores
    - Similitud coseno = medida de cercanía semántica
    - Operador <=> = distancia coseno en pgvector
    - IVFFlat = índice para búsqueda rápida en millones de vectores
    """

    def __init__(self, database_url: str | None = None):
        """
        Args:
            database_url: URL de conexión PostgreSQL (usa env var si es None)
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL env var requerida")

        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Crea connection pool a PostgreSQL"""
        # Callback para inicializar cada conexión del pool
        async def init_connection(conn):
            await register_vector(conn)

        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            init=init_connection  # Registrar vector type en cada conexión
        )

        # Crear tabla y extensión si no existen
        await self._initialize_schema()

    async def close(self):
        """Cierra connection pool"""
        if self.pool:
            await self.pool.close()

    async def _initialize_schema(self):
        """
        Crea la tabla document_chunks si no existe.

        PEDAGOGÍA:
        - vector(768) = columna para embeddings de 768 dimensiones
        - JSONB = formato binario JSON eficiente
        - IVFFlat = índice para búsqueda vectorial rápida
          - lists=100 = particiones del espacio vectorial
          - Más lists = más rápido pero menos preciso
        """
        async with self.pool.acquire() as conn:
            # Habilitar extensión pgvector
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Crear tabla
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(255) NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    embedding vector(768),
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(document_id, chunk_index)
                )
            """)

            # Crear índice IVFFlat para búsqueda rápida
            # NOTA: Solo crear índice si hay >1000 registros en producción
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS embedding_idx
                ON document_chunks
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)

    async def upsert_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Inserta o actualiza chunks con sus embeddings.

        Args:
            chunks: Lista de dicts con keys:
                - content: Texto del chunk
                - metadata: Dict con metadata (categoría, source, chunk_index, etc.)
                - embedding: Vector de 768 dimensiones

        PEDAGOGÍA:
        - PostgreSQL JSONB requiere string, no dict de Python
        - json.dumps() convierte dict → JSON string
        - document_id y chunk_index son requeridos por el schema
        - ON CONFLICT permite actualizar chunks existentes
        """
        async with self.pool.acquire() as conn:
            for chunk in chunks:
                metadata = chunk.get("metadata", {})

                # Extraer document_id (usamos procedure_code si existe, sino source)
                document_id = metadata.get("procedure_code") or metadata.get("source", "unknown")

                # Extraer chunk_index
                chunk_index = metadata.get("chunk_index", 0)

                # Convertir metadata dict a JSON string
                metadata_json = json.dumps(metadata)

                await conn.execute("""
                    INSERT INTO document_chunks (document_id, chunk_index, content, metadata, embedding)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (document_id, chunk_index)
                    DO UPDATE SET
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding,
                        created_at = CURRENT_TIMESTAMP
                """,
                document_id,
                chunk_index,
                chunk["content"],
                metadata_json,
                chunk["embedding"]
                )

    async def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_metadata: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        Busca chunks más similares al query embedding.

        PEDAGOGÍA:
        - Operador <=> = distancia coseno en pgvector
        - Menor distancia = mayor similitud
        - Score = 1 - distancia (para tener valor entre 0-1)
        - ORDER BY ... LIMIT k = top-k resultados

        Args:
            query_embedding: Vector de query (768 dims)
            k: Número de resultados a retornar
            filter_metadata: Filtros JSONB opcionales

        Returns:
            Lista de chunks con content, metadata, score
        """
        query = """
            SELECT
                id,
                content,
                metadata,
                1 - (embedding <=> $1) AS score
            FROM document_chunks
        """

        params = [query_embedding]

        # Agregar filtros si existen
        if filter_metadata:
            conditions = []
            for key, value in filter_metadata.items():
                params.append(value)
                conditions.append(f"metadata->>'{key}' = ${len(params)}")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY embedding <=> $1 LIMIT $2"
        params.append(k)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            {
                "id": row["id"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
                "score": float(row["score"])
            }
            for row in rows
        ]

    async def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la base de datos"""
        async with self.pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM document_chunks")
            categories = await conn.fetch("""
                SELECT metadata->>'category' as category, COUNT(*) as count
                FROM document_chunks
                WHERE metadata ? 'category'
                GROUP BY category
            """)

        return {
            "total_chunks": total,
            "chunks_by_category": [
                {"category": row["category"], "count": row["count"]}
                for row in categories
            ]
        }
