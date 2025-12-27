# COE IA Training - Capacitación en Agentes de IA

> Curso intensivo de desarrollo de agentes de IA con CAG (Compound AI with Agents) para CoE TI AFP Integra

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

---

## 🚀 Setup Rápido

### Requisitos Previos

- **Docker Desktop** instalado y corriendo
- **Visual Studio Code** con extensión Dev Containers
- **Credenciales de Vertex AI** (proporcionadas por el instructor)
- **Imágenes Docker** (proporcionadas en USB/Drive)

### Instalación (5 minutos)

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/Lautaroorbes/COE-AI-TRAINING.git
   cd COE-IA-TRAINING
   ```

2. **Copiar credenciales**
   ```bash
   # Copiar desde USB/Drive
   cp /path/to/usb/vertex-ai-sa.json credentials/
   ```

3. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus valores (PROJECT_ID, etc.)
   ```

4. **Importar imágenes Docker offline**
   ```bash
   # Los archivos deben estar en dist/
   # - coe-ia-training-latest.tar.gz
   # - pgvector-pg16.tar.gz

   python scripts/import_image.py
   python scripts/import_postgres.py
   ```

5. **Abrir en Dev Container**
   ```bash
   code .
   ```
   → Cuando VSCode pregunte "Reopen in Container", acepta

6. **Verificar instalación**
   ```bash
   python scripts/test_setup.py
   ```

7. **Probar el Prototipo 1 (Agente Asistente)** - Opcional
   ```bash
   # Después de ingestar documentos, puedes probar el agente completo:
   python scripts/demo_asistente.py
   ```

📖 **Instrucciones detalladas**: Ver [docs/SETUP-PARTICIPANTES.md](docs/SETUP-PARTICIPANTES.md)

---

## 📚 ¿Qué Construiremos?

Este curso de **3 días presenciales** te enseña a construir 3 agentes de IA para casos de uso reales de AFP:

### Prototipo 1: Agente Asistente de Procedimientos
- **Tools**: Retrieval (RAG) + Checklist Generator
- **Caso de uso**: Consultas sobre traspasos, jubilación, afiliación
- **Aprenderás**: RAG, embeddings, generación estructurada

### Prototipo 2: Agente Gestión de Reclamos
- **Tools**: Classifier + Router + Audit
- **Caso de uso**: Clasificación automática y routing de reclamos
- **Aprenderás**: Agentes multi-tool, orquestación, logging

### Prototipo 3: Agente Buscador Multisistema
- **Tools**: SQL Query + Filesystem Search
- **Caso de uso**: Búsqueda unificada en bases de datos + documentos
- **Aprenderás**: Seguridad (SQL injection), multi-source retrieval

---

## 🗓️ Cronograma

### Día 0: Setup Autoguiado (~2 horas)
- Instalación Docker + VSCode
- Importación de imágenes offline
- Configuración Vertex AI
- Verificación de entorno

### Día 1: Agente Asistente (4 horas)
- Teoría (1h): LLM vs SLM, CAG vs RAG tradicional
- Labs (3h): Retrieval Tool + Checklist Tool + Orchestration
- **Entregable**: Prototipo 1 funcional

### Día 2: Agente Reclamos (4 horas)
- Teoría (1h): Patrones de agentes, Router + Tools
- Labs (3h): Classifier + Router + Audit Tools
- **Entregable**: Prototipo 2 funcional

### Día 3: Agente Buscador + Capstone (4 horas)
- Teoría (50min): Evaluación, observabilidad, guardrails
- Labs (2h): SQL + Filesystem Tools
- Capstone (1h 10min): Extensión por equipos
- **Entregable**: Prototipo 3 funcional + Extensión personalizada

### Post-Curso: Clínicas Remotas
- **Clínica 1 (2h)**: Debugging y hardening
- **Clínica 2 (2h)**: Evaluación de impacto + roadmap

---

## 🛠️ Stack Tecnológico

| Categoría | Tecnología |
|-----------|-----------|
| Lenguaje | Python 3.11+ |
| API Framework | FastAPI |
| Base de Datos | PostgreSQL 16 + pgvector |
| LLM | Gemini (Vertex AI) 2.5 Flash / Pro |
| Embeddings | text-embedding-004 |
| Infraestructura | Docker + Dev Containers |

---

## 📂 Estructura del Proyecto

```
COE-IA-TRAINING/
├── src/
│   ├── framework/          # Custom Agent Framework (PROVISTO)
│   ├── rag/                # Infraestructura RAG (PROVISTO)
│   ├── tools/              # Tools personalizadas (TÚ IMPLEMENTAS)
│   ├── agents/             # Los 3 prototipos (TÚ IMPLEMENTAS)
│   └── guardrails/         # Seguridad (PROVISTO + EXTENSIÓN)
├── data/
│   ├── documentos/         # PDFs de procedimientos AFP
│   └── bases_datos/        # Schemas PostgreSQL
├── scripts/                # Utilidades de setup
├── docs/                   # Documentación adicional
└── docker-compose.yml      # Configuración Docker
```

---

## 🎯 Filosofía del Curso

### Production-Ready, no Académico
Construirás **3 prototipos funcionales** que AFP Integra puede llevar a producción. No es teoría, es código real.

### Distribución de Código
- **Infraestructura base**: Provista (framework, RAG, DB)
- **Agentes y tools**: Tú implementas (con guía)
- **Guardrails**: Proveídos + extiendes

### Progresión de Autonomía
- **Día 1**: 50% guiado / 50% implementas
- **Día 2**: 40% guiado / 60% implementas
- **Día 3**: 20% guiado / 80% implementas

---

## 📖 Documentación

- **[SETUP-PARTICIPANTES.md](docs/SETUP-PARTICIPANTES.md)**: Guía completa de instalación
- **[QUICKSTART.md](docs/QUICKSTART.md)**: Referencia rápida
- **[.env.example](.env.example)**: Template de configuración

---

## 🆘 Soporte

Durante el curso:
- **En vivo**: Pregunta al instructor o asistentes
- **Slack/Teams**: Canal dedicado del curso

Post-curso (4 semanas):
- **Email**: [instructor-email]
- **Clínicas remotas**: 2 sesiones de 2 horas

---

## 🔑 Estrategia de Ramas

Cada laboratorio tiene 3 ramas para ayudarte:

```bash
git checkout lab-1.1-start       # Empezar desde cero
git checkout lab-1.1-checkpoint  # Si te atrasaste (código parcial)
git checkout lab-1.1-solution    # Ver solución completa
```

**Recomendación**: Intenta completar desde `-start`. Usa `-checkpoint` solo si te atrasas.

---

## ⚖️ Licencia

MIT License - Código libre para uso interno en AFP Integra

---

## 📞 Contacto

**Organización**: LILAB - CoE IA AFP Integra
**Instructor**: [Nombre del instructor]
**Email**: [instructor@email.com]

---

**¡Bienvenido al curso! 🚀 Prepárate para construir agentes de IA que resuelven problemas reales.**
