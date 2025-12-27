"""
Sistema de Indexación para Agent RAG

OBJETIVO:
- Procesar documentos PDF en batches
- Generar índices JSON con resúmenes por sección/página
- Usar LLM para resumir contenido de manera inteligente

DIFERENCIA CON VECTOR RAG:
- NO usa embeddings
- Genera resúmenes estructurados con LLM
- Índices JSON para búsqueda rápida por metadatos

PEDAGOGÍA:
- El agente busca primero en índices (rápido)
- Luego lee documentos completos solo si es necesario
- LLM resume batches de 5 páginas → más eficiente
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class AgentRAGIndexer:
    """
    Indexador de documentos para Agent RAG.

    FLUJO:
    1. Lee PDF completo con pdfplumber
    2. Agrupa páginas en batches de 5
    3. Resume cada batch con LLM
    4. Genera resumen global del documento
    5. Crea índice JSON estructurado
    6. Guarda en data/indices/

    PEDAGOGÍA:
    - Batches de 5 páginas = balance entre contexto y costo
    - Resúmenes estructurados facilitan búsqueda posterior
    - Metadata se extrae automáticamente
    - Keywords por sección para búsqueda rápida
    """

    def __init__(self, model_provider):
        """
        Args:
            model_provider: Instancia de ModelProvider (ej: VertexAIProvider)
                           Necesitamos LLM para resumir contenido
        """
        self.model_provider = model_provider

    async def index_document(
        self,
        pdf_path: str,
        output_dir: str = "data/indices",
        batch_size: int = 5
    ) -> Dict[str, Any]:
        """
        Procesa un PDF completo y genera su índice.

        FLUJO COMPLETO:
        1. Lee PDF por páginas
        2. Crea batches de N páginas
        3. Resume cada batch con LLM
        4. Genera resumen global
        5. Crea índice JSON
        6. Guarda en disco

        Args:
            pdf_path: Ruta al archivo PDF
            output_dir: Directorio donde guardar índices
            batch_size: Páginas por batch (default: 5)

        Returns:
            Dict con el índice generado

        Example:
            >>> indexer = AgentRAGIndexer(model_provider)
            >>> index = await indexer.index_document("data/documentos/jubilacion/proc-jub-001.pdf")
            >>> print(index["document_id"])
            'PROC-JUB-001'
        """
        print(f"\n📄 Indexando: {pdf_path}")

        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            raise FileNotFoundError(f"PDF no existe: {pdf_path}")

        try:
            # 1. Leer PDF completo
            pages = self._read_pdf_pages(pdf_path_obj)
            if not pages:
                raise ValueError(f"No se pudo extraer texto del PDF: {pdf_path}")

            print(f"   ✓ Leídas {len(pages)} páginas")

            # 2. Crear batches
            batches = self._create_batches(pages, batch_size)
            print(f"   ✓ Creados {len(batches)} batches de {batch_size} páginas")

            # 3. Resumir cada batch
            sections = []
            for i, batch in enumerate(batches, 1):
                print(f"   📝 Resumiendo batch {i}/{len(batches)}...")
                summary = await self._summarize_batch(batch)

                # Generar keywords del resumen
                keywords = self._extract_keywords(summary)

                sections.append({
                    "section_id": str(i),
                    "title": f"Sección {i}",  # Título básico, LLM puede mejorar
                    "pages": [page["page_num"] for page in batch],
                    "page_range": f"{batch[0]['page_num']}-{batch[-1]['page_num']}",
                    "summary": summary,
                    "keywords": keywords
                })

            print(f"   ✓ {len(sections)} secciones resumidas")

            # 4. Generar resumen global
            print("   📝 Generando resumen global del documento...")
            global_summary = await self._summarize_document(sections)

            # 5. Extraer metadata del PDF
            metadata = self._extract_metadata_from_content(pages, pdf_path_obj)

            # 6. Crear índice estructurado
            document = {
                "content": "\n\n".join([p["text"] for p in pages]),
                "metadata": metadata
            }
            index = self._create_index(document, global_summary, sections)

            # 7. Guardar índice
            output_path = self._save_index(index, output_dir)
            print(f"   ✅ Índice guardado: {output_path}")

            return index

        except Exception as e:
            print(f"   ❌ Error indexando {pdf_path}: {e}")
            raise

    def _read_pdf_pages(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Lee PDF página por página con PyMuPDF (fitz).

        PEDAGOGÍA:
        - PyMuPDF es rápido y eficiente
        - Mantiene estructura de páginas
        - Extrae texto limpio

        Returns:
            Lista de páginas: [{"page_num": 1, "text": "..."}, ...]
        """
        try:
            import fitz
        except ImportError:
            raise ImportError(
                "PyMuPDF no está instalado. "
                "Ejecuta: pip install pymupdf"
            )

        pages = []
        doc = fitz.open(pdf_path)
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text and text.strip():
                    pages.append({
                        "page_num": page_num + 1,  # 1-indexed for consistency
                        "text": text.strip()
                    })
        finally:
            doc.close()

        return pages

    def _create_batches(
        self,
        pages: List[Dict[str, Any]],
        batch_size: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """
        Agrupa páginas en batches.

        PEDAGOGÍA:
        - Batch size = 5 páginas es buen balance
        - Más páginas = más contexto pero más caro
        - Menos páginas = menos contexto pero más batches

        Args:
            pages: Lista de páginas
            batch_size: Páginas por batch

        Returns:
            Lista de batches: [[página1, página2, ...], [página6, ...], ...]
        """
        batches = []
        for i in range(0, len(pages), batch_size):
            batch = pages[i:i + batch_size]
            batches.append(batch)
        return batches

    async def _summarize_batch(self, batch: List[Dict[str, Any]]) -> str:
        """
        Resume un batch de páginas con LLM.

        PEDAGOGÍA:
        - Prompt específico para procedimientos AFP
        - Temperatura baja (0.3) para consistencia
        - Max tokens suficiente para resumen detallado
        - Estructura clara: tema + puntos clave + requisitos

        Args:
            batch: Lista de páginas del batch

        Returns:
            Resumen del batch (max 150 palabras)
        """
        # Concatenar texto de páginas
        pages_text = "\n\n".join([
            f"=== Página {p['page_num']} ===\n{p['text']}"
            for p in batch
        ])

        # Prompt para resumir batch
        prompt = f"""Resume las siguientes páginas de un procedimiento AFP.

INSTRUCCIONES:
- Identifica el TEMA PRINCIPAL de estas páginas
- Lista los PUNTOS CLAVE (máximo 4)
- Menciona REQUISITOS si los hay
- Menciona PLAZOS si los hay
- Máximo 150 palabras
- Sé específico y concreto

PÁGINAS:
{pages_text}

RESUMEN:"""

        try:
            summary = await self.model_provider.generate(
                prompt=prompt,
                temperature=0.3,  # Baja para consistencia
                max_tokens=4000   # Modelo soporta 1M tokens de contexto
            )
            return summary.strip()
        except Exception as e:
            # Fallback: usar primeras 200 palabras del batch
            print(f"   ⚠️  LLM falló, usando resumen básico: {e}")
            words = pages_text.split()[:200]
            return " ".join(words) + "..."

    async def _summarize_document(self, sections: List[Dict[str, Any]]) -> str:
        """
        Genera resumen global del documento completo.

        PEDAGOGÍA:
        - Resume las secciones (no todo el documento)
        - Más eficiente: resumen de resúmenes
        - Captura objetivo general y proceso completo

        Args:
            sections: Lista de secciones con sus resúmenes

        Returns:
            Resumen global (max 200 palabras)
        """
        # Concatenar resúmenes de secciones
        sections_text = "\n\n".join([
            f"Sección {s['section_id']} (páginas {s['page_range']}):\n{s['summary']}"
            for s in sections
        ])

        # Prompt para resumen global
        prompt = f"""Resume este documento completo de procedimiento AFP.

INSTRUCCIONES:
- Identifica el OBJETIVO principal del documento
- Lista los REQUISITOS PRINCIPALES
- Describe el PROCESO GENERAL en 3-4 pasos
- Menciona PLAZOS importantes
- Máximo 200 palabras
- Enfócate en lo más importante

RESÚMENES DE SECCIONES:
{sections_text}

RESUMEN GLOBAL:"""

        try:
            summary = await self.model_provider.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=4000  # Modelo soporta 1M tokens de contexto
            )
            return summary.strip()
        except Exception as e:
            # Fallback: usar primer resumen de sección
            print(f"   ⚠️  LLM falló para resumen global: {e}")
            if sections:
                return sections[0]["summary"]
            return "Resumen no disponible"

    def _extract_metadata_from_content(
        self,
        pages: List[Dict[str, Any]],
        pdf_path: Path
    ) -> Dict[str, Any]:
        """
        Extrae metadata del contenido del PDF y su path.

        PEDAGOGÍA:
        - Busca patrones en primeras páginas
        - Infiere del nombre de archivo si no encuentra
        - Similar a DocumentReader pero adaptado para PDFs

        Returns:
            Dict con metadata: procedure_code, version, date, category, etc.
        """
        # Concatenar primeras 3 páginas para búsqueda de metadata
        first_pages = "\n".join([p["text"] for p in pages[:3]])

        metadata = {
            "source_file": pdf_path.name,
            "category": self._infer_category(pdf_path),
            "total_pages": len(pages),
            "indexed_at": datetime.utcnow().isoformat() + "Z"
        }

        # Extraer procedure_code
        code_match = re.search(
            r'(?:CÓDIGO|CODIGO|CODE):\s*([A-Z0-9\-]+)',
            first_pages,
            re.IGNORECASE
        )
        if code_match:
            metadata["procedure_code"] = code_match.group(1).upper()
        else:
            # Inferir del nombre de archivo
            metadata["procedure_code"] = self._infer_procedure_code(pdf_path)

        # Extraer versión
        version_match = re.search(
            r'(?:VERSIÓN|VERSION|VER\.):\s*([\d\.]+)',
            first_pages,
            re.IGNORECASE
        )
        if version_match:
            metadata["version"] = version_match.group(1)
        else:
            metadata["version"] = "1.0"

        # Extraer fecha
        date_match = re.search(
            r'(?:FECHA|DATE):\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})',
            first_pages,
            re.IGNORECASE
        )
        if date_match:
            metadata["date"] = date_match.group(1)
        else:
            metadata["date"] = datetime.utcnow().strftime("%Y-%m-%d")

        # Extraer título (buscar en primera página)
        title_match = re.search(
            r'(?:PROCEDIMIENTO|PROCEDURE):\s*(.+)',
            pages[0]["text"] if pages else "",
            re.IGNORECASE
        )
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        else:
            # Inferir del nombre de archivo
            metadata["title"] = self._infer_title(pdf_path)

        return metadata

    def _create_index(
        self,
        document: Dict[str, Any],
        global_summary: str,
        sections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Crea índice JSON estructurado.

        PEDAGOGÍA:
        - Estructura clara para búsqueda rápida
        - Incluye resúmenes por sección y global
        - Keywords para búsqueda sin embeddings
        - Metadata completa

        Returns:
            Dict con índice completo
        """
        metadata = document["metadata"]

        index = {
            "document_id": metadata.get("procedure_code", "UNKNOWN"),
            "title": metadata.get("title", "Sin título"),
            "category": metadata.get("category", "general"),
            "source_file": metadata.get("source_file", ""),
            "total_pages": metadata.get("total_pages", 0),
            "summary": global_summary,
            "metadata": {
                "procedure_code": metadata.get("procedure_code", ""),
                "version": metadata.get("version", "1.0"),
                "date": metadata.get("date", ""),
                "indexed_at": metadata.get("indexed_at", "")
            },
            "sections": sections
        }

        return index

    def _save_index(self, index: Dict[str, Any], output_dir: str) -> str:
        """
        Guarda índice en disco como JSON.

        Args:
            index: Índice a guardar
            output_dir: Directorio de salida

        Returns:
            Path al archivo guardado
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Nombre de archivo: document_id.json
        filename = f"{index['document_id']}.json"
        file_path = output_path / filename

        # Guardar con formato bonito (indent=2)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def _extract_keywords(self, text: str, max_keywords: int = 8) -> List[str]:
        """
        Extrae keywords básicos del texto.

        PEDAGOGÍA:
        - Método simple: palabras frecuentes + stopwords
        - Suficiente para búsqueda básica sin embeddings
        - LLM podría mejorar esto en versión avanzada

        Args:
            text: Texto del cual extraer keywords
            max_keywords: Máximo número de keywords

        Returns:
            Lista de keywords
        """
        # Stopwords españolas básicas
        stopwords = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'al', 'y', 'o', 'en', 'a', 'por', 'para',
            'con', 'sin', 'sobre', 'que', 'es', 'son', 'está', 'están',
            'se', 'su', 'sus', 'este', 'esta', 'estos', 'estas',
            'como', 'si', 'no', 'más', 'pero', 'cuando', 'donde'
        }

        # Limpiar y tokenizar
        words = re.findall(r'\b[a-záéíóúñ]{4,}\b', text.lower())

        # Filtrar stopwords
        words = [w for w in words if w not in stopwords]

        # Contar frecuencias
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Top N palabras más frecuentes
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in top_words[:max_keywords]]

        return keywords

    def _infer_category(self, file_path: Path) -> str:
        """Infiere categoría del path (igual que DocumentReader)"""
        parent_name = file_path.parent.name
        if parent_name == "documentos":
            return "general"
        return parent_name

    def _infer_procedure_code(self, file_path: Path) -> str:
        """Infiere código de procedimiento del nombre (igual que DocumentReader)"""
        stem = file_path.stem
        match = re.search(r'proc-(\w+)-(\d+)', stem, re.IGNORECASE)
        if match:
            category_abbr = match.group(1).upper()
            number = match.group(2)
            return f"PROC-{category_abbr}-{number}"
        normalized = stem.replace("_", "-").replace(" ", "-").upper()
        return normalized

    def _infer_title(self, file_path: Path) -> str:
        """Infiere título del nombre de archivo"""
        stem = file_path.stem
        humanized = stem.replace("_", " ").replace("-", " ").title()
        return humanized


# ============================================================================
# TESTING
# ============================================================================

async def test_indexer():
    """
    Test del indexer con un documento de ejemplo.

    PEDAGOGÍA:
    - Muestra cómo usar el indexer
    - Procesa un PDF real
    - Genera y guarda índice
    - Imprime resultado para inspección
    """
    print("=" * 60)
    print("TEST: AgentRAGIndexer")
    print("=" * 60)

    # 1. Inicializar ModelProvider
    print("\n1️⃣  Inicializando ModelProvider...")
    from src.framework.model_provider import VertexAIProvider

    try:
        provider = VertexAIProvider()
        print(f"   ✓ Provider: {provider}")
    except Exception as e:
        print(f"   ❌ Error inicializando provider: {e}")
        print("   💡 Tip: Configura VERTEX_AI_PROJECT en .env")
        return

    # 2. Crear indexer
    print("\n2️⃣  Creando indexer...")
    indexer = AgentRAGIndexer(provider)
    print("   ✓ Indexer creado")

    # 3. Buscar un PDF de ejemplo
    print("\n3️⃣  Buscando PDFs de ejemplo...")
    docs_path = Path("data/documentos")
    pdf_files = list(docs_path.rglob("*.pdf"))

    if not pdf_files:
        print("   ⚠️  No hay PDFs en data/documentos/")
        print("   💡 Tip: Primero genera PDFs con el generador de datasets")
        return

    # Usar primer PDF
    pdf_path = str(pdf_files[0])
    print(f"   ✓ Usando: {pdf_path}")

    # 4. Indexar documento
    print("\n4️⃣  Indexando documento...")
    try:
        index = await indexer.index_document(pdf_path)
    except Exception as e:
        print(f"   ❌ Error indexando: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Mostrar resultado
    print("\n5️⃣  RESULTADO:")
    print("=" * 60)
    print(f"Document ID: {index['document_id']}")
    print(f"Title: {index['title']}")
    print(f"Category: {index['category']}")
    print(f"Total Pages: {index['total_pages']}")
    print(f"Sections: {len(index['sections'])}")
    print(f"\nGlobal Summary:")
    print(index['summary'])
    print(f"\nFirst Section:")
    if index['sections']:
        section = index['sections'][0]
        print(f"  - Pages: {section['page_range']}")
        print(f"  - Keywords: {', '.join(section['keywords'])}")
        print(f"  - Summary: {section['summary'][:200]}...")
    print("=" * 60)

    print("\n✅ Test completado!")
    print(f"📁 Índice guardado en: data/indices/{index['document_id']}.json")


if __name__ == "__main__":
    """
    Ejecutar test del indexer.

    PEDAGOGÍA:
    - Requiere tener PDFs en data/documentos/
    - Requiere VERTEX_AI_PROJECT configurado en .env
    - Genera índice JSON en data/indices/

    USO:
        python src/rag/agent_based/indexer.py
    """
    import asyncio

    asyncio.run(test_indexer())
