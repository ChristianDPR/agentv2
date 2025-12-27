# Setup del Entorno - COE IA Training

> Instrucciones para configurar el entorno de desarrollo del curso de Agentes IA para AFP Integra

---

## Requisitos Previos

### Software Necesario
- **Docker Desktop** instalado y corriendo
  - Windows/Mac: [Descargar Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - Linux: Docker Engine + Docker Compose
- **Visual Studio Code** instalado
  - [Descargar VSCode](https://code.visualstudio.com/)
- **Extensión de VSCode**: Dev Containers
  - Instalar desde VSCode: `Ctrl+P` → `ext install ms-vscode-remote.remote-containers`

### Archivos Necesarios (Distribución Offline)
Los siguientes archivos deben estar en tu carpeta `dist/`:
- `coe-ia-training-latest.tar.gz` (Imagen del dev container ~2-3 GB)
- `pgvector-pg16.tar.gz` (Imagen de PostgreSQL ~300 MB)

---

## Opción 1: Setup Offline (Recomendado para el Curso)

### Paso 1: Clonar el Repositorio
```bash
# Desde GitHub
git clone https://github.com/Lautaroorbes/COE-AI-TRAINING.git
cd COE-IA-TRAINING
```

### Paso 2: Copiar Imágenes Docker
Copia los archivos `.tar.gz` desde el USB/Drive a la carpeta `dist/`:
```bash
mkdir -p dist
# Copiar coe-ia-training-latest.tar.gz a dist/
# Copiar pgvector-pg16.tar.gz a dist/
```

### Paso 3: Importar Imágenes Docker
```bash
# Importar imagen del dev container
python scripts/import_image.py

# Importar imagen de PostgreSQL
python scripts/import_postgres.py
```

### Paso 4: Verificar Imágenes

**Mac/Linux:**
```bash
docker images | grep -E 'coe-ia-training|pgvector'
```

**Windows (PowerShell):**
```powershell
docker images | Select-String "coe-ia-training|pgvector"
```

**Windows (CMD):**
```cmd
docker images | findstr "coe-ia-training pgvector"
```

Deberías ver:
```
coe-ia-training    latest    ...    2-3 GB
pgvector/pgvector  pg16      ...    ~500 MB
```

### Paso 5: Abrir en VSCode Dev Container
```bash
code .
```

VSCode detectará el `.devcontainer/` y mostrará una notificación:
**"Folder contains a Dev Container configuration file. Reopen folder to develop in a container?"**

→ Click en **"Reopen in Container"**

Espera 1-2 minutos mientras el contenedor inicia (solo la primera vez).

### Paso 6: Verificar Instalación
Dentro del Dev Container, ejecuta:
```bash
# Verificar Python
python --version
# Debe mostrar: Python 3.11.x

# Verificar dependencias
pip list

# Verificar conexión a PostgreSQL
docker ps
# Debe mostrar: coe-ia-postgres (healthy)
```

---

## Opción 2: Setup Online (Construcción desde Cero)

Si tienes buena conexión a Internet:

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/Lautaroorbes/COE-AI-TRAINING.git
cd COE-IA-TRAINING
```

### Paso 2: Construir Imagen
```bash
docker compose -f docker-compose.dev.yml build devcontainer
```

Esto descargará e instalará todas las dependencias (~5-10 minutos).

### Paso 3: Abrir en VSCode Dev Container
```bash
code .
```
→ Click en **"Reopen in Container"**

---

## Configuración de Vertex AI

### Paso 1: Obtener Service Account JSON
Solicita al instructor el archivo `vertex-ai-sa.json` (Service Account de GCP).

### Paso 2: Copiar Credenciales
```bash
mkdir -p credentials
# Copiar vertex-ai-sa.json a credentials/
```

### Paso 3: Configurar Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto:
```bash
cp .env.example .env
```

Edita `.env` y configura:
```bash
VERTEX_AI_PROJECT=tu-proyecto-gcp
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/workspace/credentials/vertex-ai-sa.json
```

### Paso 4: Verificar Conexión
```python
# Dentro del Dev Container
python

>>> from google.cloud import aiplatform
>>> aiplatform.init(project="tu-proyecto-gcp", location="us-central1")
>>> print("✅ Conexión exitosa")
```

---

## Estructura del Proyecto

```
COE-IA-TRAINING/
├── .devcontainer/           # Configuración Dev Container
│   ├── devcontainer.json
│   └── Dockerfile
├── src/                     # Código fuente
│   ├── framework/           # Agent framework custom
│   ├── rag/                 # Infraestructura RAG
│   ├── tools/               # Tools personalizadas
│   ├── agents/              # Los 3 prototipos
│   ├── guardrails/          # Seguridad
│   └── api/                 # FastAPI endpoints
├── data/                    # Datasets sintéticos
├── tests/                   # Tests
├── scripts/                 # Scripts de utilidad
├── dist/                    # Imágenes Docker offline
├── requirements.txt         # Dependencias Python
├── docker-compose.dev.yml   # Docker Compose para desarrollo
└── SETUP.md                 # Este archivo
```

---

## Comandos Útiles

### Dentro del Dev Container

```bash
# Ejecutar API en modo desarrollo
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Ejecutar tests
pytest

# Ejecutar tests con coverage
pytest --cov=src tests/

# Formatear código
black src/

# Ver logs de PostgreSQL
docker logs coe-ia-postgres

# Conectarse a PostgreSQL
psql postgresql://afp_user:afp_secure_2024@postgres:5432/afp_agents
```

### Desde el Host (fuera del contenedor)

```bash
# Reconstruir contenedor si cambias requirements.txt
docker compose -f docker-compose.dev.yml build devcontainer

# Detener todos los contenedores
docker compose -f docker-compose.dev.yml down

# Detener y eliminar volúmenes (reset completo)
docker compose -f docker-compose.dev.yml down -v

# Ver logs
docker compose -f docker-compose.dev.yml logs -f
```

---

## Troubleshooting

### Problema: "Cannot connect to Docker daemon"
**Solución**: Asegúrate de que Docker Desktop esté corriendo.

### Problema: "Port 5432 already in use"
**Solución**: Detén cualquier PostgreSQL local:
```bash
# Mac
brew services stop postgresql

# Windows
# Detener servicio PostgreSQL desde Services.msc

# Linux
sudo systemctl stop postgresql
```

### Problema: "No space left on device"
**Solución**: Limpia imágenes Docker viejas:
```bash
docker system prune -a
```

### Problema: "Extension host terminated unexpectedly"
**Solución**:
1. Cierra VSCode completamente
2. Elimina contenedores: `docker compose -f docker-compose.dev.yml down`
3. Vuelve a abrir: `code .` → Reopen in Container

### Problema: "Cannot install packages - pip fails"
**Solución**: Verifica que el archivo `requirements.txt` no tenga errores de sintaxis.

---

## Checklist Pre-Curso (Día 0)

- [ ] Docker Desktop instalado y corriendo
- [ ] VSCode instalado con extensión Dev Containers
- [ ] Repositorio clonado desde GitHub
- [ ] Imágenes Docker importadas (coe-ia-training + pgvector)
- [ ] Contenedor iniciado correctamente (`docker ps` muestra 2 contenedores)
- [ ] Credenciales de Vertex AI configuradas
- [ ] Conexión a Vertex AI verificada
- [ ] Tests básicos corriendo: `pytest tests/`

---

## Soporte

Si tienes problemas durante el setup:
1. Revisa la sección de Troubleshooting
2. Consulta al instructor durante el Día 0 (setup autoguiado)
3. Durante el curso: Levanta la mano y pediremos ayuda

---

**Última actualización**: 2025-11-23
**Versión**: 1.0
**Mantenido por**: LILAB - COE IA AFP Integra
