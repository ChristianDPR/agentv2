"""
SQL Query Tool - Ejecuta consultas SQL seguras

Tool para el Agente Buscador que permite consultas SELECT
a la base de datos con prevención de SQL injection.
"""

import re
from typing import Any, Dict, List, Tuple
from src.tools.checklist_tool import Tool, ToolDefinition
from src.agents.buscador.config import (
    ALLOWED_TABLES,
    ALLOWED_COLUMNS,
    FORBIDDEN_SQL_KEYWORDS,
    MAX_SQL_ROWS
)


def normalize_rut(rut: str) -> str:
    """
    Normaliza un RUT chileno quitando puntos.
    Ejemplo: '12.345.678-9' -> '12345678-9'
    """
    return rut.replace(".", "")


class SQLValidator:
    """Valida queries SQL contra whitelist de tablas y keywords."""

    def validate(self, query: str) -> Tuple[bool, str]:
        """
        Valida que una query SQL sea segura.

        Returns:
            (is_safe, error_message)
        """
        query_upper = query.upper().strip()

        # 1. Solo SELECT permitido
        if not query_upper.startswith("SELECT"):
            return False, "Solo consultas SELECT permitidas"

        # 2. Sin keywords peligrosos
        for keyword in FORBIDDEN_SQL_KEYWORDS:
            if keyword in query_upper:
                return False, f"Keyword prohibido: {keyword}"

        # 3. Verificar que usa tablas permitidas
        query_lower = query.lower()
        has_valid_table = False
        for table in ALLOWED_TABLES:
            if table in query_lower:
                has_valid_table = True
                break

        if not has_valid_table:
            return False, f"Tabla no permitida. Tablas válidas: {ALLOWED_TABLES}"

        return True, "OK"


class SQLQueryTool(Tool):
    """
    Tool para ejecutar consultas SQL seguras.

    Características:
    - Solo SELECT permitido
    - Whitelist de tablas y columnas
    - Prevención de SQL injection
    - Límite de resultados
    """

    def __init__(self, db_pool):
        """
        Args:
            db_pool: Pool de conexiones asyncpg
        """
        self.db_pool = db_pool
        self.validator = SQLValidator()

    @property
    def definition(self) -> ToolDefinition:
        tables_info = ", ".join(ALLOWED_TABLES)
        return ToolDefinition(
            name="sql_query",
            description=f"Ejecuta consultas SQL en la base de datos de AFP Integra. Solo SELECT permitido. Tablas disponibles: {tables_info}",
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
        """
        Normaliza RUTs chilenos en la query (quita puntos).
        Detecta patrones como '12.345.678-9' y los convierte a '12345678-9'.
        """
        # Patrón para RUT chileno con puntos: XX.XXX.XXX-X
        rut_pattern = r"'(\d{1,2}\.\d{3}\.\d{3}-[\dkK])'"

        def replace_rut(match):
            rut_with_dots = match.group(1)
            rut_normalized = normalize_rut(rut_with_dots)
            return f"'{rut_normalized}'"

        return re.sub(rut_pattern, replace_rut, query)

    async def execute(self, query: str) -> Dict[str, Any]:
        """
        Ejecuta una consulta SQL validada.

        Args:
            query: Consulta SQL (solo SELECT)

        Returns:
            Dict con results y count, o error si la query es inválida
        """
        # Normalizar RUTs en la query (quitar puntos)
        query = self._normalize_ruts_in_query(query)

        # Validar query
        is_safe, error = self.validator.validate(query)
        if not is_safe:
            return {
                "error": error,
                "query": query,
                "results": [],
                "count": 0
            }

        # Agregar LIMIT si no tiene
        query_upper = query.upper()
        if "LIMIT" not in query_upper:
            query = f"{query.rstrip(';')} LIMIT {MAX_SQL_ROWS}"

        # Ejecutar query
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query)

            results = [dict(row) for row in rows]
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
