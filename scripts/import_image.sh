#!/bin/bash
###############################################################################
# Script: import_image.sh
# Descripción: Importa la imagen Docker del dev container (distribución offline)
# Uso: ./scripts/import_image.sh
###############################################################################

set -e  # Exit on error

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

IMAGE_NAME="coe-ia-training"
IMAGE_TAG="latest"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
DIST_DIR="./dist"
COMPRESSED_FILE="${DIST_DIR}/${IMAGE_NAME}-${IMAGE_TAG}.tar.gz"
UNCOMPRESSED_FILE="${DIST_DIR}/${IMAGE_NAME}-${IMAGE_TAG}.tar"

echo -e "${GREEN}=== Importación de Imagen Docker para COE IA Training ===${NC}\n"

# 1. Verificar que el archivo existe
echo -e "${YELLOW}[1/4] Verificando archivo de imagen...${NC}"
if [ ! -f "${COMPRESSED_FILE}" ]; then
    echo -e "${RED}❌ Error: No se encuentra el archivo ${COMPRESSED_FILE}${NC}"
    echo -e "${YELLOW}Asegúrate de haber copiado el archivo desde el USB/Drive a la carpeta dist/${NC}"
    exit 1
fi

FILE_SIZE=$(du -h ${COMPRESSED_FILE} | cut -f1)
echo -e "${GREEN}✓ Archivo encontrado: ${COMPRESSED_FILE}${NC}"
echo -e "  Tamaño: ${FILE_SIZE}"

# 2. Descomprimir archivo
echo -e "\n${YELLOW}[2/4] Descomprimiendo archivo...${NC}"
gunzip -k -f ${COMPRESSED_FILE}
echo -e "${GREEN}✓ Archivo descomprimido${NC}"

# 3. Cargar imagen en Docker
echo -e "\n${YELLOW}[3/4] Cargando imagen en Docker (esto puede tomar varios minutos)...${NC}"
docker load -i ${UNCOMPRESSED_FILE}
echo -e "${GREEN}✓ Imagen cargada correctamente${NC}"

# 4. Verificar imagen
echo -e "\n${YELLOW}[4/4] Verificando instalación...${NC}"
if docker image inspect ${FULL_IMAGE} > /dev/null 2>&1; then
    IMAGE_SIZE=$(docker image inspect ${FULL_IMAGE} --format='{{.Size}}' | awk '{print $1/1024/1024/1024}')
    echo -e "${GREEN}✓ Imagen disponible: ${FULL_IMAGE}${NC}"
    echo -e "  Tamaño: $(printf '%.2f' ${IMAGE_SIZE}) GB"
else
    echo -e "${RED}❌ Error: La imagen no se cargó correctamente${NC}"
    exit 1
fi

# Limpiar archivo descomprimido (opcional)
echo -e "\n${YELLOW}Limpiando archivos temporales...${NC}"
rm -f ${UNCOMPRESSED_FILE}
echo -e "${GREEN}✓ Limpieza completada${NC}"

# Resumen
echo -e "\n${GREEN}=== ✅ Importación Completada ===${NC}"
echo -e "\n${YELLOW}Próximos pasos:${NC}"
echo -e "  1. Importar también la imagen de PostgreSQL si no la tienes:"
echo -e "     gunzip -k dist/pgvector-pg16.tar.gz"
echo -e "     docker load -i dist/pgvector-pg16.tar"
echo -e "\n  2. Verificar que las imágenes están cargadas:"
echo -e "     docker images | grep -E 'coe-ia-training|pgvector'"
echo -e "\n  3. Abrir el repositorio con VSCode:"
echo -e "     code ."
echo -e "\n  4. VSCode te pedirá 'Reopen in Container' - acepta"
echo -e "\n  5. Espera a que el contenedor inicie (primera vez puede tardar 1-2 min)"
echo -e "\n${GREEN}¡Listo para empezar el curso! 🚀${NC}"
echo -e "\n${GREEN}=== Fin del Script ===${NC}"
