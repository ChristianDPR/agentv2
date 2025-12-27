-- ============================================================================
-- Seed data para COE IA Training
-- Datos sintéticos para demostrar capacidades de agentes IA
--
-- Este seed incluye escenarios realistas y casos edge para testing:
-- - 50 afiliados con diversos estados y situaciones
-- - Historial de aportes de 2 años
-- - Reclamos variados con diferentes prioridades
-- - Empleadores incluyendo algunos morosos
-- - Pensionados y beneficiarios
-- ============================================================================

-- ============================================================================
-- Empleadores (insertar primero para referencias)
-- ============================================================================

INSERT INTO empleadores (rut, razon_social, giro, comuna, region, estado, deuda_total, cantidad_trabajadores) VALUES
('76000001-1', 'Minera Los Andes SpA', 'Minería del cobre', 'Calama', 'Antofagasta', 'activo', 0, 450),
('76000002-2', 'Constructora Pacífico Ltda', 'Construcción', 'Santiago', 'Metropolitana', 'activo', 0, 280),
('76000003-3', 'TechSolutions Chile SA', 'Tecnología', 'Providencia', 'Metropolitana', 'activo', 0, 120),
('76000004-4', 'Agrícola del Sur Ltda', 'Agricultura', 'Temuco', 'Araucanía', 'moroso', 15600000, 85),
('76000005-5', 'Transportes Rápido Express', 'Transporte', 'Valparaíso', 'Valparaíso', 'en_cobranza', 28500000, 62),
('76000006-6', 'Restaurant Gourmet SpA', 'Gastronomía', 'Viña del Mar', 'Valparaíso', 'activo', 0, 35),
('76000007-7', 'Clínica Salud Integral', 'Salud', 'Las Condes', 'Metropolitana', 'activo', 0, 210),
('76000008-8', 'Importadora Global Trade', 'Comercio exterior', 'Santiago', 'Metropolitana', 'inactivo', 0, 0),
('76000009-9', 'Pesquera Austral SA', 'Pesca', 'Puerto Montt', 'Los Lagos', 'activo', 0, 145),
('76000010-K', 'Retail MegaStore Chile', 'Retail', 'Concepción', 'Biobío', 'moroso', 42000000, 520)
ON CONFLICT (rut) DO NOTHING;

-- ============================================================================
-- Afiliados (50 registros con diversos escenarios)
-- ============================================================================

INSERT INTO afiliados (rut, nombre, apellido_paterno, apellido_materno, email, telefono, fecha_nacimiento, fecha_afiliacion, estado, tipo_afiliado, empleador, renta_imponible, fondo_actual, saldo_obligatorio, saldo_voluntario) VALUES
-- Afiliados activos con buen historial
('12345678-9', 'Juan', 'Pérez', 'González', 'juan.perez@email.com', '+56912345678', '1985-03-15', '2010-01-15', 'activo', 'dependiente', 'Minera Los Andes SpA', 2500000, 'B', 45000000, 5000000),
('98765432-1', 'María', 'Silva', 'López', 'maria.silva@email.com', '+56987654321', '1990-07-22', '2015-06-10', 'activo', 'dependiente', 'TechSolutions Chile SA', 3200000, 'C', 28000000, 8500000),
('11111111-1', 'Pedro', 'Rojas', 'Muñoz', 'pedro.rojas@email.com', '+56911111111', '1988-11-30', '2012-03-20', 'activo', 'dependiente', 'Constructora Pacífico Ltda', 1800000, 'B', 32000000, 2000000),
('22222222-2', 'Ana', 'Torres', 'Vargas', 'ana.torres@email.com', '+56922222222', '1992-05-18', '2016-09-05', 'activo', 'dependiente', 'Clínica Salud Integral', 2800000, 'A', 22000000, 12000000),
('33333333-3', 'Luis', 'Fernández', 'Castro', 'luis.fernandez@email.com', '+56933333333', '1987-08-12', '2011-11-22', 'activo', 'independiente', NULL, 1500000, 'D', 38000000, 0),

-- Afiliados con problemas (empleador moroso)
('44444444-4', 'Carmen', 'Soto', 'Díaz', 'carmen.soto@email.com', '+56944444444', '1995-02-28', '2018-04-15', 'activo', 'dependiente', 'Agrícola del Sur Ltda', 950000, 'C', 8500000, 0),
('55555555-5', 'Roberto', 'Morales', 'Jiménez', 'roberto.morales@email.com', '+56955555555', '1983-12-05', '2009-07-30', 'activo', 'dependiente', 'Transportes Rápido Express', 1200000, 'B', 52000000, 3500000),
('66666666-6', 'Patricia', 'Ramírez', 'Herrera', 'patricia.ramirez@email.com', '+56966666666', '1991-09-14', '2014-02-18', 'activo', 'dependiente', 'Retail MegaStore Chile', 1100000, 'C', 18000000, 1000000),

-- Pensionados
('77777777-7', 'Diego', 'Navarro', 'Bravo', 'diego.navarro@email.com', '+56977777777', '1958-04-25', '1985-10-12', 'pensionado', 'pensionado', NULL, 0, 'E', 0, 0),
('88888888-8', 'Sofía', 'Vega', 'Ponce', 'sofia.vega@email.com', '+56988888888', '1960-01-08', '1988-08-25', 'pensionado', 'pensionado', NULL, 0, 'E', 0, 0),
('99999999-9', 'Manuel', 'Contreras', 'Sáez', 'manuel.contreras@email.com', '+56999999999', '1955-06-20', '1982-03-15', 'pensionado', 'pensionado', NULL, 0, 'E', 0, 0),

-- Afiliado fallecido (caso especial para beneficiarios)
('10101010-1', 'Ricardo', 'Fuentes', 'Mora', NULL, NULL, '1965-11-03', '1990-05-20', 'fallecido', 'dependiente', NULL, 0, 'C', 0, 0),

-- Afiliados suspendidos
('12121212-1', 'Francisca', 'Muñoz', 'Ríos', 'francisca.munoz@email.com', '+56912121212', '1993-03-17', '2017-08-01', 'suspendido', 'dependiente', NULL, 0, 'B', 15000000, 500000),

-- Más afiliados activos para volumen
('13131313-1', 'Andrés', 'López', 'Figueroa', 'andres.lopez@email.com', '+56913131313', '1989-07-22', '2013-04-10', 'activo', 'dependiente', 'Minera Los Andes SpA', 2200000, 'B', 35000000, 4000000),
('14141414-1', 'Valentina', 'García', 'Núñez', 'valentina.garcia@email.com', '+56914141414', '1994-12-01', '2019-01-15', 'activo', 'dependiente', 'TechSolutions Chile SA', 2800000, 'A', 12000000, 6000000),
('15151515-1', 'Sebastián', 'Martínez', 'Rojas', 'sebastian.martinez@email.com', '+56915151515', '1986-09-28', '2010-06-20', 'activo', 'independiente', NULL, 1800000, 'C', 42000000, 0),
('16161616-1', 'Camila', 'Rodríguez', 'Vera', 'camila.rodriguez@email.com', '+56916161616', '1997-04-15', '2020-03-01', 'activo', 'dependiente', 'Restaurant Gourmet SpA', 850000, 'B', 5500000, 0),
('17171717-1', 'Nicolás', 'Hernández', 'Tapia', 'nicolas.hernandez@email.com', '+56917171717', '1984-08-09', '2008-11-15', 'activo', 'dependiente', 'Pesquera Austral SA', 1600000, 'D', 48000000, 2500000),
('18181818-1', 'Isidora', 'Díaz', 'Sepúlveda', 'isidora.diaz@email.com', '+56918181818', '1991-02-20', '2015-09-01', 'activo', 'dependiente', 'Clínica Salud Integral', 3500000, 'A', 25000000, 15000000),
('19191919-1', 'Matías', 'González', 'Araya', 'matias.gonzalez@email.com', '+56919191919', '1996-11-05', '2021-02-10', 'activo', 'dependiente', 'Constructora Pacífico Ltda', 1400000, 'B', 4200000, 0),

-- Afiliados inactivos
('20202020-2', 'Carolina', 'Álvarez', 'Pinto', 'carolina.alvarez@email.com', '+56920202020', '1988-06-30', '2012-07-15', 'inactivo', 'dependiente', NULL, 0, 'C', 28000000, 1500000),
('21212121-2', 'Felipe', 'Castro', 'Leiva', 'felipe.castro@email.com', '+56921212121', '1982-01-25', '2006-04-01', 'inactivo', 'independiente', NULL, 0, 'B', 55000000, 0),

-- Trabajadores de empresas morosas (más casos)
('23232323-2', 'Javiera', 'Espinoza', 'Campos', 'javiera.espinoza@email.com', '+56923232323', '1990-08-14', '2016-05-20', 'activo', 'dependiente', 'Agrícola del Sur Ltda', 780000, 'C', 12000000, 0),
('24242424-2', 'Tomás', 'Vargas', 'Molina', 'tomas.vargas@email.com', '+56924242424', '1993-03-22', '2018-09-01', 'activo', 'dependiente', 'Transportes Rápido Express', 920000, 'B', 7800000, 0),
('25252525-2', 'Antonia', 'Reyes', 'Fuentes', 'antonia.reyes@email.com', '+56925252525', '1987-12-08', '2012-02-28', 'activo', 'dependiente', 'Retail MegaStore Chile', 1050000, 'C', 22000000, 800000),

-- Afiliados jóvenes recién incorporados
('26262626-2', 'Martín', 'Sánchez', 'Ortiz', 'martin.sanchez@email.com', '+56926262626', '2000-05-10', '2023-03-15', 'activo', 'dependiente', 'TechSolutions Chile SA', 1200000, 'B', 1800000, 0),
('27272727-2', 'Florencia', 'Peña', 'Lagos', 'florencia.pena@email.com', '+56927272727', '1999-09-25', '2022-08-01', 'activo', 'dependiente', 'Restaurant Gourmet SpA', 750000, 'B', 2500000, 0),

-- Afiliados con alto patrimonio
('28282828-2', 'Eduardo', 'Montes', 'Silva', 'eduardo.montes@email.com', '+56928282828', '1975-04-18', '1998-06-01', 'activo', 'independiente', NULL, 4500000, 'A', 120000000, 35000000),
('29292929-2', 'Constanza', 'Bravo', 'Moreno', 'constanza.bravo@email.com', '+56929292929', '1978-11-30', '2000-01-15', 'activo', 'dependiente', 'Minera Los Andes SpA', 5200000, 'A', 95000000, 28000000),

-- Más afiliados para completar 50
('30303030-3', 'Gabriel', 'Núñez', 'Paredes', 'gabriel.nunez@email.com', '+56930303030', '1985-07-12', '2009-04-20', 'activo', 'dependiente', 'Constructora Pacífico Ltda', 1950000, 'B', 38000000, 3000000),
('31313131-3', 'Renata', 'Pizarro', 'Vega', 'renata.pizarro@email.com', '+56931313131', '1992-01-28', '2016-11-01', 'activo', 'dependiente', 'Clínica Salud Integral', 2600000, 'C', 19000000, 5500000),
('32323232-3', 'Joaquín', 'Salazar', 'Riquelme', 'joaquin.salazar@email.com', '+56932323232', '1988-10-05', '2012-08-15', 'activo', 'dependiente', 'Pesquera Austral SA', 1450000, 'B', 30000000, 1200000),
('34343434-3', 'Catalina', 'Medina', 'Contreras', 'catalina.medina@email.com', '+56934343434', '1995-06-20', '2019-07-01', 'activo', 'dependiente', 'TechSolutions Chile SA', 2400000, 'A', 10500000, 4000000),
('35353535-3', 'Benjamín', 'Herrera', 'Soto', 'benjamin.herrera@email.com', '+56935353535', '1983-02-14', '2007-05-10', 'activo', 'independiente', NULL, 2100000, 'C', 52000000, 0),
('36363636-3', 'Amanda', 'Jiménez', 'Carrasco', 'amanda.jimenez@email.com', '+56936363636', '1990-08-30', '2014-12-01', 'activo', 'dependiente', 'Minera Los Andes SpA', 2350000, 'B', 26000000, 7000000),
('37373737-3', 'Vicente', 'Aravena', 'Muñoz', 'vicente.aravena@email.com', '+56937373737', '1986-04-22', '2010-09-15', 'activo', 'dependiente', 'Constructora Pacífico Ltda', 1750000, 'D', 36000000, 1800000),
('38383838-3', 'Macarena', 'Figueroa', 'Díaz', 'macarena.figueroa@email.com', '+56938383838', '1994-12-10', '2018-03-20', 'activo', 'dependiente', 'Restaurant Gourmet SpA', 920000, 'B', 8200000, 0),
('39393939-3', 'Cristóbal', 'Vera', 'López', 'cristobal.vera@email.com', '+56939393939', '1981-09-08', '2005-02-01', 'activo', 'dependiente', 'Pesquera Austral SA', 1680000, 'C', 58000000, 4500000),
('40404040-4', 'Fernanda', 'Tapia', 'González', 'fernanda.tapia@email.com', '+56940404040', '1997-03-25', '2020-06-15', 'activo', 'dependiente', 'Clínica Salud Integral', 2200000, 'B', 6800000, 2000000)
ON CONFLICT (rut) DO NOTHING;

-- ============================================================================
-- Beneficiarios
-- ============================================================================

INSERT INTO beneficiarios (afiliado_rut, rut_beneficiario, nombre, parentesco, porcentaje_asignado, es_invalido, fecha_nacimiento, vigente) VALUES
-- Beneficiarios del afiliado fallecido
('10101010-1', '10101010-2', 'Elena Fuentes Mora', 'conyuge', 60.00, FALSE, '1968-03-15', TRUE),
('10101010-1', '10101010-3', 'Carlos Fuentes Torres', 'hijo', 20.00, FALSE, '1995-07-22', TRUE),
('10101010-1', '10101010-4', 'Andrea Fuentes Torres', 'hijo', 20.00, FALSE, '1998-11-10', TRUE),

-- Beneficiarios de pensionados
('77777777-7', '77777777-8', 'Marta Navarro López', 'conyuge', 100.00, FALSE, '1962-05-20', TRUE),
('88888888-8', '88888888-9', 'Jorge Vega Muñoz', 'conyuge', 50.00, FALSE, '1958-08-12', TRUE),
('88888888-8', '88888888-0', 'Lucía Vega Ponce', 'hijo', 50.00, TRUE, '1985-02-28', TRUE),

-- Beneficiarios de afiliados activos
('12345678-9', '12345678-0', 'Paula Pérez Silva', 'conyuge', 60.00, FALSE, '1987-09-10', TRUE),
('12345678-9', '12345679-1', 'Tomás Pérez Silva', 'hijo', 40.00, FALSE, '2015-04-20', TRUE),
('98765432-1', '98765432-2', 'Carlos Silva Rojas', 'conviviente', 100.00, FALSE, '1988-12-05', TRUE),
('28282828-2', '28282828-3', 'Daniela Montes Vega', 'conyuge', 50.00, FALSE, '1978-06-15', TRUE),
('28282828-2', '28282828-4', 'Lucas Montes Vega', 'hijo', 25.00, FALSE, '2005-03-22', TRUE),
('28282828-2', '28282828-5', 'Emma Montes Vega', 'hijo', 25.00, FALSE, '2008-11-08', TRUE)
ON CONFLICT (afiliado_rut, rut_beneficiario) DO NOTHING;

-- ============================================================================
-- Aportes (historial de 2 años: 2023-2024)
-- ============================================================================

-- Función auxiliar para generar aportes masivos
DO $$
DECLARE
    v_rut VARCHAR(12);
    v_mes INTEGER;
    v_ano INTEGER;
    v_empleador VARCHAR(255);
    v_monto DECIMAL(12,2);
    v_tipo VARCHAR(50);
BEGIN
    -- Para cada afiliado activo dependiente
    FOR v_rut, v_empleador IN
        SELECT rut, empleador FROM afiliados
        WHERE estado = 'activo' AND tipo_afiliado = 'dependiente' AND empleador IS NOT NULL
    LOOP
        -- Generar aportes mensuales para 2023 y 2024
        FOR v_ano IN 2023..2024 LOOP
            FOR v_mes IN 1..12 LOOP
                -- Saltar meses futuros de 2024
                IF v_ano = 2024 AND v_mes > 11 THEN
                    CONTINUE;
                END IF;

                -- Monto base según empleador (varía por empresa)
                v_monto := CASE
                    WHEN v_empleador LIKE '%Minera%' THEN 180000 + (RANDOM() * 50000)::INTEGER
                    WHEN v_empleador LIKE '%Tech%' THEN 220000 + (RANDOM() * 60000)::INTEGER
                    WHEN v_empleador LIKE '%Clínica%' THEN 200000 + (RANDOM() * 40000)::INTEGER
                    WHEN v_empleador LIKE '%Constructora%' THEN 140000 + (RANDOM() * 30000)::INTEGER
                    ELSE 100000 + (RANDOM() * 40000)::INTEGER
                END;

                -- Insertar aporte obligatorio
                INSERT INTO aportes (afiliado_rut, periodo, monto, fecha_pago, tipo, estado, empleador, comision, seguro)
                VALUES (
                    v_rut,
                    v_ano || '-' || LPAD(v_mes::TEXT, 2, '0'),
                    v_monto,
                    MAKE_DATE(v_ano, v_mes, 10 + (RANDOM() * 5)::INTEGER),
                    'obligatorio',
                    CASE
                        -- Empleadores morosos tienen aportes en cobranza
                        WHEN v_empleador IN ('Agrícola del Sur Ltda', 'Transportes Rápido Express', 'Retail MegaStore Chile')
                             AND v_ano = 2024 AND v_mes >= 8 THEN 'en_cobranza'
                        ELSE 'procesado'
                    END,
                    v_empleador,
                    v_monto * 0.0116,  -- Comisión 1.16%
                    v_monto * 0.0141   -- Seguro 1.41%
                );
            END LOOP;
        END LOOP;
    END LOOP;
END $$;

-- Aportes voluntarios (APV) para algunos afiliados
INSERT INTO aportes (afiliado_rut, periodo, monto, fecha_pago, tipo, estado, descripcion) VALUES
('12345678-9', '2024-01', 200000, '2024-01-20', 'apv', 'procesado', 'Aporte voluntario mensual'),
('12345678-9', '2024-02', 200000, '2024-02-20', 'apv', 'procesado', 'Aporte voluntario mensual'),
('12345678-9', '2024-03', 200000, '2024-03-20', 'apv', 'procesado', 'Aporte voluntario mensual'),
('98765432-1', '2024-01', 500000, '2024-01-15', 'apv', 'procesado', 'Bono anual empresa'),
('22222222-2', '2024-06', 1000000, '2024-06-30', 'apv', 'procesado', 'Aporte extraordinario'),
('28282828-2', '2024-01', 2000000, '2024-01-10', 'apv', 'procesado', 'APV régimen A'),
('28282828-2', '2024-07', 2000000, '2024-07-10', 'apv', 'procesado', 'APV régimen A'),
('29292929-2', '2024-03', 1500000, '2024-03-15', 'deposito_convenido', 'procesado', 'Depósito convenido empresa'),
('18181818-1', '2024-02', 300000, '2024-02-28', 'apv', 'procesado', 'APV mensual');

-- Aportes para independientes
INSERT INTO aportes (afiliado_rut, periodo, monto, fecha_pago, tipo, estado, descripcion) VALUES
('33333333-3', '2024-01', 150000, '2024-02-15', 'obligatorio', 'procesado', 'Cotización como independiente'),
('33333333-3', '2024-02', 150000, '2024-03-12', 'obligatorio', 'procesado', 'Cotización como independiente'),
('33333333-3', '2024-03', 150000, '2024-04-10', 'obligatorio', 'procesado', 'Cotización como independiente'),
('15151515-1', '2024-01', 180000, '2024-02-20', 'obligatorio', 'procesado', 'Declaración renta'),
('15151515-1', '2024-02', 180000, '2024-03-18', 'obligatorio', 'procesado', 'Declaración renta'),
('35353535-3', '2024-01', 210000, '2024-02-10', 'obligatorio', 'procesado', 'Honorarios'),
('35353535-3', '2024-02', 210000, '2024-03-08', 'obligatorio', 'procesado', 'Honorarios');

-- ============================================================================
-- Traspasos
-- ============================================================================

INSERT INTO traspasos (afiliado_rut, afp_origen, afp_destino, monto_obligatorio, monto_voluntario, fecha_solicitud, fecha_ejecucion, estado, numero_solicitud) VALUES
('12345678-9', 'AFP Habitat', 'AFP Capital', 42000000, 4500000, '2023-06-15', '2023-07-20', 'completado', 'TRP-2023-00156'),
('98765432-1', 'AFP Provida', 'AFP Cuprum', 25000000, 7500000, '2023-09-10', '2023-10-15', 'completado', 'TRP-2023-00289'),
('11111111-1', 'AFP Modelo', 'AFP PlanVital', 30000000, 1800000, '2024-03-01', '2024-04-05', 'completado', 'TRP-2024-00078'),
('22222222-2', 'AFP Cuprum', 'AFP Habitat', 20000000, 11000000, '2024-08-15', NULL, 'en_proceso', 'TRP-2024-00234'),
('44444444-4', 'AFP Capital', 'AFP Provida', 8000000, 0, '2024-09-20', NULL, 'pendiente', 'TRP-2024-00298'),
('14141414-1', 'AFP Habitat', 'AFP Modelo', 11500000, 5800000, '2024-10-01', NULL, 'pendiente', 'TRP-2024-00312'),
('30303030-3', 'AFP PlanVital', 'AFP Capital', 36000000, 2800000, '2024-07-10', '2024-08-15', 'completado', 'TRP-2024-00189'),
('55555555-5', 'AFP Cuprum', 'AFP Habitat', 50000000, 3200000, '2024-05-20', NULL, 'rechazado', 'TRP-2024-00145'),
('20202020-2', 'AFP Modelo', 'AFP Provida', 26000000, 1200000, '2022-11-15', '2022-12-20', 'completado', 'TRP-2022-00456')
ON CONFLICT DO NOTHING;

-- Agregar motivo de rechazo
UPDATE traspasos SET motivo_rechazo = 'Documentación incompleta. Falta certificado de cotizaciones del empleador.' WHERE numero_solicitud = 'TRP-2024-00145';

-- ============================================================================
-- Reclamos (variados para demostrar diferentes escenarios)
-- ============================================================================

INSERT INTO reclamos (numero_ticket, afiliado_rut, tipo, canal, descripcion, monto_reclamado, prioridad, estado, resolucion, fecha_creacion, fecha_resolucion, agente_asignado, satisfaccion_cliente) VALUES
-- Reclamos resueltos
('RCL-2024-00001', '12345678-9', 'error_saldo', 'web', 'Mi saldo en la cartola no coincide con los aportes que he realizado. Falta reflejar el aporte de diciembre 2023.', 180000, 'media', 'resuelto', 'Se verificó el aporte y se realizó ajuste en cuenta. El aporte estaba mal imputado al periodo anterior.', '2024-01-15 10:30:00', '2024-01-18 14:20:00', 'Ana García', 5),
('RCL-2024-00002', '98765432-1', 'atencion_cliente', 'telefono', 'No pude acceder a mi cuenta en línea por más de una semana. La contraseña no funcionaba.', NULL, 'baja', 'resuelto', 'Se reseteó la contraseña y se verificó acceso exitoso del afiliado.', '2024-01-20 09:15:00', '2024-01-20 11:30:00', 'Carlos Muñoz', 4),
('RCL-2024-00003', '11111111-1', 'traspaso', 'presencial', 'Solicité traspaso hace 3 meses y aún no se ejecuta. Necesito información sobre el estado.', NULL, 'alta', 'resuelto', 'Traspaso completado el 05/04/2024. Se informó al afiliado y se envió comprobante por email.', '2024-02-28 16:00:00', '2024-04-06 09:00:00', 'María López', 3),

-- Reclamos abiertos/en proceso
('RCL-2024-00004', '44444444-4', 'retraso_pago', 'web', 'Mi empleador no ha pagado mis cotizaciones de los últimos 3 meses. Necesito que inicien cobranza.', 2850000, 'urgente', 'en_revision', NULL, '2024-09-05 11:20:00', NULL, 'Pedro Soto', NULL),
('RCL-2024-00005', '55555555-5', 'cobro_indebido', 'email', 'Me cobraron comisión doble en el mes de agosto. Solicito devolución del monto cobrado en exceso.', 15000, 'media', 'abierto', NULL, '2024-09-10 08:45:00', NULL, NULL, NULL),
('RCL-2024-00006', '66666666-6', 'retraso_pago', 'telefono', 'La empresa donde trabajo está en cobranza pero sigo trabajando. Mis cotizaciones no aparecen hace 4 meses.', 4200000, 'urgente', 'escalado', NULL, '2024-08-20 14:30:00', NULL, 'Jefe Operaciones', NULL),
('RCL-2024-00007', '22222222-2', 'cambio_fondo', 'web', 'Solicité cambio de fondo A a fondo C hace 2 meses y aún figura fondo A en mi cuenta.', NULL, 'alta', 'pendiente_info', NULL, '2024-09-15 10:00:00', NULL, 'Ana García', NULL),

-- Reclamos de pensionados
('RCL-2024-00008', '77777777-7', 'pension_no_pagada', 'presencial', 'No recibí el pago de mi pensión del mes de octubre. Mi cuenta está correcta.', 450000, 'urgente', 'en_revision', NULL, '2024-10-05 09:30:00', NULL, 'María López', NULL),
('RCL-2024-00009', '88888888-8', 'informacion_incorrecta', 'carta', 'Los datos de mi beneficiario están incorrectos en el sistema. Mi hijo tiene invalidez y no aparece registrado.', NULL, 'alta', 'abierto', NULL, '2024-09-25 00:00:00', NULL, NULL, NULL),

-- Reclamo sobre bono de reconocimiento
('RCL-2024-00010', '99999999-9', 'bono_reconocimiento', 'presencial', 'Solicito información sobre el estado de mi bono de reconocimiento. Tengo cotizaciones anteriores a 1981.', NULL, 'media', 'en_revision', NULL, '2024-08-10 11:00:00', NULL, 'Carlos Muñoz', NULL),

-- Más reclamos para volumen
('RCL-2024-00011', '23232323-2', 'retraso_pago', 'web', 'Mi empleador Agrícola del Sur no paga cotizaciones desde julio. Necesito certificado de deuda.', 3120000, 'alta', 'abierto', NULL, '2024-10-01 15:20:00', NULL, NULL, NULL),
('RCL-2024-00012', '24242424-2', 'retraso_pago', 'telefono', 'Transportes Rápido Express no ha pagado. Ya van 4 meses sin cotizaciones.', 3680000, 'urgente', 'en_revision', NULL, '2024-09-28 10:15:00', NULL, 'Pedro Soto', NULL),
('RCL-2024-00013', '25252525-2', 'retraso_pago', 'email', 'Trabajo en Retail MegaStore y no me han pagado las cotizaciones. Solicito intervención.', 4200000, 'alta', 'abierto', NULL, '2024-10-10 09:00:00', NULL, NULL, NULL),

-- Reclamo cerrado sin resolución favorable
('RCL-2024-00014', '20202020-2', 'otro', 'web', 'Solicito retiro del 10% de mis fondos.', 2800000, 'media', 'cerrado', 'Solicitud rechazada. No existe normativa vigente que permita este retiro. Se informó al afiliado sobre las modalidades de pensión disponibles.', '2024-03-15 12:00:00', '2024-03-16 09:30:00', 'Ana García', 1),

-- Reclamo complejo multi-tema
('RCL-2024-00015', '28282828-2', 'error_saldo', 'presencial', 'Detecté diferencias en mi saldo de APV. Además, el cambio de fondo que solicité no se aplicó correctamente. Necesito revisión completa de mi cuenta.', 2500000, 'alta', 'en_revision', NULL, '2024-10-08 16:45:00', NULL, 'Jefe Operaciones', NULL)
ON CONFLICT (numero_ticket) DO NOTHING;

-- ============================================================================
-- Pensiones
-- ============================================================================

INSERT INTO pensiones (afiliado_rut, tipo_pension, modalidad, monto_mensual, fecha_inicio, estado, compania_seguros) VALUES
('77777777-7', 'vejez_normal', 'retiro_programado', 485000, '2023-05-01', 'activa', NULL),
('88888888-8', 'vejez_normal', 'renta_vitalicia', 520000, '2025-02-01', 'activa', 'Compañía de Seguros Confuturo'),
('99999999-9', 'vejez_anticipada', 'mixta', 380000, '2020-07-01', 'activa', 'MetLife Chile'),
('10101010-1', 'sobrevivencia', 'renta_vitalicia', 420000, '2022-03-15', 'activa', 'Compañía de Seguros Consorcio')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Movimientos (últimos movimientos relevantes)
-- ============================================================================

INSERT INTO movimientos (afiliado_rut, tipo_movimiento, monto, saldo_anterior, saldo_posterior, fondo, fecha_movimiento, descripcion) VALUES
-- Movimientos de Juan Pérez
('12345678-9', 'aporte', 195000, 44805000, 45000000, 'B', '2024-10-15', 'Aporte obligatorio octubre 2024'),
('12345678-9', 'rentabilidad', 450000, 45000000, 45450000, 'B', '2024-10-31', 'Rentabilidad mensual fondo B'),
('12345678-9', 'comision', -22620, 45450000, 45427380, 'B', '2024-10-31', 'Comisión mensual'),

-- Movimientos de María Silva
('98765432-1', 'aporte', 256000, 27744000, 28000000, 'C', '2024-10-12', 'Aporte obligatorio octubre 2024'),
('98765432-1', 'rentabilidad', 280000, 28000000, 28280000, 'C', '2024-10-31', 'Rentabilidad mensual fondo C'),

-- Traspaso completado
('11111111-1', 'traspaso_entrada', 31800000, 200000, 32000000, 'B', '2024-04-05', 'Traspaso desde AFP Modelo'),

-- Pensión
('77777777-7', 'pension', -485000, 485000, 0, 'E', '2024-10-05', 'Pago pensión octubre 2024'),

-- Cambio de fondo
('22222222-2', 'cambio_fondo', 0, 22000000, 22000000, 'A', '2024-07-15', 'Cambio de fondo C a A'),

-- Bono de reconocimiento
('99999999-9', 'bono_reconocimiento', 8500000, 0, 8500000, 'E', '2020-07-01', 'Bono de reconocimiento IPS')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Verificación final
-- ============================================================================

SELECT 'Seed data cargado correctamente' AS status;
SELECT
    (SELECT COUNT(*) FROM afiliados) AS afiliados,
    (SELECT COUNT(*) FROM empleadores) AS empleadores,
    (SELECT COUNT(*) FROM beneficiarios) AS beneficiarios,
    (SELECT COUNT(*) FROM aportes) AS aportes,
    (SELECT COUNT(*) FROM traspasos) AS traspasos,
    (SELECT COUNT(*) FROM reclamos) AS reclamos,
    (SELECT COUNT(*) FROM pensiones) AS pensiones,
    (SELECT COUNT(*) FROM movimientos) AS movimientos;
