"""
FastAPI Application - API REST para Agentes de IA

Aplicación principal que expone los 3 prototipos del curso como APIs REST.
Los frontends pueden consumir estos endpoints para construir UIs ricas.

PEDAGOGÍA:
- Muestra cómo desplegar agentes en producción con FastAPI
- Demuestra separación de concerns (routes, models, business logic)
- Incluye CORS, logging, y error handling para producción

ARQUITECTURA:
    Frontend (React/Vue)
           ↓
    FastAPI (este archivo)
           ↓
    Routers (routes/asistente.py, etc.)
           ↓
    Agentes (agents/asistente/agent.py, etc.)
           ↓
    Tools + Framework

USO:
    # Desarrollo
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

    # Producción (con gunicorn)
    gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
"""

# IMPORTANTE: Cargar variables de entorno ANTES de importar componentes
from dotenv import load_dotenv
load_dotenv()  # Carga .env para GOOGLE_APPLICATION_CREDENTIALS y otras vars

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog
import time

from src.api.routes import asistente
from src.api.models import HealthResponse


# ============================================================================
# Configuración de Logging Estructurado
# ============================================================================

# PEDAGOGÍA:
# Logging estructurado (JSON) es crítico en producción para:
# - Parseo automático por sistemas de logs (ELK, Splunk, etc.)
# - Búsquedas eficientes
# - Correlación de requests (trace_id)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


# ============================================================================
# Inicialización de FastAPI
# ============================================================================

app = FastAPI(
    title="COE IA Training - API de Agentes",
    description=(
        "API REST para los 3 prototipos de agentes de IA del curso: "
        "Agente Asistente, Agente Reclamos, y Agente Buscador."
    ),
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc UI alternativo
)


# ============================================================================
# Middleware de CORS
# ============================================================================

# PEDAGOGÍA:
# CORS permite que frontends en diferentes dominios llamen a esta API.
# En desarrollo: allow_origins=["*"]
# En producción: especificar dominios exactos: ["https://afp.com", "https://app.afp.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Middleware de Logging
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware que logea todas las requests para observabilidad.

    PEDAGOGÍA:
    En producción, este middleware permite:
    - Tracking de latencias (percentiles p50, p95, p99)
    - Debugging de requests problemáticos
    - Analytics de uso (endpoints más llamados, etc.)

    En un sistema real, aquí también irían:
    - Trace IDs para distributed tracing
    - Metrics a Prometheus
    - Rate limiting
    """
    start_time = time.time()

    # Procesar request
    response = await call_next(request)

    # Calcular latencia
    process_time = time.time() - start_time

    # Log estructurado
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=int(process_time * 1000)
    )

    # Agregar header de timing
    response.headers["X-Process-Time"] = str(process_time)

    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler para errores de validación de Pydantic.

    PEDAGOGÍA:
    Retorna mensajes de error claros cuando el request no cumple con el schema.
    Útil para debugging en desarrollo y mensajes amigables en producción.
    """
    logger.error(
        "validation_error",
        path=request.url.path,
        errors=exc.errors()
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Error de validación en el request",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handler genérico para excepciones no capturadas.

    PEDAGOGÍA:
    Última línea de defensa para errores inesperados.
    En producción, aquí también iría alerting (PagerDuty, Slack, etc.)
    """
    import traceback

    # Obtener traceback completo
    tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # Log con traceback completo
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=tb_str
    )

    # TAMBIÉN imprimir a stdout para debugging
    print(f"\n{'='*80}")
    print(f"ERROR EN {request.url.path}")
    print(f"{'='*80}")
    print(tb_str)
    print(f"{'='*80}\n")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),  # Mostrar error real en desarrollo
            "error_type": type(exc).__name__
        }
    )


# ============================================================================
# Routers - Los 3 Prototipos
# ============================================================================

# Prototipo 1: Agente Asistente de Procedimientos
app.include_router(asistente.router, prefix="/api/v1")

# TODO: Prototipo 2: Agente Reclamos (Lab Día 2)
# from src.api.routes import reclamos
# app.include_router(reclamos.router, prefix="/api/v1")

# TODO: Prototipo 3: Agente Buscador (Lab Día 3)
# from src.api.routes import buscador
# app.include_router(buscador.router, prefix="/api/v1")


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Endpoint raíz - Información de la API.

    PEDAGOGÍA:
    Siempre es buena práctica tener un endpoint raíz que explique
    qué es la API y dónde encontrar la documentación.
    """
    return {
        "message": "COE IA Training - API de Agentes",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "prototipos": {
            "asistente": "/api/v1/asistente",
            "reclamos": "/api/v1/reclamos (TODO)",
            "buscador": "/api/v1/buscador (TODO)"
        }
    }


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health():
    """
    Health check global de la API.

    PEDAGOGÍA:
    - Usado por load balancers y Kubernetes probes
    - Puede incluir checks de dependencias (DB, Redis, etc.)
    - Retorna 200 si el servicio está healthy
    """
    # TODO: En producción, verificar conectividad a:
    # - PostgreSQL (vector store)
    # - Vertex AI (model provider)
    # - Redis (si hay caché)

    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Evento ejecutado al iniciar la aplicación.

    PEDAGOGÍA:
    Aquí se inicializan recursos globales:
    - Pool de conexiones a DB
    - Conexión a Redis/Memcached
    - Warm-up de modelos
    """
    logger.info("api_startup", message="Inicializando API...")

    # Inicializar pool de conexiones a PostgreSQL
    from src.api.routes import asistente
    await asistente.vector_store.connect()
    logger.info("api_startup", message="VectorStore conectado a PostgreSQL")

    logger.info("api_startup", message="API iniciada correctamente")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Evento ejecutado al apagar la aplicación.

    PEDAGOGÍA:
    Limpieza ordenada de recursos:
    - Cerrar conexiones a DB
    - Flush de logs pendientes
    - Completar requests en curso
    """
    logger.info("api_shutdown", message="API apagándose...")

    # Cerrar pool de conexiones a PostgreSQL
    from src.api.routes import asistente
    await asistente.vector_store.close()
    logger.info("api_shutdown", message="VectorStore cerrado correctamente")


# ============================================================================
# Punto de entrada para desarrollo
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # PEDAGOGÍA:
    # Este bloque solo se ejecuta si corres `python src/api/main.py`
    # En producción, se usa uvicorn/gunicorn directamente

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload en desarrollo
        log_level="info"
    )
