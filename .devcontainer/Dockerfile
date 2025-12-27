# Imagen base oficial de Python
FROM python:3.11-slim

# Metadata
LABEL maintainer="LILAB - COE IA AFP Integra"
LABEL description="Entorno de desarrollo para curso de Agentes IA"
LABEL version="1.0"

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crear usuario no-root para desarrollo
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Herramientas de build
    gcc \
    g++ \
    make \
    git \
    curl \
    wget \
    # PostgreSQL client
    postgresql-client \
    # Para procesamiento de PDFs (PyMuPDF)
    libmupdf-dev \
    mupdf-tools \
    # Para Pillow
    libjpeg-dev \
    zlib1g-dev \
    # Utilidades de desarrollo
    vim \
    nano \
    tree \
    jq \
    htop \
    # Limpieza
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# Copiar requirements.txt
COPY requirements.txt /tmp/requirements.txt

# Instalar dependencias Python
# Esta es la única fuente de verdad para las dependencias
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Crear directorio de trabajo
WORKDIR /workspace

# Asegurar permisos correctos del home directory
RUN chown -R $USERNAME:$USERNAME /home/$USERNAME

# Cambiar al usuario no-root
USER $USERNAME

# Crear directorios de VSCode Server con permisos correctos
RUN mkdir -p /home/$USERNAME/.vscode-server/extensions \
    && mkdir -p /home/$USERNAME/.vscode-server-insiders/extensions

# Verificar instalación
RUN python --version && pip list

# Healthcheck (opcional)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Comando por defecto (será sobreescrito por devcontainer)
CMD ["/bin/bash"]
