"""
Retrieval orquestado para Agent RAG

Usa el LLM para evaluar relevancia en vez de búsqueda vectorial.

VERSION 2.0: Retrieval con índices JSON
- Fase 1: LLM filtra documentos relevantes leyendo índices
- Fase 2: LLM filtra secciones relevantes por documento
- Fase 3: Lee solo secciones específicas del contenido
"""

import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from .document_reader import DocumentReader
from .chunk_evaluator import ChunkEvaluator


class AgentRetrieval:
    """
    Orquestador del flujo completo de Agent RAG.

    PEDAGOGÍA:
    - DIFERENCIA CON VECTOR RAG:
      * NO usa embeddings
      * NO usa vector store
      * El LLM lee y evalúa directamente
    - VENTAJA: Transparencia total (el LLM explica el "por qué")
    - DESVENTAJA: Más lento y costoso

    CUÁNDO USAR:
    - Pocos documentos (<100)
    - Necesitas explicabilidad
    - No quieres infraestructura de vectores
    """

    def __init__(
        self,
        document_reader: DocumentReader,
        chunk_evaluator: ChunkEvaluator
    ):
        """
        Args:
            document_reader: Lector de documentos
            chunk_evaluator: Evaluador con LLM
        """
        self.document_reader = document_reader
        self.chunk_evaluator = chunk_evaluator

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        documents_path: str = "data/documentos"
    ) -> Dict[str, Any]:
        """
        Recupera documentos relevantes usando el LLM como juez.

        PEDAGOGÍA:
        - Flujo diferente a Vector RAG:
          1. Leer TODOS los documentos
          2. Evaluar CADA UNO con el LLM
          3. Rankear por score
          4. Retornar top-k

        OPTIMIZACIÓN:
        - Evaluaciones en paralelo (asyncio.gather)
        - Sin paralelo, sería muy lento (N llamadas secuenciales al LLM)

        Args:
            query: Consulta del usuario
            k: Número de documentos a retornar
            documents_path: Ruta a documentos

        Returns:
            Dict con chunks y reasoning del LLM
        """
        # 1. Leer todos los documentos
        documents = await self.document_reader.read_all_documents(documents_path)

        # 2. Evaluar relevancia de cada documento EN PARALELO
        # Esto reduce latencia de N*time a ~time
        evaluation_tasks = [
            self.chunk_evaluator.evaluate_relevance(query, doc)
            for doc in documents
        ]
        evaluations = await asyncio.gather(*evaluation_tasks)

        # 3. Combinar documentos con evaluaciones
        scored_docs = []
        for doc, evaluation in zip(documents, evaluations):
            scored_docs.append({
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": evaluation["relevance_score"],
                "reasoning": evaluation["reasoning"],
                "relevant_sections": evaluation["relevant_sections"]
            })

        # 4. Rankear por score descendente
        scored_docs.sort(key=lambda x: x["score"], reverse=True)

        # 5. Tomar top-k
        top_docs = scored_docs[:k]

        # 6. Formatear con citas diferenciadas de Vector RAG
        formatted_chunks = []
        for doc in top_docs:
            citation = self._format_citation(doc["metadata"], doc["score"])

            formatted_chunks.append({
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": doc["score"],
                "reasoning": doc["reasoning"],  # ÚNICO DE AGENT RAG
                "citation": citation
            })

        return {
            "chunks": formatted_chunks,
            "method": "agent_rag"  # Identificador del método
        }

    def _format_citation(self, metadata: Dict[str, Any], score: float) -> str:
        """
        Formatea cita distinguible de Vector RAG.

        PEDAGOGÍA:
        - Incluimos "relevancia LLM" para diferenciar de vector search
        - El usuario puede saber qué método se usó
        """
        proc_code = metadata.get("procedure_code", "UNKNOWN")
        category = metadata.get("category", "general")
        score_pct = int(score * 100)

        return f"[Doc: {proc_code} ({category}), relevancia LLM: {score_pct}%]"

    # ========================================================================
    # VERSION 2.0: RETRIEVAL CON ÍNDICES JSON (3 FASES)
    # ========================================================================

    def _load_all_indices(self, indices_dir: str = "data/indices") -> Dict[str, Dict]:
        """
        Carga todos los índices JSON disponibles.

        PEDAGOGÍA:
        - Los índices son archivos JSON pequeños (resúmenes de documentos)
        - El LLM puede leer TODOS los índices rápidamente
        - Decide qué documentos son relevantes sin leer contenido completo

        Args:
            indices_dir: Directorio con archivos index-*.json

        Returns:
            Dict {document_id: index_data}
        """
        indices_path = Path(indices_dir)

        if not indices_path.exists():
            print(f"⚠️  Directorio de índices no existe: {indices_dir}")
            print("💡 Fallback: Se usará el método de retrieval sin índices")
            return {}

        indices = {}

        for index_file in indices_path.glob("index-*.json"):
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    doc_id = index_data.get("document_id", index_file.stem)
                    indices[doc_id] = index_data
            except Exception as e:
                print(f"⚠️  Error cargando índice {index_file.name}: {e}")
                continue

        return indices

    async def _filter_relevant_documents(
        self,
        query: str,
        indices: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        FASE 1: LLM decide qué documentos son relevantes leyendo índices.

        PEDAGOGÍA:
        - El LLM lee TODOS los índices (son resúmenes cortos)
        - Decide cuáles son relevantes para la query
        - Más eficiente que leer documentos completos

        Args:
            query: Consulta del usuario
            indices: Dict con todos los índices cargados

        Returns:
            Lista de documentos relevantes con reasoning
        """
        if not indices:
            return []

        # Formatear índices para el prompt
        indices_summary = []
        for doc_id, index_data in indices.items():
            summary = f"""
Documento: {doc_id}
Código: {index_data.get('procedure_code', 'N/A')}
Título: {index_data.get('procedure_name', 'Sin título')}
Categoría: {index_data.get('category', 'general')}
Resumen: {index_data.get('summary', 'Sin resumen')}
Número de secciones: {len(index_data.get('sections', []))}
"""
            indices_summary.append(summary.strip())

        # Prompt para Fase 1
        prompt = f"""Tienes estos documentos disponibles (índices):

{chr(10).join(indices_summary)}

Pregunta del usuario: {query}

¿Qué documentos son RELEVANTES para responder esta pregunta?

Responde SOLO con un JSON válido (sin markdown, sin explicaciones adicionales):
{{
  "relevant_documents": ["doc_id_1", "doc_id_2", ...],
  "reasoning": "Explicación breve de por qué estos documentos son relevantes"
}}

Si ningún documento es relevante, devuelve un array vacío.
"""

        # Llamar al LLM (usando el chunk_evaluator como proxy al model provider)
        try:
            response = await self.chunk_evaluator.model_provider.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )

            # Parse JSON response
            response_text = response.content.strip()

            # Limpiar markdown si está presente
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)

            # Construir lista de documentos relevantes con metadata
            relevant_docs = []
            for doc_id in result.get("relevant_documents", []):
                if doc_id in indices:
                    relevant_docs.append({
                        "document_id": doc_id,
                        "index": indices[doc_id],
                        "reasoning": result.get("reasoning", "")
                    })

            return relevant_docs

        except json.JSONDecodeError as e:
            print(f"⚠️  Error parseando JSON en Fase 1: {e}")
            print(f"Respuesta del LLM: {response_text[:200]}...")
            return []
        except Exception as e:
            print(f"⚠️  Error en Fase 1 (filtrar documentos): {e}")
            return []

    async def _filter_relevant_sections(
        self,
        query: str,
        document_index: Dict[str, Any]
    ) -> List[str]:
        """
        FASE 2: LLM decide qué secciones de un documento son relevantes.

        PEDAGOGÍA:
        - Ya sabemos que el documento es relevante (Fase 1)
        - Ahora el LLM lee el índice de secciones
        - Decide qué secciones específicas leer (no todo el documento)

        Args:
            query: Consulta del usuario
            document_index: Índice completo del documento

        Returns:
            Lista de section_ids relevantes
        """
        sections = document_index.get("sections", [])

        if not sections:
            return []

        # Formatear secciones para el prompt
        sections_summary = []
        for section in sections:
            summary = f"""
Sección {section['section_id']}: {section['title']}
Páginas: {section.get('page_start', '?')}-{section.get('page_end', '?')}
Resumen: {section.get('summary', 'Sin resumen')}
"""
            sections_summary.append(summary.strip())

        # Prompt para Fase 2
        prompt = f"""Documento: {document_index.get('procedure_name', 'Sin título')}
Código: {document_index.get('procedure_code', 'N/A')}

Índice de secciones:
{chr(10).join(sections_summary)}

Pregunta del usuario: {query}

¿Qué secciones necesitas leer para responder esta pregunta?

Responde SOLO con un JSON válido (sin markdown, sin explicaciones adicionales):
{{
  "relevant_sections": ["1", "5", "9"],
  "reasoning": "Explicación breve de por qué estas secciones"
}}

Selecciona SOLO las secciones estrictamente necesarias (máximo 3-5).
Si no estás seguro, es mejor incluir una sección de más que omitirla.
"""

        try:
            response = await self.chunk_evaluator.model_provider.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )

            response_text = response.content.strip()

            # Limpiar markdown si está presente
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)

            return result.get("relevant_sections", [])

        except json.JSONDecodeError as e:
            print(f"⚠️  Error parseando JSON en Fase 2: {e}")
            print(f"Respuesta del LLM: {response_text[:200]}...")
            # Fallback: retornar todas las secciones
            return [s["section_id"] for s in sections]
        except Exception as e:
            print(f"⚠️  Error en Fase 2 (filtrar secciones): {e}")
            # Fallback: retornar todas las secciones
            return [s["section_id"] for s in sections]

    def _load_section_content(
        self,
        document_index: Dict[str, Any],
        section_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        FASE 3: Carga contenido SOLO de las secciones relevantes por PÁGINAS.

        PEDAGOGÍA:
        - Para PDFs: Lee SOLO las páginas especificadas (eficiente)
        - Para Markdown: Lee documento completo y extrae por títulos
        - Mucho más rápido y preciso que leer documento completo

        Args:
            document_index: Índice del documento
            section_ids: IDs de secciones a cargar

        Returns:
            Lista de secciones con contenido completo
        """
        doc_path = Path(document_index.get("path", ""))

        if not doc_path.exists():
            print(f"⚠️  Documento no existe: {doc_path}")
            return []

        # Extraer secciones relevantes
        sections_content = []
        all_sections = document_index.get("sections", [])
        is_pdf = doc_path.suffix.lower() == '.pdf'

        for section in all_sections:
            if section["section_id"] not in section_ids:
                continue

            try:
                # Extraer rango de páginas del formato del índice
                page_start = None
                page_end = None

                # Formato 1: Array de páginas ["pages": [1,2,3,4,5]]
                if section.get("pages") and isinstance(section["pages"], list):
                    page_start = min(section["pages"])
                    page_end = max(section["pages"])
                # Formato 2: String de rango ["page_range": "1-5"]
                elif section.get("page_range"):
                    try:
                        parts = section["page_range"].split("-")
                        page_start = int(parts[0])
                        page_end = int(parts[1])
                    except (ValueError, IndexError):
                        pass
                # Formato 3: Campos separados (legacy)
                elif section.get("page_start") and section.get("page_end"):
                    page_start = section["page_start"]
                    page_end = section["page_end"]

                # NUEVO: Para PDFs, leer solo páginas específicas
                if is_pdf and page_start and page_end:
                    section_content = self.document_reader.read_pdf_pages(
                        doc_path,
                        page_start,
                        page_end
                    )
                else:
                    # Fallback para Markdown o secciones sin páginas
                    content = self.document_reader._read_file(doc_path)
                    section_content = self._extract_section_from_content(
                        content,
                        section
                    )

                sections_content.append({
                    "section_id": section["section_id"],
                    "title": section["title"],
                    "content": section_content,
                    "metadata": {
                        "document_id": document_index.get("document_id"),
                        "procedure_code": document_index.get("procedure_code"),
                        "procedure_name": document_index.get("procedure_name"),
                        "page_start": page_start,
                        "page_end": page_end,
                        "category": document_index.get("category")
                    }
                })

            except Exception as e:
                print(f"⚠️  Error cargando sección {section['section_id']} de {doc_path.name}: {e}")
                continue

        return sections_content

    def _extract_section_from_content(
        self,
        full_content: str,
        section: Dict[str, Any]
    ) -> str:
        """
        Extrae el contenido de una sección específica del documento completo.

        PEDAGOGÍA:
        - Busca la sección por título (## TÍTULO)
        - Extrae hasta la siguiente sección del mismo nivel
        - Si no encuentra, retorna una porción aproximada

        Args:
            full_content: Contenido completo del documento
            section: Dict con info de la sección

        Returns:
            Contenido de la sección
        """
        title = section.get("title", "")

        if not title:
            return ""

        # Buscar por título markdown (## TÍTULO)
        import re

        # Intentar encontrar la sección por título
        pattern = rf"^##\s+{re.escape(title)}.*?(?=^##\s+|\Z)"
        match = re.search(pattern, full_content, re.MULTILINE | re.DOTALL)

        if match:
            return match.group(0).strip()

        # Fallback: buscar título sin formato específico
        lines = full_content.split("\n")
        start_idx = None

        for i, line in enumerate(lines):
            if title.lower() in line.lower():
                start_idx = i
                break

        if start_idx is not None:
            # Tomar hasta la próxima sección (título con ##)
            end_idx = len(lines)
            for i in range(start_idx + 1, len(lines)):
                if lines[i].strip().startswith("##"):
                    end_idx = i
                    break

            return "\n".join(lines[start_idx:end_idx]).strip()

        # Último fallback: retornar resumen de la sección si existe
        return section.get("summary", f"[Contenido de sección {section['section_id']} no encontrado]")

    async def _generate_response_with_sections(
        self,
        query: str,
        sections_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        FASE 3 (final): Genera respuesta usando secciones específicas.

        PEDAGOGÍA:
        - El LLM lee SOLO las secciones relevantes (no documentos completos)
        - Genera respuesta citando las fuentes correctamente
        - Incluye metadata de qué secciones consultó

        Args:
            query: Consulta del usuario
            sections_content: Lista de secciones con contenido

        Returns:
            Dict con respuesta y citas
        """
        if not sections_content:
            return {
                "chunks": [],
                "method": "agent_rag_indexed",
                "message": "No se encontraron secciones relevantes"
            }

        # Formatear secciones para el prompt
        formatted_sections = []
        for section in sections_content:
            formatted = f"""
[{section['metadata']['procedure_code']} - {section['title']}, páginas {section['metadata']['page_start']}-{section['metadata']['page_end']}]

{section['content']}
"""
            formatted_sections.append(formatted.strip())

        # Prompt para generar respuesta
        prompt = f"""Pregunta del usuario: {query}

Contenido relevante de los documentos AFP:

{chr(10).join(formatted_sections)}

Genera una respuesta clara y concisa que:
1. Responda directamente la pregunta
2. Use información SOLO del contenido proporcionado
3. Incluya citas en formato: [PROC-XXX-NNN - Título Sección, páginas X-Y]
4. Sea precisa y profesional

Respuesta:"""

        try:
            response = await self.chunk_evaluator.model_provider.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1000
            )

            # Formatear como chunks para compatibilidad con API existente
            chunks = []
            for section in sections_content:
                citation = f"[{section['metadata']['procedure_code']} - {section['title']}, páginas {section['metadata']['page_start']}-{section['metadata']['page_end']}]"

                chunks.append({
                    "content": section['content'],
                    "metadata": section['metadata'],
                    "score": 1.0,  # Score fijo, LLM ya filtró
                    "reasoning": f"Sección relevante: {section['title']}",
                    "citation": citation
                })

            return {
                "response": response.content,
                "chunks": chunks,
                "method": "agent_rag_indexed",
                "sections_consulted": [
                    f"{s['metadata']['procedure_code']}: {s['title']}"
                    for s in sections_content
                ]
            }

        except Exception as e:
            print(f"⚠️  Error generando respuesta final: {e}")
            return {
                "chunks": [],
                "method": "agent_rag_indexed",
                "error": str(e)
            }

    async def retrieve_with_index(
        self,
        query: str,
        indices_dir: str = "data/indices",
        documents_path: str = "data/documentos"
    ) -> Dict[str, Any]:
        """
        Retrieval en 3 FASES usando índices JSON.

        PEDAGOGÍA:
        - FASE 1: LLM lee TODOS los índices → decide qué docs son relevantes
        - FASE 2: LLM lee índices de secciones → decide qué secciones leer
        - FASE 3: Lee SOLO secciones específicas → genera respuesta

        VENTAJAS:
        - Más eficiente: Lee solo lo necesario
        - Más rápido: Menos texto para el LLM
        - Más barato: Menos tokens
        - Mejor rendimiento: Información más precisa

        FLOW:
        Usuario: "¿Cómo jubilarme anticipadamente?"
            ↓
        Fase 1: Lee índices → "PROC-JUB-002 es relevante"
            ↓
        Fase 2: Lee índice PROC-JUB-002 → "Necesito secciones 2, 5, 9"
            ↓
        Fase 3: Lee secciones específicas → Genera respuesta con citas

        Args:
            query: Consulta del usuario
            indices_dir: Directorio con índices JSON
            documents_path: Directorio con documentos originales

        Returns:
            Dict con respuesta, chunks y metadata
        """
        start_time = time.time()

        print(f"🔍 Iniciando retrieval con índices...")
        print(f"📝 Query: {query}")

        # FASE 1: Cargar índices y filtrar documentos relevantes
        print(f"\n📚 FASE 1: Filtrando documentos relevantes...")
        indices = self._load_all_indices(indices_dir)

        if not indices:
            print("⚠️  No hay índices disponibles. Usando método sin índices.")
            return await self.retrieve(query, k=5, documents_path=documents_path)

        print(f"   Índices cargados: {len(indices)}")

        relevant_docs = await self._filter_relevant_documents(query, indices)

        if not relevant_docs:
            print("❌ No se encontraron documentos relevantes")
            return {
                "chunks": [],
                "method": "agent_rag_indexed",
                "message": "No se encontraron documentos relevantes para tu consulta"
            }

        print(f"   ✅ Documentos relevantes: {[d['document_id'] for d in relevant_docs]}")

        # FASE 2: Para cada documento, filtrar secciones relevantes
        print(f"\n📄 FASE 2: Filtrando secciones relevantes...")
        all_sections = []

        for doc in relevant_docs:
            doc_index = doc["index"]
            section_ids = await self._filter_relevant_sections(query, doc_index)

            if section_ids:
                print(f"   {doc['document_id']}: secciones {', '.join(section_ids)}")

                # FASE 3: Cargar contenido de secciones
                sections_content = self._load_section_content(doc_index, section_ids)
                all_sections.extend(sections_content)

        print(f"   ✅ Total secciones a leer: {len(all_sections)}")

        # FASE 3 (final): Generar respuesta con secciones
        print(f"\n💬 FASE 3: Generando respuesta final...")
        result = await self._generate_response_with_sections(query, all_sections)

        elapsed = int((time.time() - start_time) * 1000)
        print(f"\n⏱️  Tiempo total: {elapsed}ms")
        print(f"✅ Retrieval completado")

        result["elapsed_ms"] = elapsed
        return result

    async def retrieve_old(
        self,
        query: str,
        k: int = 5,
        documents_path: str = "data/documentos"
    ) -> Dict[str, Any]:
        """
        MÉTODO ANTIGUO: Retrieval sin índices (lee documentos completos).

        PEDAGOGÍA:
        - Mantiene compatibilidad con código existente
        - Útil para comparar rendimiento vs método con índices
        - Fallback si índices no existen

        Args:
            query: Consulta del usuario
            k: Número de documentos a retornar
            documents_path: Ruta a documentos

        Returns:
            Dict con chunks y reasoning del LLM
        """
        print("⚠️  Usando método SIN índices (menos eficiente)")
        return await self.retrieve(query, k, documents_path)
