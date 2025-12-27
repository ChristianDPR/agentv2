"""
Configuración del Agente de Reclamos

PEDAGOGÍA:
- Centraliza todas las constantes de negocio en un solo lugar
- Facilita cambios sin modificar código de las tools
- Documenta las reglas de negocio AFP

Este archivo contiene:
- Categorías de reclamos
- Niveles de prioridad y SLAs
- Matriz de routing a departamentos
- Reglas de escalamiento
"""

from typing import Dict, List

# ============================================================================
# CATEGORÍAS DE RECLAMOS
# ============================================================================

CATEGORIES: Dict[str, Dict] = {
    "fraude": {
        "name": "Fraude",
        "description": "Cargos no autorizados, suplantación de identidad, accesos no reconocidos",
        "keywords": [
            "cargo no reconozco", "no autoricé", "fraude", "robo", "suplantación",
            "hackeo", "acceso no autorizado", "transacción fraudulenta", "estafa",
            "clonación", "phishing"
        ],
        "default_priority": "critical"
    },
    "legal": {
        "name": "Legal",
        "description": "Disputas legales, demandas, requerimientos judiciales",
        "keywords": [
            "demandar", "demanda", "abogado", "denuncia", "judicial", "indecopi",
            "sbs", "superintendencia", "carta notarial", "proceso legal"
        ],
        "default_priority": "high"
    },
    "operaciones": {
        "name": "Operaciones",
        "description": "Estados de cuenta, transacciones, consultas de saldo",
        "keywords": [
            "estado de cuenta", "saldo", "movimiento", "extracto", "consulta",
            "historial", "transacción", "operación"
        ],
        "default_priority": "normal"
    },
    "aportes": {
        "name": "Aportes",
        "description": "Aportes faltantes, descuentos incorrectos, regularizaciones",
        "keywords": [
            "aporte", "descuento", "empleador", "planilla", "cotización",
            "no aparece mi aporte", "falta aporte", "aporte incorrecto"
        ],
        "default_priority": "normal"
    },
    "jubilacion": {
        "name": "Jubilación",
        "description": "Trámites de pensión, retiro, jubilación anticipada",
        "keywords": [
            "jubilar", "jubilación", "pensión", "retiro", "vejez",
            "anticipada", "invalidez", "sobrevivencia"
        ],
        "default_priority": "normal"
    },
    "traspasos": {
        "name": "Traspasos",
        "description": "Cambio de AFP, transferencias entre administradoras",
        "keywords": [
            "traspaso", "cambiar de afp", "transferir", "otra afp",
            "cambio de administradora", "trasladar fondos"
        ],
        "default_priority": "normal"
    },
    "ti": {
        "name": "Soporte Técnico",
        "description": "Problemas con app, web, acceso a plataformas",
        "keywords": [
            "app", "aplicación", "no funciona", "error", "no puedo ingresar",
            "contraseña", "clave", "token", "página web", "sistema caído"
        ],
        "default_priority": "normal"
    },
    "atencion": {
        "name": "Atención al Cliente",
        "description": "Quejas de servicio, mala atención, tiempos de espera",
        "keywords": [
            "mala atención", "no me atienden", "demora", "espera",
            "queja", "reclamo servicio", "pésimo servicio", "maltrato"
        ],
        "default_priority": "low"
    }
}

# Lista simple de categorías para validación
CATEGORY_NAMES: List[str] = list(CATEGORIES.keys())


# ============================================================================
# NIVELES DE PRIORIDAD Y SLA
# ============================================================================

PRIORITY_LEVELS: List[str] = ["critical", "high", "normal", "low"]

SLA_RULES: Dict[str, Dict] = {
    "critical": {
        "hours": 4,
        "description": "Atención inmediata (4 horas)",
        "requires_escalation": True,
        "notification": "immediate"
    },
    "high": {
        "hours": 24,
        "description": "Atención prioritaria (24 horas)",
        "requires_escalation": False,
        "notification": "same_day"
    },
    "normal": {
        "hours": 72,
        "description": "Atención estándar (72 horas / 3 días hábiles)",
        "requires_escalation": False,
        "notification": "daily_digest"
    },
    "low": {
        "hours": 168,
        "description": "Atención general (168 horas / 7 días hábiles)",
        "requires_escalation": False,
        "notification": "weekly_digest"
    }
}


# ============================================================================
# MATRIZ DE ROUTING
# ============================================================================

ROUTING_MATRIX: Dict[str, Dict] = {
    "fraude": {
        "department": "seguridad",
        "queue": "fraude_urgente",
        "backup_department": "operaciones",
        "requires_verification": True
    },
    "legal": {
        "department": "legal",
        "queue": "disputas",
        "backup_department": None,
        "requires_verification": True
    },
    "operaciones": {
        "department": "operaciones",
        "queue": "general",
        "backup_department": "servicio_cliente",
        "requires_verification": False
    },
    "aportes": {
        "department": "operaciones",
        "queue": "aportes",
        "backup_department": "servicio_cliente",
        "requires_verification": False
    },
    "jubilacion": {
        "department": "pensiones",
        "queue": "tramites",
        "backup_department": "operaciones",
        "requires_verification": True
    },
    "traspasos": {
        "department": "traspasos",
        "queue": "solicitudes",
        "backup_department": "operaciones",
        "requires_verification": True
    },
    "ti": {
        "department": "soporte_tecnico",
        "queue": "incidentes",
        "backup_department": "servicio_cliente",
        "requires_verification": False
    },
    "atencion": {
        "department": "servicio_cliente",
        "queue": "quejas",
        "backup_department": None,
        "requires_verification": False
    }
}

# Departamentos disponibles
DEPARTMENTS: List[str] = [
    "seguridad",
    "legal",
    "operaciones",
    "pensiones",
    "traspasos",
    "soporte_tecnico",
    "servicio_cliente"
]


# ============================================================================
# REGLAS DE ESCALAMIENTO
# ============================================================================

ESCALATION_RULES: Dict[str, Dict] = {
    # Escalamiento por prioridad
    "priority_critical": {
        "condition": "priority == 'critical'",
        "action": "add_supervisor",
        "queue_suffix": "_supervisor",
        "notify": ["supervisor", "gerente_area"]
    },

    # Escalamiento específico para legal crítico
    "legal_critical": {
        "condition": "category == 'legal' and priority in ['critical', 'high']",
        "action": "escalate_to_management",
        "override_department": "legal",
        "override_queue": "gerencia_legal",
        "notify": ["gerente_legal", "compliance"]
    },

    # Escalamiento para fraude (siempre)
    "fraude_always": {
        "condition": "category == 'fraude'",
        "action": "security_protocol",
        "notify": ["seguridad", "antifraude"],
        "additional_actions": ["block_review", "identity_verification"]
    },

    # Escalamiento por canal presencial + crítico
    "presencial_critical": {
        "condition": "channel == 'presencial' and priority == 'critical'",
        "action": "immediate_attention",
        "notify": ["supervisor_agencia"],
        "sla_override_hours": 1
    }
}


# ============================================================================
# CANALES DE ORIGEN
# ============================================================================

CHANNELS: List[str] = [
    "app",          # Aplicación móvil
    "web",          # Portal web
    "presencial",   # Agencia física
    "call_center",  # Centro de llamadas
    "email",        # Correo electrónico
    "redes_sociales"  # Redes sociales
]


# ============================================================================
# CONFIGURACIÓN DEL MODELO
# ============================================================================

LLM_CONFIG = {
    "classifier": {
        "model_name": "gemini-2.0-flash",
        "temperature": 0.3,  # Baja para clasificación consistente
        "max_tokens": 1000
    }
}


# ============================================================================
# MENSAJES DE RESPUESTA
# ============================================================================

RESPONSE_TEMPLATES = {
    "critical": (
        "Su reclamo ha sido registrado con prioridad CRÍTICA. "
        "Será atendido en las próximas {sla_hours} horas por nuestro equipo de {department}. "
        "Un especialista se comunicará con usted a la brevedad."
    ),
    "high": (
        "Su reclamo ha sido registrado con prioridad ALTA. "
        "Será atendido en las próximas {sla_hours} horas por nuestro equipo de {department}."
    ),
    "normal": (
        "Su reclamo ha sido registrado. "
        "Será atendido en un plazo máximo de {sla_hours} horas ({sla_days} días hábiles) "
        "por nuestro equipo de {department}."
    ),
    "low": (
        "Su consulta ha sido registrada. "
        "Recibirá una respuesta en un plazo máximo de {sla_hours} horas ({sla_days} días hábiles)."
    )
}
