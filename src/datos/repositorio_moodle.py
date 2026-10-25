"""Operaciones CRUD de cursos y tareas en PostgreSQL y gestión de subida de archivos de entregas.

Capa Imperativa de Persistencia (Fase II) conectada a PostgreSQL (`moodle_ucsm`).
"""

import os
import shutil
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from src.core.validador import (
    validar_extension_archivo,
    validar_pertenencia_importancia,
    validar_presencia,
    validar_rango_esfuerzo,
)

RAIZ_PROYECTO: Path = Path(__file__).resolve().parent.parent.parent
RUTA_ENV: Path = RAIZ_PROYECTO / ".env"
RUTA_SQL_INIT: Path = RAIZ_PROYECTO / "sql" / "init_db.sql"
DIRECTORIO_ENTREGAS: Path = RAIZ_PROYECTO / "data" / "entregas_subidas"
SQLSTATE_BD_INEXISTENTE: str = "3D000"

load_dotenv(dotenv_path=RUTA_ENV)


def obtener_configuracion_bd() -> dict[str, str]:
    """Obtiene los parámetros de conexión a PostgreSQL desde las variables de entorno."""
    load_dotenv(dotenv_path=RUTA_ENV)
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME", "moodle_ucsm"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }


def _asegurar_existencia_bd(config: dict[str, str]) -> None:
    """Verifica que la base de datos objetivo exista en PostgreSQL; si no existe, la crea."""
    nombre_bd: str = config["dbname"]
    conn_admin = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        dbname="postgres",
        user=config["user"],
        password=config["password"],
    )
    conn_admin.autocommit = True
    try:
        with conn_admin.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s;",
                (nombre_bd,),
            )
            existe = cur.fetchone()
            if not existe:
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre_bd))
                )
    finally:
        conn_admin.close()


def obtener_conexion():
    """Establece y retorna una conexión activa a la base de datos PostgreSQL.

    Utiliza el código estándar SQLSTATE `3D000` (`INVALID_CATALOG_NAME`) para detectar
    de forma independiente del idioma/locale si la base de datos aún no ha sido creada.
    """
    config: dict[str, str] = obtener_configuracion_bd()
    try:
        return psycopg2.connect(**config)
    except psycopg2.OperationalError as err:
        codigo_sqlstate = getattr(err, "pgcode", None)
        mensaje_err: str = str(err).lower()
        if (
            codigo_sqlstate == SQLSTATE_BD_INEXISTENTE
            or "does not exist" in mensaje_err
            or "no existe la base de datos" in mensaje_err
        ):
            _asegurar_existencia_bd(config)
            return psycopg2.connect(**config)
        raise


def asegurar_esquema_bd() -> bool:
    """Garantiza de forma NO destructiva que la tabla `tareas_moodle` y sus columnas existan."""
    ddl_no_destructivo: str = """
        CREATE TABLE IF NOT EXISTS tareas_moodle (
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
        ALTER TABLE tareas_moodle
            ADD COLUMN IF NOT EXISTS esfuerzo_estimado NUMERIC(5, 2) DEFAULT NULL;
        ALTER TABLE tareas_moodle
            ADD COLUMN IF NOT EXISTS importancia VARCHAR(10) DEFAULT NULL;
    """
    try:
        conn = obtener_conexion()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(ddl_no_destructivo)
            return True
        finally:
            conn.close()
    except Exception:
        return False


def limpiar_archivos_entregas() -> None:
    """Elimina archivos huérfanos en `data/entregas_subidas/` preservando `.gitkeep`."""
    DIRECTORIO_ENTREGAS.mkdir(parents=True, exist_ok=True)
    for archivo in DIRECTORIO_ENTREGAS.iterdir():
        if archivo.is_file() and archivo.name != ".gitkeep":
            try:
                archivo.unlink()
            except OSError:
                pass


def inicializar_bd() -> bool:
    """Ejecuta el script `sql/init_db.sql` sobre `moodle_ucsm` y limpia entregas previas.

    Returns:
        True si la inicialización y carga de datos semilla se completó con éxito,
        False en caso de error.
    """
    if not RUTA_SQL_INIT.is_file():
        print(f"[ERROR BD] No se encontró el archivo SQL en: {RUTA_SQL_INIT}")
        return False

    try:
        script_sql: str = RUTA_SQL_INIT.read_text(encoding="utf-8")
        conn = obtener_conexion()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(script_sql)
            limpiar_archivos_entregas()
            return True
        finally:
            conn.close()
    except Exception as exc:
        print(f"[ERROR BD] Falló la inicialización de la base de datos: {exc}")
        return False


def _normalizar_fila_tarea(fila: dict) -> dict:
    """Convierte tipos Decimal/SQL de una fila de PostgreSQL a tipos nativos de Python."""
    item: dict = dict(fila)
    item["tiempo_restante"] = round(float(item["tiempo_restante"]), 2)
    if item.get("esfuerzo_estimado") is not None:
        item["esfuerzo_estimado"] = round(float(item["esfuerzo_estimado"]), 2)
    else:
        item["esfuerzo_estimado"] = None

    if item.get("importancia") is not None and str(item["importancia"]).strip() != "":
        item["importancia"] = str(item["importancia"]).strip().upper()
    else:
        item["importancia"] = None
    return item


def obtener_tareas_pendientes() -> list[dict]:
    """Consulta las tareas con `estado_entrega = FALSE` y `fecha_limite > NOW()`.

    Calcula dinámicamente `tiempo_restante` en horas (`float` redondeado a 2 decimales)
    a partir de la diferencia `fecha_limite - NOW()`.

    Returns:
        Lista de diccionarios con las tareas pendientes y vigentes.
    """
    asegurar_esquema_bd()
    consulta_sql: str = """
        SELECT
            id_tarea,
            curso,
            nombre_actividad,
            descripcion,
            fecha_limite,
            esfuerzo_estimado,
            importancia,
            estado_entrega,
            archivo_entregado,
            comentario_entrega,
            fecha_entrega,
            ROUND((EXTRACT(EPOCH FROM (fecha_limite - NOW())) / 3600.0)::numeric, 2) AS tiempo_restante
        FROM tareas_moodle
        WHERE estado_entrega = FALSE
          AND fecha_limite > NOW()
        ORDER BY fecha_limite ASC, id_tarea ASC;
    """
    conn = obtener_conexion()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(consulta_sql)
            filas = cur.fetchall()
            tareas: list[dict] = []
            for fila in filas:
                tareas.append(_normalizar_fila_tarea(fila))
            return tareas
    finally:
        conn.close()


def obtener_todas_las_tareas() -> list[dict]:
    """Obtiene todas las tareas registradas (pendientes y entregadas) para la Réplica Web de Moodle.

    Returns:
        Lista de diccionarios con todas las tareas ordenadas por ID.
    """
    asegurar_esquema_bd()
    consulta_sql: str = """
        SELECT
            id_tarea,
            curso,
            nombre_actividad,
            descripcion,
            fecha_limite,
            esfuerzo_estimado,
            importancia,
            estado_entrega,
            archivo_entregado,
            comentario_entrega,
            fecha_entrega,
            ROUND((EXTRACT(EPOCH FROM (fecha_limite - NOW())) / 3600.0)::numeric, 2) AS tiempo_restante
        FROM tareas_moodle
        ORDER BY id_tarea ASC;
    """
    conn = obtener_conexion()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(consulta_sql)
            filas = cur.fetchall()
            tareas: list[dict] = []
            for fila in filas:
                tareas.append(_normalizar_fila_tarea(fila))
            return tareas
    finally:
        conn.close()


def crear_tarea_moodle(
    curso: str,
    nombre_actividad: str,
    descripcion: str,
    horas_plazo: float,
) -> int:
    """Inserta una nueva tarea académica en PostgreSQL con fecha límite relativa a `NOW()`.

    Args:
        curso: Nombre de la asignatura.
        nombre_actividad: Título de la actividad académica.
        descripcion: Enunciado e instrucciones detalladas de la tarea.
        horas_plazo: Horas disponibles desde el momento actual hasta el cierre.

    Returns:
        El identificador `id_tarea` generado para la nueva tarea.

    Raises:
        ValueError: Si algún campo de texto está vacío o `horas_plazo <= 0`.
    """
    for valor, campo in (
        (curso, "curso"),
        (nombre_actividad, "nombre_actividad"),
        (descripcion, "descripcion"),
    ):
        ok, msg = validar_presencia(valor, campo)
        if not ok:
            raise ValueError(msg)

    plazo: float = float(horas_plazo)
    if not (plazo > 0.0 and plazo != float("inf")):
        raise ValueError("El plazo en horas debe ser un número finito mayor a 0.0.")

    asegurar_esquema_bd()
    insertar_sql: str = """
        INSERT INTO tareas_moodle (
            curso,
            nombre_actividad,
            descripcion,
            fecha_limite,
            estado_entrega
        )
        VALUES (%s, %s, %s, NOW() + (%s * INTERVAL '1 hour'), FALSE)
        RETURNING id_tarea;
    """
    conn = obtener_conexion()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    insertar_sql,
                    (curso.strip(), nombre_actividad.strip(), descripcion.strip(), plazo),
                )
                fila = cur.fetchone()
                return int(fila[0])
    finally:
        conn.close()


def guardar_estimacion_tarea(
    id_tarea: int,
    esfuerzo_estimado: float,
    importancia: str,
) -> tuple[bool, str]:
    """Guarda o actualiza en PostgreSQL el esfuerzo estimado y la importancia de una tarea.

    Permite que la planificación del estudiante (o la inferencia futura del Agente en Fase III)
    persista entre sesiones tanto en consola como en la interfaz web.
    """
    ok_esf, msg_esf = validar_rango_esfuerzo(esfuerzo_estimado)
    if not ok_esf:
        return (False, msg_esf)

    ok_imp, msg_imp = validar_pertenencia_importancia(importancia)
    if not ok_imp:
        return (False, msg_imp)

    esfuerzo_val: float = round(float(esfuerzo_estimado), 2)
    importancia_val: str = importancia.strip().upper()

    try:
        conn = obtener_conexion()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE tareas_moodle
                        SET esfuerzo_estimado = %s,
                            importancia = %s
                        WHERE id_tarea = %s;
                        """,
                        (esfuerzo_val, importancia_val, int(id_tarea)),
                    )
                    if cur.rowcount == 0:
                        return (
                            False,
                            f"No se encontró ninguna tarea con id_tarea = {id_tarea}.",
                        )
            return (
                True,
                f"Estimación guardada para la tarea #{id_tarea} (Esfuerzo: {esfuerzo_val:.2f} h, Importancia: {importancia_val}).",
            )
        finally:
            conn.close()
    except Exception as exc:
        return (False, f"Error al guardar la estimación en PostgreSQL: {exc}")


def entregar_tarea(
    id_tarea: int,
    ruta_archivo_origen: str,
    comentario: str,
) -> tuple[bool, str]:
    """Registra la entrega de una tarea copiando el archivo a `data/entregas_subidas/` y actualizando PostgreSQL.

    Args:
        id_tarea: Identificador único de la tarea en `tareas_moodle`.
        ruta_archivo_origen: Ruta local del archivo que el estudiante desea entregar.
        comentario: Comentario opcional o nota de entrega del estudiante.

    Returns:
        Tupla `(exito, mensaje)` indicando si la operación fue realizada satisfactoriamente.
    """
    ok_ruta, msg_ruta = validar_presencia(ruta_archivo_origen, "ruta_archivo_origen")
    if not ok_ruta:
        return (False, msg_ruta)

    ruta_origen: Path = Path(ruta_archivo_origen.strip()).expanduser()
    es_ext_valida, msg_ext = validar_extension_archivo(ruta_origen.name)
    if not es_ext_valida:
        return (False, msg_ext)

    if not ruta_origen.is_file():
        return (
            False,
            f"Error de archivo: No existe el archivo local en la ruta '{ruta_origen}'.",
        )

    DIRECTORIO_ENTREGAS.mkdir(parents=True, exist_ok=True)
    nombre_destino: str = f"tarea_{int(id_tarea)}_{ruta_origen.name}"
    ruta_destino: Path = DIRECTORIO_ENTREGAS / nombre_destino

    try:
        conn = obtener_conexion()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            id_tarea,
                            nombre_actividad,
                            estado_entrega,
                            (fecha_limite > NOW()) AS plazo_vigente
                        FROM tareas_moodle
                        WHERE id_tarea = %s;
                        """,
                        (int(id_tarea),),
                    )
                    tarea = cur.fetchone()
                    if not tarea:
                        return (
                            False,
                            f"No existe ninguna tarea registrada con id_tarea = {id_tarea}.",
                        )
                    if not bool(tarea["plazo_vigente"]):
                        return (
                            False,
                            f"La fecha límite para la tarea '{tarea['nombre_actividad']}' ya ha vencido.",
                        )

                    if ruta_origen.resolve() != ruta_destino.resolve():
                        shutil.copy2(ruta_origen, ruta_destino)

                    comentario_limpio: str = (
                        comentario.strip() if isinstance(comentario, str) else ""
                    )
                    cur.execute(
                        """
                        UPDATE tareas_moodle
                        SET estado_entrega = TRUE,
                            archivo_entregado = %s,
                            comentario_entrega = %s,
                            fecha_entrega = NOW()
                        WHERE id_tarea = %s;
                        """,
                        (nombre_destino, comentario_limpio, int(id_tarea)),
                    )
            return (
                True,
                f"Entrega registrada exitosamente para '{tarea['nombre_actividad']}'. "
                f"Archivo guardado en: data/entregas_subidas/{nombre_destino}",
            )
        finally:
            conn.close()
    except Exception as exc:
        return (False, f"Error al registrar la entrega en la base de datos: {exc}")
