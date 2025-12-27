"""
Document Tools - Herramientas para filesystem

Tools para el Agente Buscador:
- ListDocumentsTool: Lista documentos disponibles (como ls/tree)
- ReadDocumentTool: Lee el contenido de un documento específico
"""

from typing import Any, Dict, List
from pathlib import Path
import os
import re

from src.tools.checklist_tool import Tool, ToolDefinition
from src.agents.buscador.config import ALLOWED_FILE_TYPES, FILE_EXTENSIONS


class PathValidator:
    """Valida paths para prevenir path traversal."""

    def __init__(self, base_path: Path):
        self.base_path = base_path.resolve()

    def validate(self, path: str) -> bool:
        """Verifica que el path esté dentro del directorio base."""
        try:
            resolved = (self.base_path / path).resolve()
            return resolved.is_relative_to(self.base_path)
        except Exception:
            return False


class ListDocumentsTool(Tool):
    """
    Lista documentos disponibles en el filesystem (como ls/tree).

    NO devuelve contenido, solo nombres y metadata.
    Útil para que el agente sepa qué documentos existen antes de leerlos.
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path).resolve()
        self.path_validator = PathValidator(self.base_path)

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_documents",
            description=(
                "Lista los documentos disponibles en el sistema de archivos. "
                "Similar a 'ls' o 'tree'. Devuelve nombres y metadata, NO el contenido. "
                "Usa filter_pattern para filtrar por nombre (ej: 'certificado', '12345678-9')."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "filter_pattern": {
                        "type": "string",
                        "description": "Patrón opcional para filtrar nombres de archivo (texto o regex). Dejar vacío para listar todos.",
                        "default": ""
                    },
                    "file_type": {
                        "type": "string",
                        "enum": ["pdf", "txt", "docx", "all"],
                        "description": "Tipo de archivo a listar",
                        "default": "all"
                    }
                },
                "required": []
            }
        )

    async def execute(
        self,
        filter_pattern: str = "",
        file_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Lista documentos disponibles.

        Args:
            filter_pattern: Patrón opcional para filtrar por nombre
            file_type: Tipo de archivo (pdf, txt, docx, all)

        Returns:
            Dict con lista de documentos (nombre, tamaño, tipo)
        """
        if not self.base_path.exists():
            return {
                "error": "Directorio de documentos no existe",
                "documents": [],
                "count": 0
            }

        # Determinar extensiones
        if file_type == "all":
            extensions = []
            for exts in FILE_EXTENSIONS.values():
                extensions.extend(exts)
        else:
            extensions = FILE_EXTENSIONS.get(file_type, [])

        # Preparar filtro
        pattern_regex = None
        if filter_pattern:
            try:
                pattern_regex = re.compile(filter_pattern, re.IGNORECASE)
            except re.error:
                pattern_regex = re.compile(re.escape(filter_pattern), re.IGNORECASE)

        # Listar archivos
        documents = []

        for root, dirs, files in os.walk(self.base_path):
            for filename in files:
                # Filtrar por extensión
                if extensions and not any(filename.lower().endswith(ext) for ext in extensions):
                    continue

                # Filtrar por patrón
                if pattern_regex and not pattern_regex.search(filename):
                    continue

                file_path = Path(root) / filename
                rel_path = file_path.relative_to(self.base_path)

                if not self.path_validator.validate(str(rel_path)):
                    continue

                stat = file_path.stat()

                # Extraer tipo de documento del nombre
                doc_type = "unknown"
                if "certificado" in filename.lower():
                    doc_type = "certificado"
                elif "traspaso" in filename.lower():
                    doc_type = "traspaso"
                elif "reclamo" in filename.lower():
                    doc_type = "reclamo"
                elif "pension" in filename.lower():
                    doc_type = "pension"
                elif "beneficiario" in filename.lower():
                    doc_type = "beneficiarios"
                elif "cobranza" in filename.lower():
                    doc_type = "cobranza"

                documents.append({
                    "filename": filename,
                    "type": doc_type,
                    "size_bytes": stat.st_size,
                    "extension": file_path.suffix
                })

        # Ordenar por nombre
        documents.sort(key=lambda d: d["filename"])

        return {
            "filter_pattern": filter_pattern or "(ninguno)",
            "file_type": file_type,
            "documents": documents,
            "count": len(documents),
            "hint": "Usa read_document(filename) para leer el contenido de un documento específico"
        }


class ReadDocumentTool(Tool):
    """
    Lee el contenido completo de un documento específico.

    Requiere el nombre exacto del archivo (obtenido de list_documents).
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path).resolve()
        self.path_validator = PathValidator(self.base_path)

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_document",
            description=(
                "Lee el contenido completo de un documento específico. "
                "Requiere el nombre exacto del archivo (usar list_documents primero para ver qué hay disponible)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Nombre exacto del archivo a leer (ej: 'certificado_12345678-9_2024.txt')"
                    }
                },
                "required": ["filename"]
            }
        )

    async def execute(self, filename: str) -> Dict[str, Any]:
        """
        Lee el contenido de un documento.

        Args:
            filename: Nombre del archivo a leer

        Returns:
            Dict con el contenido del documento
        """
        # Validar path
        if not self.path_validator.validate(filename):
            return {
                "error": "Nombre de archivo inválido o intento de path traversal",
                "filename": filename
            }

        file_path = self.base_path / filename

        if not file_path.exists():
            # Intentar buscar el archivo (por si hay subdirectorios)
            found = None
            for root, dirs, files in os.walk(self.base_path):
                if filename in files:
                    found = Path(root) / filename
                    break

            if not found:
                return {
                    "error": f"Documento '{filename}' no encontrado",
                    "filename": filename,
                    "hint": "Usa list_documents() para ver los documentos disponibles"
                }
            file_path = found

        # Leer contenido
        try:
            if file_path.suffix.lower() == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                return {
                    "filename": filename,
                    "content": content,
                    "size_bytes": len(content),
                    "lines": content.count("\n") + 1
                }
            else:
                return {
                    "filename": filename,
                    "error": f"Solo se pueden leer archivos .txt (archivo es {file_path.suffix})",
                    "hint": "Los archivos PDF y DOCX requieren procesamiento especial"
                }

        except Exception as e:
            return {
                "error": f"Error leyendo documento: {str(e)}",
                "filename": filename
            }


# Alias para compatibilidad con código existente
class DocumentSearchTool(ListDocumentsTool):
    """Alias para compatibilidad. Usa ListDocumentsTool o ReadDocumentTool."""
    pass
