# Sistema de Priorización de Carga Académica Semanal + Réplica Moodle UCSM (Fase II)

## 1. Propósito y Arquitectura (Functional Core, Imperative Shell)
Sistema de soporte a la decisión para estudiantes de la UCSM (Curso: Pensamiento Computacional). Prioriza las actividades pendientes combinando urgencia, esfuerzo estimado e importancia.

El sistema se divide en 4 capas estrictamente desacopladas:
1. **Base de Datos y Persistencia (`src/datos/` + PostgreSQL):** Almacena cursos, tareas (con descripción y fecha límite) y el estado/archivo de las entregas.
2. **Réplica Web de Moodle UCSM (`moodle_replica/`):** Servidor ligero en Flask conectado a PostgreSQL. Permite crear tareas de prueba, visualizar descripciones/plazos y verificar los archivos entregados desde el programa en consola.
3. **Núcleo Algorítmico Determinista (`src/core/`):** 100% Python estándar (CERO librerías externas, cero llamadas a BD o HTTP). Implementa validaciones, cálculo de puntajes y ordenamiento multicriterio para cumplir la rúbrica de Fase II.
4. **Módulo de Agente (`src/agente/`):** ESTRICTAMENTE VACÍO en Fase II. Reservado para la Fase III (inferencia de esfuerzo/importancia mediante IA leyendo la descripción y generación de analítica).

## 2. Estructura Oficial del Repositorio
```text
priorizador-academico-ucsm/
├── .env.example                  # Plantilla de variables de conexión a PostgreSQL
├── .gitignore                    # Ignora .venv/, __pycache__/, .env, data/entregas_subidas/*
├── README.md                     # Documentación de arquitectura y estructura del proyecto
├── requirements.txt              # psycopg2-binary, flask, pytest, python-dotenv
├── sql/
│   └── init_db.sql               # Creación de tablas en PostgreSQL y datos semilla UCSM
├── data/
│   └── entregas_subidas/         # Almacenamiento físico de archivos subidos (.pdf, .py, .zip)
├── moodle_replica/
│   ├── __init__.py
│   ├── app.py                    # Servidor Flask (puerto 5000) conectado a PostgreSQL
│   └── templates/
│       └── index.html            # Interfaz elemental del Aula Virtual UCSM
├── src/
│   ├── __init__.py
│   ├── core/                     # NÚCLEO PURO FASE II (Sin dependencias externas)
│   │   ├── __init__.py
│   │   ├── validador.py          # Presencia, Rango (0 < e <= 80), Pertenencia, Consistencia (e <= t)
│   │   ├── calculador.py         # Puntajes [3, 9] y etiquetas ("CRÍTICO", "ALTO", "MEDIO", "BAJO")
│   │   └── procesador.py         # Filtrado y ordenamiento con doble desempate (-puntaje, t, -imp)
│   ├── datos/                    # CAPA DE PERSISTENCIA POSTGRESQL
│   │   ├── __init__.py
│   │   └── repositorio_moodle.py # CRUD de tareas en Postgres y gestión de subida de archivos
│   └── agente/                   # VACÍO EN FASE II (Reservado para Fase III)
│       └── __init__.py
├── tests/
│   └── test_fase2_rubrica.py     # 7 casos oficiales de la rúbrica (3 Normales, 2 Límite, 2 Inválidos)
└── main.py                       # Menú en consola (Sincronizar BD, Priorizar, Subir Entrega)