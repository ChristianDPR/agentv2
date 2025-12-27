#!/usr/bin/env python3
"""
Script: import_image.py
Descripción: Importa la imagen Docker del dev container (distribución offline)
Uso: python scripts/import_image.py
Compatible con: Windows, Mac, Linux
"""

import subprocess
import sys
from pathlib import Path
import gzip
import shutil


class Colors:
    """ANSI colors (funcionan en Windows 10+ con terminal moderno)"""
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
        print(f"{Colors.RED}❌ Error ejecutando comando: {cmd}{Colors.NC}")
        print(f"{Colors.RED}{e}{Colors.NC}")
        sys.exit(1)


def get_image_size(image_name):
    """Obtiene el tamaño de una imagen Docker en GB"""
    try:
        cmd = f'docker image inspect {image_name} --format="{{{{.Size}}}}"'
        size_bytes = int(run_command(cmd, capture_output=True))
        size_gb = size_bytes / (1024 ** 3)
        return size_gb
    except:
        return 0.0


def main():
    IMAGE_NAME = "coe-ia-training"
    IMAGE_TAG = "latest"
    FULL_IMAGE = f"{IMAGE_NAME}:{IMAGE_TAG}"
    DIST_DIR = Path("dist")
    COMPRESSED_FILE = DIST_DIR / f"{IMAGE_NAME}-{IMAGE_TAG}.tar.gz"
    UNCOMPRESSED_FILE = DIST_DIR / f"{IMAGE_NAME}-{IMAGE_TAG}.tar"

    print(f"{Colors.GREEN}=== Importación de Imagen Docker para COE IA Training ==={Colors.NC}\n")

    # 1. Verificar que el archivo existe
    print(f"{Colors.YELLOW}[1/4] Verificando archivo de imagen...{Colors.NC}")
    if not COMPRESSED_FILE.exists():
        print(f"{Colors.RED}❌ Error: No se encuentra el archivo {COMPRESSED_FILE}{Colors.NC}")
        print(f"{Colors.YELLOW}Asegúrate de haber copiado el archivo desde el USB/Drive a la carpeta dist/{Colors.NC}")
        sys.exit(1)

    file_size_mb = COMPRESSED_FILE.stat().st_size / (1024 ** 2)
    print(f"{Colors.GREEN}✓ Archivo encontrado: {COMPRESSED_FILE}{Colors.NC}")
    print(f"  Tamaño: {file_size_mb:.2f} MB")

    # 2. Descomprimir archivo
    print(f"\n{Colors.YELLOW}[2/4] Descomprimiendo archivo...{Colors.NC}")
    with gzip.open(COMPRESSED_FILE, 'rb') as f_in:
        with open(UNCOMPRESSED_FILE, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    print(f"{Colors.GREEN}✓ Archivo descomprimido{Colors.NC}")

    # 3. Cargar imagen en Docker
    print(f"\n{Colors.YELLOW}[3/4] Cargando imagen en Docker (esto puede tomar varios minutos)...{Colors.NC}")
    run_command(f"docker load -i {UNCOMPRESSED_FILE}")
    print(f"{Colors.GREEN}✓ Imagen cargada correctamente{Colors.NC}")

    # 4. Verificar imagen
    print(f"\n{Colors.YELLOW}[4/4] Verificando instalación...{Colors.NC}")
    try:
        run_command(f"docker image inspect {FULL_IMAGE}", capture_output=True)
        size_gb = get_image_size(FULL_IMAGE)
        print(f"{Colors.GREEN}✓ Imagen disponible: {FULL_IMAGE}{Colors.NC}")
        print(f"  Tamaño: {size_gb:.2f} GB")
    except:
        print(f"{Colors.RED}❌ Error: La imagen no se cargó correctamente{Colors.NC}")
        sys.exit(1)

    # Limpiar archivo descomprimido
    print(f"\n{Colors.YELLOW}Limpiando archivos temporales...{Colors.NC}")
    UNCOMPRESSED_FILE.unlink()
    print(f"{Colors.GREEN}✓ Limpieza completada{Colors.NC}")

    # Resumen
    print(f"\n{Colors.GREEN}=== ✅ Importación Completada ==={Colors.NC}")
    print(f"\n{Colors.YELLOW}Próximos pasos:{Colors.NC}")
    print(f"  1. Importar también la imagen de PostgreSQL si no la tienes:")
    print(f"     python scripts/import_postgres.py")
    print(f"\n  2. Verificar que las imágenes están cargadas:")
    if sys.platform == 'win32':
        print(f"     docker images | findstr \"coe-ia-training pgvector\"")
    else:
        print(f"     docker images | grep -E 'coe-ia-training|pgvector'")
    print(f"\n  3. Abrir el repositorio con VSCode:")
    print(f"     code .")
    print(f"\n  4. VSCode te pedirá 'Reopen in Container' - acepta")
    print(f"\n  5. Espera a que el contenedor inicie (primera vez puede tardar 1-2 min)")
    print(f"\n{Colors.GREEN}¡Listo para empezar el curso! 🚀{Colors.NC}")
    print(f"\n{Colors.GREEN}=== Fin del Script ==={Colors.NC}")


if __name__ == "__main__":
    main()
