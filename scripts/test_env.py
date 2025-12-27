#!/usr/bin/env python3
"""Script para validar configuración de entorno"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("VALIDACIÓN DE CONFIGURACIÓN")
print("=" * 60)

# 1. Verificar .env
env_path = project_root / ".env"
print(f"\n1. Verificando archivo .env:")
print(f"   Path: {env_path}")
print(f"   Existe: {env_path.exists()}")

if env_path.exists():
    print(f"   Tamaño: {env_path.stat().st_size} bytes")
    print(f"\n   Contenido relevante:")
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                print(f"   {line.strip()}")

# 2. Cargar .env
print(f"\n2. Cargando variables de entorno:")
load_dotenv(dotenv_path=env_path, override=True)
print("   ✓ load_dotenv() ejecutado (con override=True)")

# 3. Verificar variables
print(f"\n3. Variables de entorno cargadas:")
vertex_project = os.getenv("VERTEX_AI_PROJECT")
vertex_location = os.getenv("VERTEX_AI_LOCATION")
vertex_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
llm_model = os.getenv("DEFAULT_LLM_MODEL")

print(f"   VERTEX_AI_PROJECT: {vertex_project}")
print(f"   VERTEX_AI_LOCATION: {vertex_location}")
print(f"   GOOGLE_APPLICATION_CREDENTIALS: {vertex_creds}")
print(f"   DEFAULT_LLM_MODEL: {llm_model}")

# 4. Intentar inicializar VertexAIProvider
print(f"\n4. Intentando inicializar VertexAIProvider:")
try:
    from src.framework.model_provider import VertexAIProvider
    provider = VertexAIProvider()
    print(f"   ✓ VertexAIProvider inicializado")
    print(f"   - project_id: {provider.project_id}")
    print(f"   - location: {provider.location}")
    print(f"   - model_name: {provider.model_name}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 60)
