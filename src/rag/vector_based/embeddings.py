"""
Generación de embeddings usando Vertex AI text-embedding-004

Este módulo es parte del enfoque Vector RAG (tradicional)
donde convertimos texto a vectores de 768 dimensiones.
"""

import os
from typing import List
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel


class EmbeddingGenerator:
    """
    Genera embeddings vectoriales usando Vertex AI.

    PEDAGOGÍA:
    - Embeddings = representación numérica del significado del texto
    - Textos similares semánticamente → vectores cercanos en espacio
    - Dimensionalidad 768 = balance entre precisión y costo computacional
    """

    def __init__(
        self,
        project_id: str | None = None,
        location: str = "us-central1",
        model_name: str = "text-embedding-004"
    ):
        """
        Args:
            project_id: ID del proyecto GCP (usa env var si es None)
            location: Región de Vertex AI
            model_name: Modelo de embeddings (text-embedding-004 recomendado)
        """
        self.project_id = project_id or os.getenv("VERTEX_AI_PROJECT")
        self.location = location
        self.model_name = model_name

        if not self.project_id:
            raise ValueError("VERTEX_AI_PROJECT env var requerida")

        # Inicializar Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)
        self.model = TextEmbeddingModel.from_pretrained(self.model_name)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 250
    ) -> List[List[float]]:
        """
        Genera embeddings para una lista de textos.

        PEDAGOGÍA:
        - Batch processing = más eficiente que uno por uno
        - Límite 250 textos/batch según documentación Vertex AI
        - Retries automáticos para manejar fallos transitorios

        Args:
            texts: Lista de textos para embeddings
            batch_size: Máximo textos por batch (default 250)

        Returns:
            Lista de vectores (cada uno de 768 dimensiones)
        """
        if not texts:
            return []

        all_embeddings = []

        # Procesar en batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Llamada síncrona al modelo (Vertex AI no soporta async aún)
            # Usamos run_in_executor para no bloquear el event loop
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.get_embeddings(batch)
            )

            # Extraer valores de embeddings
            batch_vectors = [emb.values for emb in embeddings]
            all_embeddings.extend(batch_vectors)

        return all_embeddings

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Genera embedding para un solo texto.

        Args:
            text: Texto individual

        Returns:
            Vector de 768 dimensiones
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else []
