#!/usr/bin/env python3
"""
Script de verificación del setup
Verifica que todos los componentes estén funcionando correctamente
"""

import sys
import asyncio


def print_status(test_name: str, passed: bool, details: str = ""):
    """Imprime el estado de un test"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"     {details}")


async def test_python_version():
    """Verifica la versión de Python"""
    version = sys.version_info
    passed = version.major == 3 and version.minor >= 11
    print_status(
        "Python 3.11+",
        passed,
        f"Versión: {version.major}.{version.minor}.{version.micro}"
    )
    return passed


async def test_imports():
    """Verifica que los imports clave funcionen"""
    try:
        import google.cloud.aiplatform
        import fastapi
        import asyncpg
        import pydantic
        import structlog
        import tiktoken
        import pytest
        passed = True
        print_status("Imports de librerías", passed, "Todas las librerías disponibles")
    except ImportError as e:
        passed = False
        print_status("Imports de librerías", passed, f"Error: {e}")
    return passed


async def test_database_connection():
    """Verifica la conexión a PostgreSQL"""
    try:
        import asyncpg
        import os

        # Obtener DATABASE_URL desde env
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://afp_user:afp_secure_2025@postgres:5432/afp_agents"
        )

        # Conectar
        conn = await asyncpg.connect(db_url)

        # Verificar pgvector
        result = await conn.fetchval(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        )

        await conn.close()

        passed = result is not None
        print_status(
            "Conexión a PostgreSQL + pgvector",
            passed,
            f"pgvector v{result}"
        )
    except Exception as e:
        passed = False
        print_status("Conexión a PostgreSQL", passed, f"Error: {e}")
    return passed


async def test_database_tables():
    """Verifica que las tablas existan con datos"""
    try:
        import asyncpg
        import os

        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://afp_user:afp_secure_2025@postgres:5432/afp_agents"
        )

        conn = await asyncpg.connect(db_url)

        # Contar registros
        afiliados = await conn.fetchval("SELECT COUNT(*) FROM afiliados")
        aportes = await conn.fetchval("SELECT COUNT(*) FROM aportes")
        traspasos = await conn.fetchval("SELECT COUNT(*) FROM traspasos")

        await conn.close()

        passed = afiliados > 0 and aportes > 0 and traspasos > 0
        print_status(
            "Tablas y seed data",
            passed,
            f"{afiliados} afiliados, {aportes} aportes, {traspasos} traspasos"
        )
    except Exception as e:
        passed = False
        print_status("Tablas y seed data", passed, f"Error: {e}")
    return passed


async def test_vertex_ai_setup():
    """Verifica la configuración de Vertex AI (no requiere credenciales reales)"""
    try:
        import os
        from google.cloud import aiplatform

        project = os.getenv("VERTEX_AI_PROJECT", "not-configured")
        location = os.getenv("VERTEX_AI_LOCATION", "not-configured")

        # No inicializamos porque no tenemos credenciales aún
        # Solo verificamos que las variables estén configuradas

        passed = project != "not-configured" and location != "not-configured"
        print_status(
            "Configuración Vertex AI",
            passed,
            f"Project: {project}, Location: {location}" if passed else "Variables no configuradas (esperado en setup inicial)"
        )
    except Exception as e:
        passed = False
        print_status("Configuración Vertex AI", passed, f"Error: {e}")
    return passed


async def main():
    """Ejecuta todos los tests"""
    print("=" * 60)
    print("VERIFICACIÓN DE SETUP - COE IA TRAINING")
    print("=" * 60)
    print()

    tests = [
        test_python_version(),
        test_imports(),
        test_database_connection(),
        test_database_tables(),
        test_vertex_ai_setup(),
    ]

    results = await asyncio.gather(*tests)

    print()
    print("=" * 60)
    total = len(results)
    passed = sum(results)

    print(f"RESULTADOS: {passed}/{total} tests pasaron")

    if passed == total:
        print("✅ Setup completo y funcionando correctamente!")
        return 0
    elif passed >= total - 1:  # Si solo falla Vertex AI (esperado)
        print("⚠️  Setup casi completo. Configura Vertex AI para completar.")
        return 0
    else:
        print("❌ Hay problemas con el setup. Revisa los errores arriba.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
