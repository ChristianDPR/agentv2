"""
Lectura directa de documentos para Agent RAG

A diferencia del Vector RAG, aquí NO usamos embeddings.
El LLM lee los documentos directamente.

PEDAGOGÍA:
- Soporte multi-formato: Markdown, PDF, TXT, DOCX
- Extracción de metadata robusta con fallbacks
- No depende de formato específico de headers
- Fácil de extender para nuevos formatos
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import re


class DocumentReader:
    """
    Lee documentos de múltiples formatos sin procesamiento vectorial.

    PEDAGOGÍA:
    - Soporte para: .md, .pdf, .txt, .docx
    - Extracción de metadata robusta con fallbacks inteligentes
    - No depende de formato específico de headers
    - Agent RAG lee documentos completos (no chunks)

    VENTAJAS:
    - Fácil agregar PDFs sin romper nada
    - Metadata se infiere del path y nombre si no hay headers
    - Extensible: agregar nuevo formato = agregar método _read_xxx()
    """

    # Formatos soportados
    SUPPORTED_EXTENSIONS = {'.md', '.txt', '.pdf', '.docx'}

    async def read_all_documents(self, path: str = "data/documentos") -> List[Dict[str, Any]]:
        """
        Carga todos los documentos del directorio (multi-formato).

        DIFERENCIA CON VECTOR RAG:
        - No hace chunking, mantiene documentos completos
        - No genera embeddings
        - Solo lectura y extracción de metadata

        PEDAGOGÍA:
        - Soporta .md, .pdf, .txt, .docx automáticamente
        - Metadata se extrae del contenido O se infiere del path
        - Fallbacks robustos: si no hay headers, usa nombre de archivo

        Args:
            path: Ruta al directorio de documentos

        Returns:
            Lista de dicts con content completo y metadata
        """
        docs_path = Path(path)
        if not docs_path.exists():
            raise FileNotFoundError(f"Directorio no existe: {path}")

        documents = []

        # Recorrer todos los archivos soportados
        for file_path in docs_path.rglob("*"):
            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            try:
                # Leer contenido según formato
                content = self._read_file(file_path)

                if not content or not content.strip():
                    continue  # Skip archivos vacíos

                # Extraer metadata con fallbacks inteligentes
                metadata = self._extract_metadata_robust(content, file_path)

                # Generar ID único (prioridad: procedure_code > nombre archivo)
                doc_id = metadata.get("procedure_code") or file_path.stem

                documents.append({
                    "id": doc_id,
                    "content": content,  # Documento COMPLETO (no chunks)
                    "metadata": metadata
                })

            except Exception as e:
                # Log error pero continuar con otros archivos
                print(f"⚠️  Error leyendo {file_path.name}: {e}")
                continue

        return documents

    def _read_file(self, file_path: Path) -> str:
        """
        Lee archivo según su extensión.

        PEDAGOGÍA:
        - Abstrae la lectura por tipo de archivo
        - Fácil agregar nuevos formatos: agregar elif con método _read_xxx()
        """
        ext = file_path.suffix.lower()

        if ext == '.md' or ext == '.txt':
            return self._read_text(file_path)
        elif ext == '.pdf':
            return self._read_pdf(file_path)
        elif ext == '.docx':
            return self._read_docx(file_path)
        else:
            # Fallback: intentar leer como texto
            return self._read_text(file_path)

    def _read_text(self, file_path: Path) -> str:
        """Lee archivos de texto plano (.md, .txt)"""
        return file_path.read_text(encoding="utf-8")

    def _read_pdf(self, file_path: Path) -> str:
        """
        Lee archivos PDF y extrae texto.

        PEDAGOGÍA:
        - Usa PyMuPDF (fitz) para extracción robusta de texto
        - Mantiene estructura de páginas
        - Rápido y eficiente en memoria

        NOTE: Requiere: pip install PyMuPDF
        """
        try:
            import fitz
        except ImportError:
            raise ImportError(
                "PyMuPDF no está instalado. "
                "Ejecuta: pip install PyMuPDF"
            )

        text_parts = []
        doc = fitz.open(file_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text and page_text.strip():
                text_parts.append(f"--- Página {page_num + 1} ---\n{page_text}")

        doc.close()
        return "\n\n".join(text_parts)

    def read_pdf_pages(self, file_path: Path, page_start: int, page_end: int) -> str:
        """
        Lee solo páginas específicas de un PDF.

        PEDAGOGÍA:
        - Extracción eficiente: solo lee páginas necesarias
        - Más rápido que leer documento completo
        - Reduce tokens enviados al LLM

        Args:
            file_path: Ruta al archivo PDF
            page_start: Página inicial (1-indexed)
            page_end: Página final (1-indexed, inclusiva)

        Returns:
            Texto de las páginas especificadas

        Example:
            # Leer páginas 5-8 de un PDF
            text = reader.read_pdf_pages(Path("doc.pdf"), 5, 8)
        """
        try:
            import fitz
        except ImportError:
            raise ImportError(
                "PyMuPDF no está instalado. "
                "Ejecuta: pip install PyMuPDF"
            )

        doc = fitz.open(file_path)
        total_pages = len(doc)

        # Validar rangos
        if page_start < 1 or page_end > total_pages:
            doc.close()
            raise ValueError(
                f"Rango de páginas inválido: {page_start}-{page_end} "
                f"(documento tiene {total_pages} páginas)"
            )

        text_parts = []

        # Convertir a 0-indexed para fitz
        for page_num in range(page_start - 1, page_end):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text and page_text.strip():
                # Incluir número de página para contexto
                text_parts.append(f"--- Página {page_num + 1} ---\n{page_text}")

        doc.close()
        return "\n\n".join(text_parts)

    def _read_docx(self, file_path: Path) -> str:
        """
        Lee archivos DOCX y extrae texto.

        NOTE: Requiere: pip install python-docx
        """
        try:
            from docx import Document
        except ImportError:
            raise ImportError(
                "python-docx no está instalado. "
                "Ejecuta: pip install python-docx"
            )

        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)

    def get_document_summary(self, doc: Dict[str, Any], max_chars: int = 500) -> str:
        """
        Genera un resumen corto del documento.

        Útil para mostrar al LLM una "vista previa" antes de
        procesar el documento completo.

        Args:
            doc: Documento con content y metadata
            max_chars: Máximo de caracteres del resumen

        Returns:
            Resumen del documento
        """
        content = doc["content"]
        metadata = doc["metadata"]

        # Primera parte del contenido
        preview = content[:max_chars]
        if len(content) > max_chars:
            preview += "..."

        # Agregar metadata importante
        summary = f"""
Documento: {metadata.get('procedure_name', 'Sin nombre')}
Código: {metadata.get('procedure_code', 'N/A')}
Categoría: {metadata.get('category', 'general')}

Contenido (preview):
{preview}
"""
        return summary.strip()

    def _extract_metadata_robust(self, content: str, file_path: Path) -> Dict[str, Any]:
        """
        Extrae metadata con fallbacks inteligentes.

        PEDAGOGÍA:
        - Intenta extraer del contenido (headers, títulos, etc.)
        - Si no encuentra, infiere del path y nombre de archivo
        - Funciona con cualquier formato (MD, PDF, TXT, DOCX)
        - No requiere estructura específica de headers

        FALLBACKS INTELIGENTES:
        1. Busca headers explícitos (PROCEDIMIENTO:, CÓDIGO:, etc.)
        2. Si no encuentra, usa nombre de archivo como procedure_code
        3. Categoría se infiere del path (carpeta parent)
        4. Para PDFs: extrae metadata del documento si está disponible

        Args:
            content: Contenido del documento
            file_path: Path al archivo

        Returns:
            Dict con metadata extraído + inferido
        """
        # Metadata base inferido del filesystem
        metadata = {
            "source": file_path.name,
            "category": self._infer_category(file_path),
            "path": str(file_path),
            "format": file_path.suffix.lower()
        }

        # Intento 1: Extraer headers explícitos (MD style)
        headers_found = self._extract_headers(content)
        metadata.update(headers_found)

        # Intento 2: Si no hay procedure_code, inferir del nombre de archivo
        if not metadata.get("procedure_code"):
            metadata["procedure_code"] = self._infer_procedure_code(file_path)

        # Intento 3: Si no hay procedure_name, inferir del título o nombre
        if not metadata.get("procedure_name"):
            metadata["procedure_name"] = self._infer_procedure_name(content, file_path)

        return metadata

    def _extract_headers(self, content: str) -> Dict[str, str]:
        """
        Extrae headers explícitos del contenido.

        PEDAGOGÍA:
        - Busca patrones comunes: "CAMPO: valor" o "**CAMPO**: valor"
        - Limpia markdown bold automáticamente
        - Regex flexible que funciona con múltiples formatos
        """
        headers = {}

        # Patrones a buscar (case-insensitive, con/sin bold)
        patterns = {
            "procedure_name": r'(?:\*\*)?PROCEDIMIENTO(?:\*\*)?\s*:\s*(.+)',
            "procedure_code": r'(?:\*\*)?C[ÓO]DIGO(?:\*\*)?\s*:\s*(.+)',
            "version": r'(?:\*\*)?VERSI[ÓO]N(?:\*\*)?\s*:\s*(.+)',
            "date": r'(?:\*\*)?FECHA(?:\*\*)?\s*:\s*(.+)',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                # Limpiar markdown adicional
                value = value.replace("**", "").replace("__", "")
                headers[field] = value

        return headers

    def _infer_category(self, file_path: Path) -> str:
        """
        Infiere categoría del path.

        PEDAGOGÍA:
        - Si el archivo está en data/documentos/jubilacion/doc.md → category = "jubilacion"
        - Si está en la raíz de documentos → category = "general"

        Ejemplos:
        - data/documentos/jubilacion/proc-jub-002.md → "jubilacion"
        - data/documentos/traspasos/proc-tras-001.pdf → "traspasos"
        - data/documentos/doc.md → "general"
        """
        parent_name = file_path.parent.name

        # Si parent es "documentos", es categoría general
        if parent_name == "documentos":
            return "general"

        return parent_name

    def _infer_procedure_code(self, file_path: Path) -> str:
        """
        Infiere código de procedimiento del nombre de archivo.

        PEDAGOGÍA:
        - Busca patrones como: proc-xxx-nnn, PROC-XXX-NNN
        - Si no encuentra, usa el nombre del archivo completo

        Ejemplos:
        - proc-jub-002.md → "PROC-JUB-002"
        - Jubilacion_Anticipada.pdf → "JUBILACION-ANTICIPADA"
        - documento.txt → "DOCUMENTO"
        """
        stem = file_path.stem

        # Buscar patrón proc-xxx-nnn (case-insensitive)
        match = re.search(r'proc-(\w+)-(\d+)', stem, re.IGNORECASE)
        if match:
            category_abbr = match.group(1).upper()
            number = match.group(2)
            return f"PROC-{category_abbr}-{number}"

        # Fallback: normalizar nombre de archivo
        normalized = stem.replace("_", "-").replace(" ", "-").upper()
        return normalized

    def _infer_procedure_name(self, content: str, file_path: Path) -> str:
        """
        Infiere nombre del procedimiento del contenido o nombre de archivo.

        PEDAGOGÍA:
        - Busca primer título (# Title en MD, título grande en texto)
        - Si no encuentra, usa nombre de archivo humanizado

        Ejemplos:
        - "# Jubilación Anticipada" → "Jubilación Anticipada"
        - "proc-jub-002.md" → "Proc Jub 002"
        """
        # Intento 1: Buscar primer título markdown (# Title)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()

        # Intento 2: Buscar línea que parezca título (corta, al inicio, uppercase)
        lines = content.split("\n")
        for line in lines[:10]:  # Solo primeras 10 líneas
            clean_line = line.strip()
            if 10 < len(clean_line) < 100 and clean_line[0].isupper():
                return clean_line

        # Fallback: humanizar nombre de archivo
        stem = file_path.stem
        humanized = stem.replace("_", " ").replace("-", " ").title()
        return humanized
