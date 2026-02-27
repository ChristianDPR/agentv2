"""
Report Upload Tool - Sube archivos (PNG/JPEG/CSV/etc.) a un bucket de GCS.

Permite al agente almacenar reportes generados (por ejemplo, gráficos).
"""

from pathlib import Path
from typing import Any, Dict

from google.cloud import storage

from src.tools.checklist_tool import Tool, ToolDefinition


class ReportUploadTool(Tool):
    """
    Tool para subir un archivo local a Google Cloud Storage.
    """

    def __init__(self, gcs_client: storage.Client):
        self.client = gcs_client

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="upload_report",
            description=(
                "Sube un archivo (PNG/JPEG/CSV/etc.) a un bucket de GCS. "
                "Requiere ruta local, nombre de bucket y ruta destino."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Ruta local del archivo a subir"
                    },
                    "bucket_name": {
                        "type": "string",
                        "description": "Nombre del bucket GCS"
                    },
                    "object_path": {
                        "type": "string",
                        "description": "Ruta destino dentro del bucket (ej: reports/demo.png)"
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Content-Type opcional (ej: image/png)",
                        "default": ""
                    }
                },
                "required": ["file_path", "bucket_name", "object_path"]
            }
        )

    async def execute(
        self,
        file_path: str,
        bucket_name: str,
        object_path: str,
        content_type: str = ""
    ) -> Dict[str, Any]:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return {
                "error": "Archivo no existe",
                "file_path": file_path,
                "bucket": bucket_name,
                "object_path": object_path
            }

        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(object_path)

        blob.upload_from_filename(file_path_obj, content_type=content_type or None)

        return {
            "file_path": str(file_path_obj),
            "bucket": bucket_name,
            "object_path": object_path,
            "gcs_uri": f"gs://{bucket_name}/{object_path}"
        }
