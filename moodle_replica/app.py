"""Servidor ligero en Flask (puerto 5000) conectado a PostgreSQL para simular el Aula Virtual UCSM."""

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

# Garantiza que la raíz del proyecto esté en sys.path al ejecutar `python moodle_replica/app.py`
RAIZ_PROYECTO: Path = Path(__file__).resolve().parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

load_dotenv(dotenv_path=RAIZ_PROYECTO / ".env")

from src.core.calculador import evaluar_actividad
from src.core.validador import validar_extension_archivo
from src.datos.repositorio_moodle import (
    DIRECTORIO_ENTREGAS,
    asegurar_esquema_bd,
    crear_tarea_moodle,
    entregar_tarea,
    guardar_estimacion_tarea,
    inicializar_bd,
    obtener_todas_las_tareas,
)

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY", "ucsm-aula-virtual-fase2-secret-key"
)


def _escapar_texto_ics(texto: str) -> str:
    """Escapa caracteres especiales según el estándar RFC 5545 (iCalendar)."""
    if not texto:
        return ""
    return (
        texto.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _formatear_fecha_ics(fecha: datetime) -> str:
    """Convierte un objeto datetime al formato iCalendar (`YYYYMMDDTHHMMSS`)."""
    if fecha.tzinfo is not None:
        fecha_utc = fecha.astimezone(timezone.utc)
        return fecha_utc.strftime("%Y%m%dT%H%M%SZ")
    return fecha.strftime("%Y%m%dT%H%M%S")


@app.route("/", methods=["GET"])
def index():
    """Muestra el panel principal del Aula Virtual UCSM con todas las actividades."""
    tareas: list[dict] = []
    error_bd: str = ""
    try:
        asegurar_esquema_bd()
        tareas_raw = obtener_todas_las_tareas()
        for t in tareas_raw:
            item = dict(t)
            if (
                not item.get("estado_entrega")
                and item.get("tiempo_restante", 0.0) > 0.0
                and item.get("esfuerzo_estimado") is not None
                and item.get("importancia") is not None
            ):
                try:
                    item = evaluar_actividad(item)
                except ValueError:
                    pass
            tareas.append(item)
    except Exception:
        app.logger.exception("Error al consultar tareas en PostgreSQL.")
        error_bd = (
            "No se pudo conectar o consultar la base de datos PostgreSQL. "
            "Verifique que el servicio esté activo y utilice el botón 'Inicializar / Restaurar BD Semilla'."
        )

    total_tareas: int = len(tareas)
    total_entregadas: int = sum(1 for t in tareas if t.get("estado_entrega"))
    total_pendientes: int = total_tareas - total_entregadas

    return render_template(
        "index.html",
        tareas=tareas,
        total_tareas=total_tareas,
        total_pendientes=total_pendientes,
        total_entregadas=total_entregadas,
        error_bd=error_bd,
    )


@app.route("/inicializar_bd", methods=["POST"])
def ruta_inicializar_bd():
    """Permite inicializar o restaurar las tareas semilla en PostgreSQL desde la interfaz web."""
    exito: bool = inicializar_bd()
    if exito:
        flash(
            "Base de datos PostgreSQL inicializada con las 4 tareas semilla de la UCSM.",
            "exito",
        )
    else:
        flash(
            "Error al inicializar la base de datos PostgreSQL. Verifique el servicio y el archivo .env.",
            "error",
        )
    return redirect(url_for("index"))


@app.route("/crear_tarea", methods=["POST"])
def ruta_crear_tarea():
    """Recibe el formulario docente para registrar una nueva tarea académica en PostgreSQL."""
    curso: str = request.form.get("curso", "").strip()
    nombre_actividad: str = request.form.get("nombre_actividad", "").strip()
    descripcion: str = request.form.get("descripcion", "").strip()
    horas_plazo_str: str = request.form.get("horas_plazo", "").strip()

    try:
        horas_plazo: float = float(horas_plazo_str)
        nuevo_id: int = crear_tarea_moodle(
            curso=curso,
            nombre_actividad=nombre_actividad,
            descripcion=descripcion,
            horas_plazo=horas_plazo,
        )
        flash(
            f"Actividad '{nombre_actividad}' creada exitosamente en '{curso}' (ID #{nuevo_id}).",
            "exito",
        )
    except ValueError as err:
        flash(f"Datos inválidos al crear la actividad: {err}", "error")
    except Exception:
        app.logger.exception("Error inesperado al crear tarea en PostgreSQL.")
        flash(
            "Ocurrió un error interno al registrar la tarea en la base de datos.",
            "error",
        )

    return redirect(url_for("index"))


@app.route("/estimar/<int:id_tarea>", methods=["POST"])
def ruta_estimar_tarea(id_tarea: int):
    """Guarda en PostgreSQL la estimación de esfuerzo e importancia para una tarea."""
    esfuerzo_str: str = request.form.get("esfuerzo_estimado", "").strip()
    importancia: str = request.form.get("importancia", "").strip()

    try:
        esfuerzo_val: float = float(esfuerzo_str)
    except ValueError:
        flash("El esfuerzo estimado debe ser un valor numérico válido.", "error")
        return redirect(url_for("index"))

    exito, mensaje = guardar_estimacion_tarea(
        id_tarea=id_tarea,
        esfuerzo_estimado=esfuerzo_val,
        importancia=importancia,
    )
    if exito:
        flash(mensaje, "exito")
    else:
        flash(mensaje, "error")
    return redirect(url_for("index"))


@app.route("/entregar/<int:id_tarea>", methods=["POST"])
def ruta_entregar_tarea(id_tarea: int):
    """Procesa la subida de un archivo de entrega vía HTTP multipart para la tarea indicada."""
    comentario: str = request.form.get("comentario", "").strip()
    archivo_subido = request.files.get("archivo")

    if (
        archivo_subido is None
        or archivo_subido.filename is None
        or archivo_subido.filename.strip() == ""
    ):
        flash("Debe seleccionar un archivo para realizar la entrega.", "error")
        return redirect(url_for("index"))

    nombre_seguro: str = secure_filename(archivo_subido.filename)
    es_ext_valida, msg_ext = validar_extension_archivo(nombre_seguro)
    if not es_ext_valida:
        flash(msg_ext, "error")
        return redirect(url_for("index"))

    try:
        with tempfile.TemporaryDirectory() as dir_temp:
            ruta_temporal: Path = Path(dir_temp) / nombre_seguro
            archivo_subido.save(str(ruta_temporal))
            exito, mensaje = entregar_tarea(
                id_tarea=id_tarea,
                ruta_archivo_origen=str(ruta_temporal),
                comentario=comentario,
            )
            if exito:
                flash(mensaje, "exito")
            else:
                flash(mensaje, "error")
    except Exception:
        app.logger.exception("Error inesperado al procesar archivo subido.")
        flash("Ocurrió un error interno al procesar el archivo subido.", "error")

    return redirect(url_for("index"))


@app.route("/entregas/<path:nombre_archivo>", methods=["GET"])
def descargar_entrega(nombre_archivo: str):
    """Permite visualizar o descargar un archivo entregado almacenado en `data/entregas_subidas/`."""
    DIRECTORIO_ENTREGAS.mkdir(parents=True, exist_ok=True)
    return send_from_directory(str(DIRECTORIO_ENTREGAS), nombre_archivo)


@app.route("/calendario.ics", methods=["GET"])
def descargar_calendario_ics():
    """Genera y descarga en tiempo real un archivo `.ics` estándar (RFC 5545) con las tareas de PostgreSQL."""
    try:
        tareas: list[dict] = obtener_todas_las_tareas()
    except Exception:
        app.logger.exception("Error al generar calendario .ics.")
        flash("No se pudo generar el calendario .ics desde la base de datos.", "error")
        return redirect(url_for("index"))

    marca_dtstamp: str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lineas_ics: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Universidad Catolica de Santa Maria//Aula Virtual Moodle UCSM Fase II//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Carga Academica Moodle UCSM",
    ]

    for tarea in tareas:
        id_tarea: int = int(tarea["id_tarea"])
        curso: str = str(tarea.get("curso", ""))
        nombre_actividad: str = str(tarea.get("nombre_actividad", ""))
        descripcion: str = str(tarea.get("descripcion", ""))
        estado_entrega: bool = bool(tarea.get("estado_entrega", False))
        fecha_limite = tarea.get("fecha_limite")

        if isinstance(fecha_limite, datetime):
            dt_fin: datetime = fecha_limite
        else:
            dt_fin = datetime.now() + timedelta(
                hours=float(tarea.get("tiempo_restante", 1.0))
            )
        dt_inicio: datetime = dt_fin - timedelta(hours=1)

        estado_txt: str = "ENTREGADO" if estado_entrega else "PENDIENTE"
        resumen: str = _escapar_texto_ics(f"[{curso}] {nombre_actividad} ({estado_txt})")
        detalle: str = _escapar_texto_ics(
            f"Curso: {curso}\n"
            f"Estado: {estado_txt}\n"
            f"Descripción: {descripcion}"
        )

        # Según RFC 5545 (Sección 3.8.1.11), VEVENT admite TENTATIVE, CONFIRMED o CANCELLED
        lineas_ics.extend(
            [
                "BEGIN:VEVENT",
                f"UID:tarea-ucsm-{id_tarea}@moodle.ucsm.edu.pe",
                f"DTSTAMP:{marca_dtstamp}",
                f"DTSTART:{_formatear_fecha_ics(dt_inicio)}",
                f"DTEND:{_formatear_fecha_ics(dt_fin)}",
                f"SUMMARY:{resumen}",
                f"DESCRIPTION:{detalle}",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ]
        )

    lineas_ics.append("END:VCALENDAR")
    contenido_ics: str = "\r\n".join(lineas_ics) + "\r\n"

    return Response(
        contenido_ics,
        mimetype="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="calendario_moodle_ucsm.ics"'
        },
    )


if __name__ == "__main__":
    modo_debug: bool = os.getenv("FLASK_DEBUG", "false").strip().lower() == "true"
    app.run(host="127.0.0.1", port=5001, debug=modo_debug)
