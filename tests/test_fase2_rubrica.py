"""Suite de pruebas automatizadas con los 7 casos oficiales de la rúbrica de Fase II (3 Normales, 2 Límite, 2 Inválidos).

Evalúa directamente las funciones puras de `src/core/` utilizando diccionarios en memoria,
sin requerir conexión activa a PostgreSQL.
"""

import sys
from pathlib import Path

import pytest

# Garantiza que la raíz del proyecto esté en sys.path al invocar `pytest` directamente
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from src.core.calculador import (
    calcular_puntos_esfuerzo,
    calcular_puntos_importancia,
    calcular_puntos_urgencia,
    evaluar_actividad,
    obtener_nivel_cualitativo,
)
from src.core.procesador import (
    clave_ordenamiento,
    filtrar_actividades_pendientes,
    ordenar_actividades,
)
from src.core.validador import (
    validar_extension_archivo,
    validar_pertenencia_importancia,
    validar_presencia,
    validar_rango_esfuerzo,
    validar_rango_tiempo,
    verificar_consistencia_temporal,
)


# ============================================================================
# CASOS NORMALES (3 Pruebas)
# ============================================================================


def test_normal_1_evaluacion_critica_y_alerta_deficit() -> None:
    """Caso Normal 1: Evaluación de actividad crítica (9 pts) con y sin déficit temporal."""
    # Escenario A: Avance Proyecto Final con 12h restantes y 8h de esfuerzo (sin déficit: 8 <= 12)
    avance_sin_deficit: dict = {
        "curso": "Pensamiento Computacional",
        "nombre_actividad": "Avance Proyecto Final Fase II",
        "tiempo_restante": 12.0,
        "esfuerzo_estimado": 8.0,
        "importancia": "ALTA",
    }
    resultado_a: dict = evaluar_actividad(avance_sin_deficit)
    assert resultado_a["p_urgencia"] == 3
    assert resultado_a["p_esfuerzo"] == 3
    assert resultado_a["p_importancia"] == 3
    assert resultado_a["puntaje_total"] == 9
    assert resultado_a["nivel_cualitativo"] == "CRÍTICO"
    assert resultado_a["alerta_deficit"] is False
    assert resultado_a["mensaje_alerta"] == ""

    # Escenario B: Mismo esfuerzo de 8h pero con solo 4h restantes (con déficit: 8 > 4)
    avance_con_deficit: dict = {
        "curso": "Pensamiento Computacional",
        "nombre_actividad": "Avance Proyecto Final Fase II (Urgente)",
        "tiempo_restante": 4.0,
        "esfuerzo_estimado": 8.0,
        "importancia": "ALTA",
    }
    resultado_b: dict = evaluar_actividad(avance_con_deficit)
    assert resultado_b["puntaje_total"] == 9
    assert resultado_b["nivel_cualitativo"] == "CRÍTICO"
    assert resultado_b["alerta_deficit"] is True
    assert "DÉFICIT TEMPORAL" in resultado_b["mensaje_alerta"]
    assert "DÉFICIT TEMPORAL" in resultado_b["explicacion"]


def test_normal_2_trazado_ordenamiento_4_tareas_fase1() -> None:
    """Caso Normal 2: Trazado exacto de las 4 tareas de Fase I y su ordenamiento final.

    Verifica que el orden resultante sea:
    1. Avance Proyecto Final Fase II [9 pts, CRÍTICO]
    2. Práctica de programación en lógica [7 pts, ALTO]
    3. Cuestionario corto Semana 9 [5 pts, MEDIO, t=4.0h] (desempata por menor tiempo restante)
    4. Lectura de capítulo de sistemas de información [5 pts, MEDIO, t=60.0h]
    """
    tareas_fase1: list[dict] = [
        {
            "id_tarea": 1,
            "curso": "Pensamiento Computacional",
            "nombre_actividad": "Cuestionario corto Semana 9",
            "tiempo_restante": 4.0,
            "esfuerzo_estimado": 1.0,
            "importancia": "BAJA",
        },
        {
            "id_tarea": 2,
            "curso": "Pensamiento Computacional",
            "nombre_actividad": "Avance Proyecto Final Fase II",
            "tiempo_restante": 12.0,
            "esfuerzo_estimado": 8.0,
            "importancia": "ALTA",
        },
        {
            "id_tarea": 3,
            "curso": "Estructuras Discretas",
            "nombre_actividad": "Práctica de programación en lógica",
            "tiempo_restante": 36.0,
            "esfuerzo_estimado": 5.0,
            "importancia": "MEDIA",
        },
        {
            "id_tarea": 4,
            "curso": "Ingeniería de Sistemas",
            "nombre_actividad": "Lectura de capítulo de sistemas de información",
            "tiempo_restante": 60.0,
            "esfuerzo_estimado": 2.5,
            "importancia": "BAJA",
        },
    ]

    ordenadas: list[dict] = ordenar_actividades(tareas_fase1)

    assert len(ordenadas) == 4
    assert [t["nombre_actividad"] for t in ordenadas] == [
        "Avance Proyecto Final Fase II",
        "Práctica de programación en lógica",
        "Cuestionario corto Semana 9",
        "Lectura de capítulo de sistemas de información",
    ]
    assert [t["puntaje_total"] for t in ordenadas] == [9, 7, 5, 5]
    assert [t["nivel_cualitativo"] for t in ordenadas] == [
        "CRÍTICO",
        "ALTO",
        "MEDIO",
        "MEDIO",
    ]
    assert ordenadas[2]["tiempo_restante"] == 4.0
    assert ordenadas[3]["tiempo_restante"] == 60.0


def test_normal_3_filtrado_pendientes_y_extensiones_validas() -> None:
    """Caso Normal 3: Filtrado de actividades pendientes vigentes y validación de extensiones."""
    lista_mixta: list[dict] = [
        {
            "nombre_actividad": "Tarea Pendiente Vigente",
            "tiempo_restante": 18.0,
            "estado_entrega": False,
        },
        {
            "nombre_actividad": "Tarea Ya Entregada",
            "tiempo_restante": 20.0,
            "estado_entrega": True,
        },
        {
            "nombre_actividad": "Tarea Vencida",
            "tiempo_restante": -2.0,
            "estado_entrega": False,
        },
    ]

    pendientes: list[dict] = filtrar_actividades_pendientes(lista_mixta)
    assert len(pendientes) == 1
    assert pendientes[0]["nombre_actividad"] == "Tarea Pendiente Vigente"

    for archivo in ("informe.pdf", "solucion.py", "proyecto.zip", "avance.docx", "README.md"):
        es_valido, msg = validar_extension_archivo(archivo)
        assert es_valido is True
        assert msg == ""


# ============================================================================
# CASOS LÍMITE / FRONTERA (2 Pruebas)
# ============================================================================


def test_limite_1_frontera_exacta_tiempo_24_esfuerzo_2() -> None:
    """Caso Límite 1: Frontera exacta t=24.0 y e=2.0 con importancia 'MEDIA' -> 6 pts ('ALTO')."""
    tarea_frontera: dict = {
        "curso": "Pensamiento Computacional",
        "nombre_actividad": "Laboratorio en Frontera Exacta",
        "tiempo_restante": 24.0,
        "esfuerzo_estimado": 2.0,
        "importancia": "MEDIA",
    }

    evaluada: dict = evaluar_actividad(tarea_frontera)

    assert evaluada["p_urgencia"] == 2
    assert evaluada["p_esfuerzo"] == 2
    assert evaluada["p_importancia"] == 2
    assert evaluada["puntaje_total"] == 6
    assert evaluada["nivel_cualitativo"] == "ALTO"
    assert evaluada["alerta_deficit"] is False

    # Verificación adicional de fronteras superiores de los tramos medios (t=72.0 y e=4.0)
    assert calcular_puntos_urgencia(72.0) == 2
    assert calcular_puntos_esfuerzo(4.0) == 2
    assert obtener_nivel_cualitativo(3) == "BAJO"


def test_limite_2_doble_desempate_mismo_puntaje_y_tiempo() -> None:
    """Caso Límite 2: Doble desempate con puntaje_total=6 y tiempo_restante=48.0.

    Ambas tareas empatan en puntaje_total (6) y tiempo_restante (48.0 h -> p_urgencia=2):
    - Tarea Baja: e=5.0 (p_esfuerzo=3) + imp='BAJA' (p_importancia=1) -> total = 6
    - Tarea Alta: e=1.0 (p_esfuerzo=1) + imp='ALTA' (p_importancia=3) -> total = 6
    Debe quedar primero la de importancia 'ALTA'.
    """
    tarea_importancia_baja: dict = {
        "curso": "Estructuras Discretas",
        "nombre_actividad": "Tarea Empatada Importancia Baja",
        "tiempo_restante": 48.0,
        "esfuerzo_estimado": 5.0,
        "importancia": "BAJA",
    }
    tarea_importancia_alta: dict = {
        "curso": "Pensamiento Computacional",
        "nombre_actividad": "Tarea Empatada Importancia Alta",
        "tiempo_restante": 48.0,
        "esfuerzo_estimado": 1.0,
        "importancia": "ALTA",
    }

    ordenadas: list[dict] = ordenar_actividades(
        [tarea_importancia_baja, tarea_importancia_alta]
    )

    assert ordenadas[0]["puntaje_total"] == 6
    assert ordenadas[1]["puntaje_total"] == 6
    assert ordenadas[0]["tiempo_restante"] == 48.0
    assert ordenadas[1]["tiempo_restante"] == 48.0
    assert ordenadas[0]["importancia"] == "ALTA"
    assert ordenadas[0]["nombre_actividad"] == "Tarea Empatada Importancia Alta"
    assert ordenadas[1]["importancia"] == "BAJA"
    assert ordenadas[1]["nombre_actividad"] == "Tarea Empatada Importancia Baja"
    assert clave_ordenamiento(ordenadas[0]) < clave_ordenamiento(ordenadas[1])


# ============================================================================
# CASOS INVÁLIDOS (2 Pruebas)
# ============================================================================


def test_invalido_1_esfuerzo_negativo_o_fuera_de_rango() -> None:
    """Caso Inválido 1: Rechazo de esfuerzo negativo (-2.5), fuera de rango (95.0), NaN o Inf."""
    valido_neg, msg_neg = validar_rango_esfuerzo(-2.5)
    assert valido_neg is False
    assert msg_neg != ""

    valido_exc, msg_exc = validar_rango_esfuerzo(95.0)
    assert valido_exc is False
    assert msg_exc != ""

    # Blindaje IEEE 754 (NaN e Inf)
    assert validar_rango_esfuerzo(float("nan"))[0] is False
    assert validar_rango_esfuerzo(float("inf"))[0] is False
    assert validar_rango_tiempo(float("nan"))[0] is False
    assert validar_rango_tiempo(float("inf"))[0] is False

    with pytest.raises(ValueError, match="Error de rango"):
        evaluar_actividad(
            {
                "nombre_actividad": "Tarea Esfuerzo Negativo",
                "tiempo_restante": 20.0,
                "esfuerzo_estimado": -2.5,
                "importancia": "MEDIA",
            }
        )

    with pytest.raises(ValueError, match="Error de rango"):
        evaluar_actividad(
            {
                "nombre_actividad": "Tarea Esfuerzo Excesivo",
                "tiempo_restante": 20.0,
                "esfuerzo_estimado": 95.0,
                "importancia": "ALTA",
            }
        )


def test_invalido_2_importancia_fuera_dominio_y_tarea_vencida() -> None:
    """Caso Inválido 2: Rechazo de importancia fuera de dominio ('MUY URGENTE'), tarea vencida (t=-3.0), None y rutas ocultas."""
    valido_imp, msg_imp = validar_pertenencia_importancia("MUY URGENTE")
    assert valido_imp is False
    assert msg_imp != ""

    valido_tiempo, msg_tiempo = validar_rango_tiempo(-3.0)
    assert valido_tiempo is False
    assert msg_tiempo != ""

    with pytest.raises(ValueError, match="Error de pertenencia"):
        evaluar_actividad(
            {
                "nombre_actividad": "Tarea Importancia Inválida",
                "tiempo_restante": 15.0,
                "esfuerzo_estimado": 3.0,
                "importancia": "MUY URGENTE",
            }
        )

    with pytest.raises(ValueError, match="Error de rango"):
        evaluar_actividad(
            {
                "nombre_actividad": "Tarea Plazo Vencido",
                "tiempo_restante": -3.0,
                "esfuerzo_estimado": 2.0,
                "importancia": "BAJA",
            }
        )

    # Blindaje ante None en nombre_actividad / curso y rutas ocultas sin nombre base
    with pytest.raises(ValueError, match="Error de presencia"):
        evaluar_actividad(
            {
                "nombre_actividad": None,
                "tiempo_restante": 10.0,
                "esfuerzo_estimado": 2.0,
                "importancia": "ALTA",
            }
        )

    ok_presencia, _ = validar_presencia("   ", "nombre_actividad")
    assert ok_presencia is False
    assert validar_extension_archivo("malware.exe")[0] is False
    assert validar_extension_archivo("entregas/.pdf")[0] is False
