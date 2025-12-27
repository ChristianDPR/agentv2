
import re
from typing import Any, Dict, Tuple

from google.cloud import bigquery

from src.tools.checklist_tool import Tool, ToolDefinition
from src.agents.buscador.config import (
    ALLOWED_TABLES,
    FORBIDDEN_SQL_KEYWORDS,
    MAX_SQL_ROWS
)


def normalize_rut(rut: str) -> str:
    return rut.replace(".", "")


class SQLValidator:
    """Valida queries SQL contra whitelist (agnóstico al motor)."""

    def validate(self, query: str) -> Tuple[bool, str]:
        query_upper = query.upper().strip()

        # 1. Solo SELECT
        if not query_upper.startswith("SELECT"):
            return False, "Solo consultas SELECT permitidas"

        # 2. Keywords prohibidas
        for keyword in FORBIDDEN_SQL_KEYWORDS:
            if keyword in query_upper:
                return False, f"Keyword prohibido: {keyword}"

        # 3. Tablas permitidas
        query_lower = query.lower()
        if not any(table in query_lower for table in ALLOWED_TABLES):
            return False, f"Tabla no permitida. Tablas válidas: {ALLOWED_TABLES}"

        return True, "OK"


class BigQuerySQLQueryTool(Tool):
    """
    Tool SQL para BigQuery.
    Drop-in replacement de SQLQueryTool.
    """

    def __init__(
        self,
        bq_client: bigquery.Client,
        default_dataset: str | None = None
    ):
        self.client = bq_client
        self.default_dataset = default_dataset
        self.validator = SQLValidator()

    @property
    def definition(self) -> ToolDefinition:
        tables_info = ", ".join(ALLOWED_TABLES)
        return ToolDefinition(
            name="sql_query",  # 👈 IMPORTANTE: mismo nombre
            description=(
                "Ejecuta consultas SQL en BigQuery. "
                f"Solo SELECT permitido. Tablas disponibles: {tables_info}"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": f"Consulta SQL (solo SELECT). Tablas: {tables_info}"
                    }
                },
                "required": ["query"]
            }
        )

    def _normalize_ruts_in_query(self, query: str) -> str:
        rut_pattern = r"'(\d{1,2}\.\d{3}\.\d{3}-[\dkK])'"

        def replace(match):
            return f"'{normalize_rut(match.group(1))}'"

        return re.sub(rut_pattern, replace, query)

    async def execute(self, query: str) -> Dict[str, Any]:
        # Normalizar RUTs
        query = self._normalize_ruts_in_query(query)

        # Validar SQL
        is_safe, error = self.validator.validate(query)
        if not is_safe:
            return {
                "error": error,
                "query": query,
                "results": [],
                "count": 0
            }

        # LIMIT defensivo
        if "LIMIT" not in query.upper():
            query = f"{query.rstrip(';')} LIMIT {MAX_SQL_ROWS}"

        try:
            job_config = bigquery.QueryJobConfig()
            if self.default_dataset:
                job_config.default_dataset = self.default_dataset

            job = self.client.query(query, job_config=job_config)
            rows = list(job.result())

            results = [dict(row.items()) for row in rows]

            return {
                "query": query,
                "results": results,
                "count": len(results)
            }

        except Exception as e:
            return {
                "error": str(e),
                "query": query,
                "results": [],
                "count": 0
            }
