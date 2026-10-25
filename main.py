"""Punto de entrada e interfaz de menú en consola (Sincronizar BD, Priorizar carga académica y Subir entrega).

Orquestador Imperativo (Imperative Shell) que conecta la capa de datos PostgreSQL
(`src/datos/repositorio_moodle.py`) con el Núcleo Algorítmico Determinista (`src/core/`).
"""

from pathlib import Path

from src.core.procesador import filtrar_actividades_pendientes, ordenar_actividades
from src.core.validador import (
    validar_extension_archivo,
    validar_pertenencia_importancia,
    validar_presencia,
    validar_rango_esfuerzo,
)
from src.datos.repositorio_moodle import (
    entregar_tarea,
    guardar_estimacion_tarea,
    inicializar_bd,
    obtener_tareas_pendientes,
)

SEPARADOR_LINEA: str = "=" * 92
SEPARADOR_SECCION: str = "-" * 92


def mostrar_encabezado() -> None:
    """Imprime el encabezado institucional del sistema en consola."""
    print(f"\n{SEPARADOR_LINEA}")
    print("  UNIVERSIDAD CATÓLICA DE SANTA MARÍA (UCSM) — ESCUELA DE INGENIERÍA DE SISTEMAS")
    print("  SISTEMA DE PRIORIZACIÓN DE CARGA ACADÉMICA SEMANAL + RÉPLICA MOODLE (FASE II)")
    print(SEPARADOR_LINEA)


def mostrar_menu() -> None:
    """Muestra las opciones disponibles en el menú principal."""
    print("\nMENÚ PRINCIPAL:")
    print("  [1] Inicializar / Reiniciar Base de Datos de la Réplica de Moodle (Datos Semilla UCSM)")
    print("  [2] Sincronizar tareas pendientes desde PostgreSQL y Priorizar Carga Semanal")
    print("  [3] Subir / Entregar tarea a la Réplica de Moodle")
    print("  [4] Ver estado del Agente Inteligente (src/agente/)")
    print("  [0] Salir")
    print(SEPARADOR_SECCION)


def solicitar_esfuerzo_valido(
    nombre_actividad: str,
    valor_actual: float | None = None,
) -> float:
    """Solicita interactivamente el esfuerzo estimado en horas hasta recibir un valor válido en (0.0, 80.0]."""
    sufijo_actual: str = (
        f" [Enter para mantener {valor_actual:.2f} h]"
        if valor_actual is not None
        else ""
    )
    while True:
        entrada: str = input(
            f"    -> Ingrese esfuerzo estimado en horas para '{nombre_actividad}' (0.0 < e <= 80.0){sufijo_actual}: "
        ).strip()
        if entrada == "" and valor_actual is not None:
            es_valido_act, _ = validar_rango_esfuerzo(valor_actual)
            if es_valido_act:
                return round(float(valor_actual), 2)

        try:
            valor_esfuerzo: float = float(entrada)
        except ValueError:
            print("       [!] Entrada inválida: Debe ingresar un número real (ej. 2.5 o 6).")
            continue

        es_valido, mensaje_error = validar_rango_esfuerzo(valor_esfuerzo)
        if es_valido:
            return round(valor_esfuerzo, 2)
        print(f"       [!] {mensaje_error}")


def solicitar_importancia_valida(
    nombre_actividad: str,
    valor_actual: str | None = None,
) -> str:
    """Solicita interactivamente la importancia académica hasta recibir un valor en {'ALTA', 'MEDIA', 'BAJA'}."""
    sufijo_actual: str = (
        f" [Enter para mantener '{valor_actual}']"
        if valor_actual is not None
        else ""
    )
    while True:
        entrada: str = input(
            f"    -> Ingrese importancia para '{nombre_actividad}' [ALTA / MEDIA / BAJA]{sufijo_actual}: "
        ).strip()
        if entrada == "" and valor_actual is not None:
            es_valido_act, _ = validar_pertenencia_importancia(valor_actual)
            if es_valido_act:
                return valor_actual.strip().upper()

        es_valido, mensaje_error = validar_pertenencia_importancia(entrada)
        if es_valido:
            return entrada.upper()
        print(f"       [!] {mensaje_error}")


def imprimir_tabla_priorizada(actividades_ordenadas: list[dict]) -> None:
    """Muestra en consola la tabla semanal ordenada con puntajes, niveles, explicaciones y alertas."""
    print(f"\n{SEPARADOR_LINEA}")
    print("  PLANIFICACIÓN SEMANAL PRIORIZADA (ORDENAMIENTO MULTICRITERIO CON DOBLE DESEMPATE)")
    print(SEPARADOR_LINEA)
    encabezado_tabla: str = (
        f"{'#':<3} | {'ID':<3} | {'NIVEL':<8} | {'PTS':<5} | "
        f"{'RESTA(h)':<8} | {'ESF(h)':<6} | {'IMP':<5} | {'CURSO / ACTIVIDAD'}"
    )
    print(encabezado_tabla)
    print(SEPARADOR_SECCION)

    alertas_detectadas: list[str] = []
    posicion: int = 1
    for act in actividades_ordenadas:
        id_str: str = str(act.get("id_tarea", "-"))
        nivel: str = str(act["nivel_cualitativo"])
        pts: str = f"{act['puntaje_total']}/9"
        tiempo_h: str = f"{act['tiempo_restante']:.2f}"
        esfuerzo_h: str = f"{act['esfuerzo_estimado']:.2f}"
        imp: str = str(act["importancia"])
        curso_y_nombre: str = f"[{act.get('curso', 'General')}] {act['nombre_actividad']}"

        indicador_deficit: str = " [¡DÉFICIT!]" if act.get("alerta_deficit") else ""
        print(
            f"{posicion:<3} | {id_str:<3} | {nivel:<8} | {pts:<5} | "
            f"{tiempo_h:<8} | {esfuerzo_h:<6} | {imp:<5} | {curso_y_nombre}{indicador_deficit}"
        )
        print(f"      Explicación: {act['explicacion']}")
        if act.get("alerta_deficit") and act.get("mensaje_alerta"):
            alertas_detectadas.append(
                f"  * Tarea #{id_str} ({act['nombre_actividad']}): {act['mensaje_alerta']}"
            )
        print(SEPARADOR_SECCION)
        posicion += 1

    if alertas_detectadas:
        print("\n[!] RESUMEN DE ALERTAS DE CONSISTENCIA TEMPORAL (Esfuerzo > Tiempo Restante):")
        for alerta in alertas_detectadas:
            print(alerta)
    else:
        print("\n[OK] Consistencia temporal verificada: Ninguna actividad presenta déficit horario.")
    print(SEPARADOR_LINEA)


def opcion_1_inicializar_bd() -> None:
    """Ejecuta la Opción 1: Inicializa o reinicia la base de datos PostgreSQL con los datos semilla UCSM."""
    confirmacion: str = input(
        "\n[Confirmación] ¿Está seguro de reiniciar la BD con los datos semilla? "
        "Se borrarán las entregas y tareas personalizadas [s/N]: "
    ).strip().lower()
    if confirmacion not in ("s", "si", "sí", "y", "yes"):
        print("  Operación de reinicio cancelada.")
        return

    print("\n[Opción 1] Inicializando base de datos PostgreSQL ('moodle_ucsm')...")
    exito: bool = inicializar_bd()
    if exito:
        print(
            "[OK] Base de datos reiniciada correctamente con las 4 tareas semilla de Ingeniería de Sistemas UCSM."
        )
    else:
        print(
            "[ERROR] No fue posible inicializar la base de datos. Verifique que PostgreSQL esté activo y revise .env."
        )


def opcion_2_sincronizar_y_priorizar() -> None:
    """Ejecuta la Opción 2: Sincroniza tareas pendientes desde PostgreSQL y prioriza la carga semanal."""
    print("\n[Opción 2] Sincronizando tareas pendientes desde PostgreSQL...")
    try:
        tareas_bd: list[dict] = obtener_tareas_pendientes()
    except Exception as exc:
        print(f"[ERROR BD] No se pudieron obtener las tareas pendientes: {exc}")
        print("Sugerencia: Ejecute primero la Opción 1 para inicializar la base de datos.")
        return

    tareas_pendientes: list[dict] = filtrar_actividades_pendientes(tareas_bd)
    if not tareas_pendientes:
        print("\n[INFO] No existen tareas pendientes con plazo vigente en este momento.")
        return

    print(
        f"[OK] Se encontraron {len(tareas_pendientes)} tareas pendientes vigentes en la Réplica de Moodle.\n"
        "A continuación, confirme o ingrese el esfuerzo estimado (en horas) y la importancia para cada actividad:"
    )

    actividades_para_evaluar: list[dict] = []
    indice: int = 1
    for tarea in tareas_pendientes:
        id_tarea: int = int(tarea["id_tarea"])
        esfuerzo_guardado: float | None = tarea.get("esfuerzo_estimado")
        importancia_guardada: str | None = tarea.get("importancia")

        print(f"\n  [{indice}/{len(tareas_pendientes)}] ID #{id_tarea} — {tarea['curso']}")
        print(f"    Actividad      : {tarea['nombre_actividad']}")
        print(f"    Descripción    : {tarea['descripcion']}")
        print(f"    Tiempo restante: {tarea['tiempo_restante']:.2f} horas")

        esfuerzo: float = solicitar_esfuerzo_valido(
            tarea["nombre_actividad"], esfuerzo_guardado
        )
        importancia: str = solicitar_importancia_valida(
            tarea["nombre_actividad"], importancia_guardada
        )

        # Persistencia en PostgreSQL para no perder la planificación entre ejecuciones o en la GUI
        if esfuerzo != esfuerzo_guardado or importancia != importancia_guardada:
            guardar_estimacion_tarea(id_tarea, esfuerzo, importancia)

        tarea_enriquecida: dict = dict(tarea)
        tarea_enriquecida["esfuerzo_estimado"] = esfuerzo
        tarea_enriquecida["importancia"] = importancia
        actividades_para_evaluar.append(tarea_enriquecida)
        indice += 1

    actividades_ordenadas: list[dict] = ordenar_actividades(actividades_para_evaluar)
    imprimir_tabla_priorizada(actividades_ordenadas)


def opcion_3_subir_entrega() -> None:
    """Ejecuta la Opción 3: Permite entregar un archivo local para una tarea pendiente y actualiza Moodle."""
    print("\n[Opción 3] Consultando tareas pendientes para entrega...")
    try:
        tareas_pendientes: list[dict] = obtener_tareas_pendientes()
    except Exception as exc:
        print(f"[ERROR BD] No se pudo consultar PostgreSQL: {exc}")
        return

    if not tareas_pendientes:
        print("\n[INFO] No hay tareas pendientes de entrega en el Aula Virtual.")
        return

    print("\nTAREAS PENDIENTES EN MOODLE UCSM:")
    print(SEPARADOR_SECCION)
    ids_validos: list[int] = []
    for tarea in tareas_pendientes:
        id_actual: int = int(tarea["id_tarea"])
        ids_validos.append(id_actual)
        print(
            f"  ID #{id_actual:<3} | {tarea['curso']:<26} | "
            f"{tarea['nombre_actividad']:<38} | Restan: {tarea['tiempo_restante']:.2f} h"
        )
    print(SEPARADOR_SECCION)

    # Selección validada de id_tarea
    id_seleccionado: int = -1
    while True:
        entrada_id: str = input("  -> Ingrese el ID de la tarea a entregar (o '0' para cancelar): ").strip()
        if entrada_id == "0":
            print("  Operación de entrega cancelada.")
            return
        try:
            candidato_id: int = int(entrada_id)
        except ValueError:
            print("     [!] Debe ingresar un número entero correspondiente al ID de la tarea.")
            continue

        existe_id: bool = False
        for id_val in ids_validos:
            if candidato_id == id_val:
                existe_id = True
                break
        if existe_id:
            id_seleccionado = candidato_id
            break
        print(f"     [!] El ID #{candidato_id} no corresponde a ninguna tarea pendiente listada.")

    # Solicitud validada de la ruta del archivo local (presencia, extensión y existencia física)
    while True:
        ruta_archivo: str = input(
            "  -> Ingrese la ruta local del archivo a entregar (.pdf, .py, .zip, .docx, .md): "
        ).strip()
        ok_pres, msg_pres = validar_presencia(ruta_archivo, "ruta_archivo")
        if not ok_pres:
            print(f"     [!] {msg_pres}")
            continue
        ok_ext, msg_ext = validar_extension_archivo(ruta_archivo)
        if not ok_ext:
            print(f"     [!] {msg_ext}")
            continue
        if not Path(ruta_archivo).expanduser().is_file():
            print(f"     [!] No se encontró ningún archivo físico en la ruta '{ruta_archivo}'. Intente nuevamente.")
            continue
        break

    comentario: str = input("  -> Ingrese un comentario de entrega (opcional): ").strip()
    exito, mensaje = entregar_tarea(
        id_tarea=id_seleccionado,
        ruta_archivo_origen=ruta_archivo,
        comentario=comentario,
    )
    if exito:
        print(f"\n  [OK] {mensaje}")
        print(
            "  [Moodle Web] La actividad ya figura con estado '✓ ENTREGADO' en la Réplica Web (http://127.0.0.1:5000)."
        )
    else:
        print(f"\n  [ERROR] {mensaje}")


def opcion_4_estado_agente() -> None:
    """Ejecuta la Opción 4: Muestra el aviso arquitectónico sobre el módulo de Agente Inteligente."""
    print(f"\n{SEPARADOR_SECCION}")
    print("  ESTADO DEL MÓDULO DE AGENTE INTELIGENTE (src/agente/)")
    print(SEPARADOR_SECCION)
    print("  [AVISO ARQUITECTÓNICO — FASE II]")
    print("  El paquete 'src/agente/' se mantiene estrictamente vacío en la Fase II para garantizar")
    print("  la validación determinista del Núcleo Algorítmico ('src/core/').")
    print("\n  [PROYECCIÓN FASE III]")
    print("  En la Fase III se integrará el Agente Inteligente encargado de:")
    print("    1. Leer automáticamente la descripción de las tareas desde PostgreSQL/Moodle.")
    print("    2. Inferir el esfuerzo estimado (horas) y la importancia ('ALTA', 'MEDIA', 'BAJA') mediante IA.")
    print("    3. Generar recomendaciones personalizadas de estudio y analítica semanal.")
    print(SEPARADOR_SECCION)


def ejecutar_consola() -> None:
    """Bucle principal del menú interactivo en consola."""
    mostrar_encabezado()
    while True:
        mostrar_menu()
        try:
            opcion: str = input("Seleccione una opción [0-4]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo del sistema. ¡Hasta luego!")
            break

        if opcion == "1":
            opcion_1_inicializar_bd()
        elif opcion == "2":
            opcion_2_sincronizar_y_priorizar()
        elif opcion == "3":
            opcion_3_subir_entrega()
        elif opcion == "4":
            opcion_4_estado_agente()
        elif opcion == "0":
            print("\nCerrando el Sistema de Priorización Académica UCSM. ¡Éxitos en tu semana!")
            break
        else:
            print("\n[!] Opción no válida. Por favor, elija un número entre 0 y 4.")


if __name__ == "__main__":
    ejecutar_consola()
