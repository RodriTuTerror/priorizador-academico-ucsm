"""Filtrado de tareas válidas y ordenamiento multicriterio con doble desempate (-puntaje, t, -imp).

Módulo perteneciente al Núcleo Algorítmico Determinista (Fase II).
Restricción arquitectónica: 100% Python estándar, cero librerías externas.
"""

from src.core.calculador import evaluar_actividad


def filtrar_actividades_pendientes(lista_actividades: list[dict]) -> list[dict]:
    """Filtra la lista descartando tareas ya entregadas o cuyo plazo haya vencido.

    Criterios de descarte:
    - estado_entrega == True
    - tiempo_restante <= 0.0

    Args:
        lista_actividades: Lista de diccionarios representando tareas académicas.

    Returns:
        Nueva lista que contiene únicamente las actividades pendientes y con plazo vigente.
    """
    actividades_filtradas: list[dict] = []
    for actividad in lista_actividades:
        estado_entrega: bool = bool(actividad.get("estado_entrega", False))
        tiempo_raw = actividad.get("tiempo_restante", 0.0)
        if isinstance(tiempo_raw, bool) or not isinstance(tiempo_raw, (int, float)):
            continue
        tiempo_restante: float = float(tiempo_raw)

        if not estado_entrega and tiempo_restante > 0.0:
            actividades_filtradas.append(actividad)

    return actividades_filtradas


def clave_ordenamiento(actividad: dict) -> tuple[int, float, int]:
    """Construye la tupla de ordenamiento con doble criterio de desempate.

    Orden de prioridad:
    1. Mayor puntaje_total primero -> -actividad["puntaje_total"]
    2. Primer desempate: menor tiempo_restante primero -> actividad["tiempo_restante"]
    3. Segundo desempate: mayor p_importancia primero -> -actividad["p_importancia"]

    Args:
        actividad: Diccionario de actividad previamente evaluada.

    Returns:
        Tupla (-puntaje_total, tiempo_restante, -p_importancia).
    """
    return (
        -int(actividad["puntaje_total"]),
        float(actividad["tiempo_restante"]),
        -int(actividad["p_importancia"]),
    )


def ordenar_actividades(lista_actividades: list[dict]) -> list[dict]:
    """Evalúa cada actividad de la lista y las ordena según la prioridad multicriterio.

    Args:
        lista_actividades: Lista de diccionarios de actividades válidas por priorizar.

    Returns:
        Nueva lista de actividades enriquecidas y ordenadas por prioridad.
    """
    actividades_evaluadas: list[dict] = []
    for actividad in lista_actividades:
        actividad_evaluada: dict = evaluar_actividad(actividad)
        actividades_evaluadas.append(actividad_evaluada)

    actividades_evaluadas.sort(key=clave_ordenamiento)
    return actividades_evaluadas
