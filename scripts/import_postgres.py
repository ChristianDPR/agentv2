#!/usr/bin/env python3
"""
Script: import_postgres.py
Descripción: Importa la imagen de PostgreSQL+pgvector (distribución offline)
Uso: python scripts/import_postgres.py
Compatible con: Windows, Mac, Linux
"""

import subprocess
import sys
from pathlib import Path
import gzip
import shutil


class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

    @classmethod
    def disable_on_windows(cls):
        if sys.platform == 'win32':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except:
                cls.GREEN = cls.YELLOW = cls.RED = cls.NC = ''


Colors.disable_on_windows()


def run_command(cmd, capture_output=False):
    """Ejecuta un comando del sistema"""
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=True)
            return None
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.NC}")
        sys.exit(1)


def main():
    POSTGRES_IMAGE = "pgvector/pgvector:pg16"
    DIST_DIR = Path("dist")
    COMPRESSED_FILE = DIST_DIR / "pgvector-pg16.tar.gz"
    UNCOMPRESSED_FILE = DIST_DIR / "pgvector-pg16.tar"

    print(f"{Colors.GREEN}=== Importación de PostgreSQL + pgvector ==={Colors.NC}\n")

    # 1. Verificar archivo
    print(f"{Colors.YELLOW}[1/3] Verificando archivo...{Colors.NC}")
    if not COMPRESSED_FILE.exists():
        print(f"{Colors.RED}❌ Error: No se encuentra {COMPRESSED_FILE}{Colors.NC}")
        sys.exit(1)

    file_size_mb = COMPRESSED_FILE.stat().st_size / (1024 ** 2)
    print(f"{Colors.GREEN}✓ Archivo encontrado{Colors.NC}")
    print(f"  Tamaño: {file_size_mb:.2f} MB")

    # 2. Descomprimir
    print(f"\n{Colors.YELLOW}[2/3] Descomprimiendo...{Colors.NC}")
    with gzip.open(COMPRESSED_FILE, 'rb') as f_in:
        with open(UNCOMPRESSED_FILE, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    print(f"{Colors.GREEN}✓ Descomprimido{Colors.NC}")

    # 3. Cargar imagen
    print(f"\n{Colors.YELLOW}[3/3] Cargando imagen en Docker...{Colors.NC}")
    run_command(f"docker load -i {UNCOMPRESSED_FILE}")
    print(f"{Colors.GREEN}✓ Imagen cargada{Colors.NC}")

    # Verificar
    try:
        run_command(f"docker image inspect {POSTGRES_IMAGE}", capture_output=True)
        print(f"{Colors.GREEN}✓ Imagen disponible: {POSTGRES_IMAGE}{Colors.NC}")
    except:
        print(f"{Colors.RED}❌ Error: La imagen no se cargó correctamente{Colors.NC}")
        sys.exit(1)

    # Limpiar
    UNCOMPRESSED_FILE.unlink()
    print(f"\n{Colors.GREEN}=== ✅ Importación Completada ==={Colors.NC}")


if __name__ == "__main__":
    main()
