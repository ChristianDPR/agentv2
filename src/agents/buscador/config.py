"""
Configuración del Agente Buscador

Define tablas, columnas permitidas y parámetros del loop ReAct.
"""

from typing import Dict, List, Set

# =============================================================================
# Configuración de Base de Datos (Whitelist para SQL Injection Prevention)
# =============================================================================

"""
ALLOWED_TABLES: Set[str] = {
    "afiliados",
    "aportes",
    "traspasos",
    "reclamos",
    "beneficiarios",
    "pensiones",
    "movimientos",
    "empleadores",
    # Vistas
    "vista_resumen_afiliado",
    "vista_empleadores_morosos"
}

ALLOWED_COLUMNS: Dict[str, List[str]] = {
    "afiliados": [
        "rut", "nombre", "apellido_paterno", "apellido_materno",
        "email", "telefono", "fecha_nacimiento", "fecha_afiliacion",
        "estado", "tipo_afiliado", "empleador", "renta_imponible",
        "fondo_actual", "saldo_obligatorio", "saldo_voluntario"
    ],
    "aportes": [
        "id", "afiliado_rut", "periodo", "monto", "fecha_pago",
        "tipo", "estado", "empleador", "comision", "seguro", "descripcion"
    ],
    "traspasos": [
        "id", "afiliado_rut", "afp_origen", "afp_destino",
        "monto_obligatorio", "monto_voluntario", "fecha_solicitud",
        "fecha_ejecucion", "estado", "motivo_rechazo", "numero_solicitud"
    ],
    "reclamos": [
        "id", "numero_ticket", "afiliado_rut", "tipo", "canal",
        "descripcion", "monto_reclamado", "prioridad", "estado",
        "resolucion", "fecha_creacion", "fecha_resolucion",
        "agente_asignado", "satisfaccion_cliente"
    ],
    "beneficiarios": [
        "id", "afiliado_rut", "rut_beneficiario", "nombre",
        "parentesco", "porcentaje_asignado", "es_invalido",
        "fecha_nacimiento", "vigente"
    ],
    "pensiones": [
        "id", "afiliado_rut", "tipo_pension", "modalidad",
        "monto_mensual", "fecha_inicio", "fecha_termino",
        "estado", "compania_seguros"
    ],
    "movimientos": [
        "id", "afiliado_rut", "tipo_movimiento", "monto",
        "saldo_anterior", "saldo_posterior", "fondo",
        "fecha_movimiento", "descripcion", "referencia_id"
    ],
    "empleadores": [
        "rut", "razon_social", "giro", "direccion", "comuna",
        "region", "estado", "deuda_total", "cantidad_trabajadores"
    ]
} 
"""
# =============================================================================
# Configuración de Base de Datos (BigQuery)
# Whitelist para SQL Injection Prevention
# =============================================================================

ALLOWED_TABLES: Set[str] = {
    "tmp_fprod_trs"
}

ALLOWED_COLUMNS: Dict[str, List[str]] = {
    "tmp_fprod_trs": [
        # Fecha
        "fecha",

        # Asesor
        "codigo_asesor",
        "apellido_paterno_asesor",
        "apellido_materno_asesor",
        "primer_nombre_asesor",
        "categoria_asesor",
        "oficina_asesor",
        "zona_asesor",
        "posicion_asesor",
        "canal",

        # Cliente
        "tipo_documento_cliente",
        "numerp_documento_cliente",
        "cuspp",
        "departamento_cliente",

        # Empleador
        "ruc_empleador",
        "razon_social_empleador",
        "departamento_empleador",

        # Métricas
        "remuneracion",
        "tipo_traspaso"
    ]
}


# Keywords SQL prohibidos
FORBIDDEN_SQL_KEYWORDS: Set[str] = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
    "CREATE", "TRUNCATE", "EXEC", "EXECUTE", "--", "/*"
}

# =============================================================================
# Configuración del Loop ReAct
# =============================================================================

# Máximo de iteraciones del loop
MAX_ITERATIONS: int = 10

# Máximo de repeticiones antes de detectar loop infinito
MAX_LOOP_REPEATS: int = 3

# Límite de resultados SQL
MAX_SQL_ROWS: int = 100

# =============================================================================
# Configuración de Filesystem
# =============================================================================

# Tipos de archivo permitidos
ALLOWED_FILE_TYPES: Set[str] = {"pdf", "txt", "docx"}

# Extensiones por tipo
FILE_EXTENSIONS: Dict[str, List[str]] = {
    "pdf": [".pdf"],
    "txt": [".txt"],
    "docx": [".docx", ".doc"]
}
