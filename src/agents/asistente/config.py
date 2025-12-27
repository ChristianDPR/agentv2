"""
Configuración del Agente Asistente

PEDAGOGÍA:
- Centralizar configuraciones facilita ajustes sin modificar código
- Los participantes aprenden a separar config de lógica
- Model names configurables desde .env
"""

import os

# Configuración del LLM para diferentes tareas
LLM_CONFIG = {
    # Para respuestas rápidas (Agente Principal)
    "fast": {
        "model_name": os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash"),
        "temperature": 0.7,
        "max_tokens": 3000
    },
    # Para tareas complejas (Agent RAG, evaluación)
    "complex": {
        "model_name": os.getenv("DEFAULT_LLM_MODEL_COMPLEX", "gemini-2.5-pro"),
        "temperature": 0.5,
        "max_tokens": 5000
    }
}

# Configuración de Retrieval
RETRIEVAL_CONFIG = {
    "vector_rag": {
        "top_k": 5,
        "chunk_size": 512,
        "overlap": 50
    },
    "agent_rag": {
        "top_k": 3,  # Menos porque es más lento
        "max_docs": 10  # Máximo documentos a evaluar
    }
}

# Configuración de Checklist
CHECKLIST_CONFIG = {
    "temperature": 0.3,  # Baja para consistencia
    "max_tokens": 4000
}

# Keywords para detectar necesidad de checklist
CHECKLIST_KEYWORDS = [
    "cómo", "como",
    "pasos", "paso a paso",
    "proceso", "procedimiento",
    "requisitos", "qué necesito", "que necesito",
    "documentos necesarios", "cómo tramitar"
]
