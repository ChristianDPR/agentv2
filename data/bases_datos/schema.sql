-- ============================================================================
-- Schema para COE IA Training
-- PostgreSQL 16 + pgvector
--
-- Este schema está diseñado para demostrar el poder de agentes IA
-- con búsquedas complejas multi-tabla y escenarios realistas.
-- ============================================================================

-- Habilitar extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Tabla de chunks de documentos (para RAG)
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),  -- text-embedding-004 usa 768 dimensiones
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_chunks_metadata
ON document_chunks
USING gin (metadata);

-- ============================================================================
-- DOMINIO AFP: Tablas principales
-- ============================================================================

-- Tabla de afiliados
CREATE TABLE IF NOT EXISTS afiliados (
    rut VARCHAR(12) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    apellido_paterno VARCHAR(255) NOT NULL,
    apellido_materno VARCHAR(255),
    email VARCHAR(255),
    telefono VARCHAR(20),
    fecha_nacimiento DATE,
    fecha_afiliacion DATE NOT NULL,
    estado VARCHAR(50) DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo', 'suspendido', 'pensionado', 'fallecido')),
    tipo_afiliado VARCHAR(50) DEFAULT 'dependiente' CHECK (tipo_afiliado IN ('dependiente', 'independiente', 'voluntario', 'pensionado')),
    empleador VARCHAR(255),
    renta_imponible DECIMAL(12, 2),
    fondo_actual VARCHAR(10) DEFAULT 'B' CHECK (fondo_actual IN ('A', 'B', 'C', 'D', 'E')),
    saldo_obligatorio DECIMAL(14, 2) DEFAULT 0,
    saldo_voluntario DECIMAL(14, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_afiliados_estado ON afiliados(estado);
CREATE INDEX IF NOT EXISTS idx_afiliados_empleador ON afiliados(empleador);
CREATE INDEX IF NOT EXISTS idx_afiliados_fondo ON afiliados(fondo_actual);

-- Tabla de beneficiarios (para pensión de sobrevivencia)
CREATE TABLE IF NOT EXISTS beneficiarios (
    id SERIAL PRIMARY KEY,
    afiliado_rut VARCHAR(12) NOT NULL REFERENCES afiliados(rut) ON DELETE CASCADE,
    rut_beneficiario VARCHAR(12) NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    parentesco VARCHAR(50) NOT NULL CHECK (parentesco IN ('conyuge', 'conviviente', 'hijo', 'madre', 'padre', 'otro')),
    porcentaje_asignado DECIMAL(5, 2) CHECK (porcentaje_asignado >= 0 AND porcentaje_asignado <= 100),
    es_invalido BOOLEAN DEFAULT FALSE,
    fecha_nacimiento DATE,
    vigente BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(afiliado_rut, rut_beneficiario)
);

CREATE INDEX IF NOT EXISTS idx_beneficiarios_afiliado ON beneficiarios(afiliado_rut);

-- Tabla de aportes (cotizaciones)
CREATE TABLE IF NOT EXISTS aportes (
    id SERIAL PRIMARY KEY,
    afiliado_rut VARCHAR(12) NOT NULL REFERENCES afiliados(rut) ON DELETE CASCADE,
    periodo VARCHAR(7) NOT NULL,  -- Formato: YYYY-MM
    monto DECIMAL(12, 2) NOT NULL CHECK (monto >= 0),
    fecha_pago DATE NOT NULL,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('obligatorio', 'voluntario', 'apv', 'apvc', 'deposito_convenido')),
    estado VARCHAR(50) DEFAULT 'procesado' CHECK (estado IN ('pendiente', 'procesado', 'rechazado', 'en_cobranza')),
    empleador VARCHAR(255),
    comision DECIMAL(10, 2) DEFAULT 0,
    seguro DECIMAL(10, 2) DEFAULT 0,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aportes_afiliado ON aportes(afiliado_rut);
CREATE INDEX IF NOT EXISTS idx_aportes_periodo ON aportes(periodo DESC);
CREATE INDEX IF NOT EXISTS idx_aportes_estado ON aportes(estado);
CREATE INDEX IF NOT EXISTS idx_aportes_empleador ON aportes(empleador);

-- Tabla de traspasos entre AFPs
CREATE TABLE IF NOT EXISTS traspasos (
    id SERIAL PRIMARY KEY,
    afiliado_rut VARCHAR(12) NOT NULL REFERENCES afiliados(rut) ON DELETE CASCADE,
    afp_origen VARCHAR(100) NOT NULL,
    afp_destino VARCHAR(100) NOT NULL,
    monto_obligatorio DECIMAL(14, 2) CHECK (monto_obligatorio >= 0),
    monto_voluntario DECIMAL(14, 2) DEFAULT 0,
    fecha_solicitud DATE NOT NULL,
    fecha_ejecucion DATE,
    estado VARCHAR(50) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'en_proceso', 'completado', 'rechazado', 'cancelado')),
    motivo_rechazo TEXT,
    numero_solicitud VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_traspasos_afiliado ON traspasos(afiliado_rut);
CREATE INDEX IF NOT EXISTS idx_traspasos_estado ON traspasos(estado);
CREATE INDEX IF NOT EXISTS idx_traspasos_fecha ON traspasos(fecha_solicitud DESC);

-- Tabla de reclamos
CREATE TABLE IF NOT EXISTS reclamos (
    id SERIAL PRIMARY KEY,
    numero_ticket VARCHAR(20) UNIQUE NOT NULL,
    afiliado_rut VARCHAR(12) REFERENCES afiliados(rut) ON DELETE SET NULL,
    tipo VARCHAR(100) NOT NULL CHECK (tipo IN (
        'cobro_indebido', 'retraso_pago', 'error_saldo', 'pension_no_pagada',
        'bono_reconocimiento', 'cambio_fondo', 'traspaso', 'atencion_cliente',
        'informacion_incorrecta', 'otro'
    )),
    canal VARCHAR(50) NOT NULL CHECK (canal IN ('web', 'telefono', 'presencial', 'email', 'carta')),
    descripcion TEXT NOT NULL,
    monto_reclamado DECIMAL(12, 2),
    prioridad VARCHAR(20) DEFAULT 'media' CHECK (prioridad IN ('baja', 'media', 'alta', 'urgente')),
    estado VARCHAR(50) DEFAULT 'abierto' CHECK (estado IN ('abierto', 'en_revision', 'pendiente_info', 'resuelto', 'cerrado', 'escalado')),
    resolucion TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion TIMESTAMP,
    agente_asignado VARCHAR(100),
    satisfaccion_cliente INTEGER CHECK (satisfaccion_cliente >= 1 AND satisfaccion_cliente <= 5)
);

CREATE INDEX IF NOT EXISTS idx_reclamos_afiliado ON reclamos(afiliado_rut);
CREATE INDEX IF NOT EXISTS idx_reclamos_estado ON reclamos(estado);
CREATE INDEX IF NOT EXISTS idx_reclamos_tipo ON reclamos(tipo);
CREATE INDEX IF NOT EXISTS idx_reclamos_prioridad ON reclamos(prioridad);
CREATE INDEX IF NOT EXISTS idx_reclamos_fecha ON reclamos(fecha_creacion DESC);

-- Tabla de movimientos de cuenta (historial detallado)
CREATE TABLE IF NOT EXISTS movimientos (
    id SERIAL PRIMARY KEY,
    afiliado_rut VARCHAR(12) NOT NULL REFERENCES afiliados(rut) ON DELETE CASCADE,
    tipo_movimiento VARCHAR(50) NOT NULL CHECK (tipo_movimiento IN (
        'aporte', 'retiro', 'traspaso_entrada', 'traspaso_salida',
        'rentabilidad', 'comision', 'bono_reconocimiento', 'pension',
        'cambio_fondo', 'ajuste'
    )),
    monto DECIMAL(14, 2) NOT NULL,
    saldo_anterior DECIMAL(14, 2),
    saldo_posterior DECIMAL(14, 2),
    fondo VARCHAR(10),
    fecha_movimiento DATE NOT NULL,
    descripcion TEXT,
    referencia_id INTEGER,  -- ID de aporte, traspaso, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_movimientos_afiliado ON movimientos(afiliado_rut);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha_movimiento DESC);
CREATE INDEX IF NOT EXISTS idx_movimientos_tipo ON movimientos(tipo_movimiento);

-- Tabla de pensiones (para pensionados)
CREATE TABLE IF NOT EXISTS pensiones (
    id SERIAL PRIMARY KEY,
    afiliado_rut VARCHAR(12) NOT NULL REFERENCES afiliados(rut) ON DELETE CASCADE,
    tipo_pension VARCHAR(50) NOT NULL CHECK (tipo_pension IN (
        'vejez_normal', 'vejez_anticipada', 'invalidez_parcial',
        'invalidez_total', 'sobrevivencia'
    )),
    modalidad VARCHAR(50) CHECK (modalidad IN (
        'retiro_programado', 'renta_vitalicia', 'renta_temporal', 'mixta'
    )),
    monto_mensual DECIMAL(12, 2),
    fecha_inicio DATE NOT NULL,
    fecha_termino DATE,
    estado VARCHAR(50) DEFAULT 'activa' CHECK (estado IN ('activa', 'suspendida', 'terminada')),
    compania_seguros VARCHAR(255),  -- Para renta vitalicia
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pensiones_afiliado ON pensiones(afiliado_rut);
CREATE INDEX IF NOT EXISTS idx_pensiones_tipo ON pensiones(tipo_pension);

-- Tabla de empleadores (para validar pagos)
CREATE TABLE IF NOT EXISTS empleadores (
    rut VARCHAR(12) PRIMARY KEY,
    razon_social VARCHAR(255) NOT NULL,
    giro VARCHAR(255),
    direccion TEXT,
    comuna VARCHAR(100),
    region VARCHAR(100),
    estado VARCHAR(50) DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo', 'moroso', 'en_cobranza')),
    deuda_total DECIMAL(14, 2) DEFAULT 0,
    cantidad_trabajadores INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_empleadores_estado ON empleadores(estado);

-- ============================================================================
-- Tabla de auditoría (para todos los agentes)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id VARCHAR(255),
    user_id VARCHAR(100),
    query_text TEXT,
    decision JSONB,
    metadata JSONB,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent_name);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);

-- ============================================================================
-- Funciones de utilidad
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para updated_at
DROP TRIGGER IF EXISTS update_afiliados_updated_at ON afiliados;
CREATE TRIGGER update_afiliados_updated_at BEFORE UPDATE ON afiliados
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_traspasos_updated_at ON traspasos;
CREATE TRIGGER update_traspasos_updated_at BEFORE UPDATE ON traspasos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_reclamos_updated_at ON reclamos;
CREATE TRIGGER update_reclamos_updated_at BEFORE UPDATE ON reclamos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Vistas útiles para consultas comunes
-- ============================================================================

-- Vista de resumen de afiliado
CREATE OR REPLACE VIEW vista_resumen_afiliado AS
SELECT
    a.rut,
    a.nombre || ' ' || a.apellido_paterno || ' ' || COALESCE(a.apellido_materno, '') AS nombre_completo,
    a.estado,
    a.tipo_afiliado,
    a.fondo_actual,
    a.saldo_obligatorio + a.saldo_voluntario AS saldo_total,
    a.fecha_afiliacion,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, a.fecha_afiliacion)) AS anos_afiliado,
    (SELECT COUNT(*) FROM aportes ap WHERE ap.afiliado_rut = a.rut) AS total_aportes,
    (SELECT COUNT(*) FROM reclamos r WHERE r.afiliado_rut = a.rut AND r.estado IN ('abierto', 'en_revision')) AS reclamos_activos,
    (SELECT COUNT(*) FROM beneficiarios b WHERE b.afiliado_rut = a.rut AND b.vigente = TRUE) AS beneficiarios_vigentes
FROM afiliados a;

-- Vista de empleadores morosos
CREATE OR REPLACE VIEW vista_empleadores_morosos AS
SELECT
    e.rut,
    e.razon_social,
    e.deuda_total,
    e.cantidad_trabajadores,
    (SELECT COUNT(DISTINCT ap.afiliado_rut)
     FROM aportes ap
     WHERE ap.empleador = e.razon_social AND ap.estado = 'en_cobranza') AS afiliados_afectados
FROM empleadores e
WHERE e.estado IN ('moroso', 'en_cobranza') AND e.deuda_total > 0;

-- ============================================================================
-- Fin del schema
-- ============================================================================

SELECT 'Schema creado correctamente' AS status;
SELECT COUNT(*) AS total_tables
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
