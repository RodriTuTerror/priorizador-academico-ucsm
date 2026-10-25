-- ============================================================================
-- Sistema de Priorización de Carga Académica Semanal + Réplica Moodle UCSM
-- Fase II: Script de Inicialización y Datos Semilla en PostgreSQL
-- ============================================================================

DROP TABLE IF EXISTS tareas_moodle;

CREATE TABLE tareas_moodle (
    id_tarea SERIAL PRIMARY KEY,
    curso VARCHAR(120) NOT NULL,
    nombre_actividad VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_limite TIMESTAMP NOT NULL,
    esfuerzo_estimado NUMERIC(5, 2) DEFAULT NULL,
    importancia VARCHAR(10) DEFAULT NULL,
    estado_entrega BOOLEAN DEFAULT FALSE,
    archivo_entregado VARCHAR(255) DEFAULT NULL,
    comentario_entrega TEXT DEFAULT NULL,
    fecha_entrega TIMESTAMP DEFAULT NULL
);

-- Inserción de 4 tareas de prueba realistas de Ingeniería de Sistemas UCSM
-- Se emplean intervalos dinámicos respecto a NOW() para garantizar plazos vigentes.
INSERT INTO tareas_moodle (
    curso,
    nombre_actividad,
    descripcion,
    fecha_limite,
    esfuerzo_estimado,
    importancia,
    estado_entrega,
    archivo_entregado,
    comentario_entrega,
    fecha_entrega
) VALUES
(
    'Pensamiento Computacional',
    'Cuestionario corto Semana 9',
    'Resolver el cuestionario rápido de 10 preguntas sobre estructuras de datos elementales (listas, tuplas y diccionarios) y complejidad básica en el Aula Virtual.',
    NOW() + INTERVAL '4 hours',
    NULL,
    NULL,
    FALSE,
    NULL,
    NULL,
    NULL
),
(
    'Pensamiento Computacional',
    'Avance Proyecto Final Fase II',
    'Entrega obligatoria del prototipo funcional en Python aplicando arquitectura Functional Core, Imperative Shell. Debe incluir el núcleo determinista puro (validador, calculador y procesador con doble desempate), integración con base de datos PostgreSQL, réplica web de Moodle en Flask y la suite completa de 7 casos de prueba oficiales de la rúbrica (3 normales, 2 límite y 2 inválidos) ejecutables con pytest.',
    NOW() + INTERVAL '12 hours',
    NULL,
    NULL,
    FALSE,
    NULL,
    NULL,
    NULL
),
(
    'Estructuras Discretas',
    'Práctica de programación en lógica',
    'Implementar y documentar la resolución de 5 ejercicios sobre tablas de verdad, inferencia proposicional, relaciones de equivalencia y grafos dirigidos, adjuntando el código fuente y un informe con capturas de ejecución.',
    NOW() + INTERVAL '36 hours',
    NULL,
    NULL,
    FALSE,
    NULL,
    NULL,
    NULL
),
(
    'Ingeniería de Sistemas',
    'Lectura de capítulo de sistemas de información',
    'Leer el Capítulo 3 sobre Sistemas de Información Gerencial y elaborar un resumen ejecutivo de una página identificando los componentes sociotécnicos de una organización.',
    NOW() + INTERVAL '60 hours',
    NULL,
    NULL,
    FALSE,
    NULL,
    NULL,
    NULL
);
