"""Cálculo determinista de puntajes de prioridad en el rango [3, 9] y asignación de etiquetas ('CRÍTICO', 'ALTO', 'MEDIO', 'BAJO').

Módulo perteneciente al Núcleo Algorítmico Determinista (Fase II).
Restricción arquitectónica: 100% Python estándar, cero librerías externas.
"""

from src.core.validador import (
    validar_pertenencia_importancia,
    validar_presencia,
    validar_rango_esfuerzo,
    validar_rango_tiempo,
    verificar_consistencia_temporal,
)


def calcular_puntos_urgencia(tiempo_restante: float) -> int:
    """Calcula el puntaje de urgencia según el tiempo restante t (en horas).

    Reglas de negocio:
    - 0 < t < 24.0   -> 3 puntos
    - 24.0 <= t <= 72.0 -> 2 puntos
    - t > 72.0       -> 1 punto

    Args:
        tiempo_restante: Horas disponibles hasta la fecha límite (debe ser > 0.0).

    Returns:
        Puntaje entero de urgencia en {1, 2, 3}.

    Raises:
        ValueError: Si tiempo_restante no cumple el rango válido (> 0.0).
    """
    es_valido, mensaje = validar_rango_tiempo(tiempo_restante)
    if not es_valido:
        raise ValueError(mensaje)

    t: float = float(tiempo_restante)
    if t < 24.0:
        return 3
    if t <= 72.0:
        return 2
    return 1


def calcular_puntos_esfuerzo(esfuerzo_estimado: float) -> int:
    """Calcula el puntaje de esfuerzo según el esfuerzo estimado e (en horas).

    Reglas de negocio:
    - e > 4.0        -> 3 puntos
    - 2.0 <= e <= 4.0 -> 2 puntos
    - 0 < e < 2.0    -> 1 punto

    Args:
        esfuerzo_estimado: Horas requeridas para completar la tarea en (0.0, 80.0].

    Returns:
        Puntaje entero de esfuerzo en {1, 2, 3}.

    Raises:
        ValueError: Si esfuerzo_estimado está fuera del rango (0.0, 80.0].
    """
    es_valido, mensaje = validar_rango_esfuerzo(esfuerzo_estimado)
    if not es_valido:
        raise ValueError(mensaje)

    e: float = float(esfuerzo_estimado)
    if e > 4.0:
        return 3
    if e >= 2.0:
        return 2
    return 1


def calcular_puntos_importancia(importancia: str) -> int:
    """Calcula el puntaje de importancia académica según su nivel categórico.

    Reglas de negocio:
    - "ALTA"  -> 3 puntos
    - "MEDIA" -> 2 puntos
    - "BAJA"  -> 1 punto

    Args:
        importancia: Nivel de importancia ("ALTA", "MEDIA" o "BAJA").

    Returns:
        Puntaje entero de importancia en {1, 2, 3}.

    Raises:
        ValueError: Si la importancia no pertenece al dominio válido.
    """
    es_valido, mensaje = validar_pertenencia_importancia(importancia)
    if not es_valido:
        raise ValueError(mensaje)

    nivel: str = importancia.strip().upper()
    if nivel == "ALTA":
        return 3
    if nivel == "MEDIA":
        return 2
    return 1


def obtener_nivel_cualitativo(puntaje_total: int) -> str:
    """Traduce el puntaje total numérico [3, 9] a su etiqueta de nivel cualitativo.

    Reglas de negocio:
    - [8, 9] -> "CRÍTICO"
    - [6, 7] -> "ALTO"
    - [4, 5] -> "MEDIO"
    - 3      -> "BAJO"

    Args:
        puntaje_total: Suma entera de urgencia, esfuerzo e importancia.

    Returns:
        Etiqueta cualitativa ("CRÍTICO", "ALTO", "MEDIO" o "BAJO").

    Raises:
        ValueError: Si el puntaje total se encuentra fuera del rango entero [3, 9].
    """
    if isinstance(puntaje_total, bool) or not isinstance(puntaje_total, int):
        raise ValueError("El puntaje total debe ser un número entero.")
    if puntaje_total < 3 or puntaje_total > 9:
        raise ValueError(f"El puntaje total ({puntaje_total}) debe estar en el rango [3, 9].")

    if puntaje_total >= 8:
        return "CRÍTICO"
    if puntaje_total >= 6:
        return "ALTO"
    if puntaje_total >= 4:
        return "MEDIO"
    return "BAJO"


def generar_explicacion(actividad: dict) -> str:
    """Genera un resumen explicativo de los puntajes de la actividad y su alerta de déficit si existe.

    Args:
        actividad: Diccionario con los datos y puntajes calculados de la actividad.

    Returns:
        Cadena de texto explicativa detallando urgencia, esfuerzo, importancia y alertas.
    """
    tiempo_restante: float = float(actividad.get("tiempo_restante", 0.0))
    esfuerzo_estimado: float = float(
        actividad.get("esfuerzo_estimado", actividad.get("esfuerzo", 0.0))
    )
    importancia: str = str(actividad.get("importancia", "")).strip().upper()

    p_urgencia: int = int(
        actividad.get("p_urgencia", calcular_puntos_urgencia(tiempo_restante))
    )
    p_esfuerzo: int = int(
        actividad.get("p_esfuerzo", calcular_puntos_esfuerzo(esfuerzo_estimado))
    )
    p_importancia: int = int(
        actividad.get("p_importancia", calcular_puntos_importancia(importancia))
    )
    puntaje_total: int = int(
        actividad.get("puntaje_total", p_urgencia + p_esfuerzo + p_importancia)
    )
    nivel: str = str(
        actividad.get(
            "nivel_cualitativo",
            actividad.get("nivel_prioridad", obtener_nivel_cualitativo(puntaje_total)),
        )
    )

    if "alerta_deficit" in actividad and "mensaje_alerta" in actividad:
        hay_deficit: bool = bool(actividad["alerta_deficit"])
        mensaje_alerta: str = str(actividad["mensaje_alerta"])
    else:
        hay_deficit, mensaje_alerta = verificar_consistencia_temporal(
            esfuerzo_estimado, tiempo_restante
        )

    resumen: str = (
        f"Nivel {nivel} ({puntaje_total}/9 pts) -> "
        f"Urgencia: {p_urgencia}/3 (restan {tiempo_restante:.1f} h), "
        f"Esfuerzo: {p_esfuerzo}/3 (requiere {esfuerzo_estimado:.1f} h), "
        f"Importancia: {p_importancia}/3 ({importancia})."
    )
    if hay_deficit and mensaje_alerta:
        resumen = f"{resumen} {mensaje_alerta}"
    return resumen


def evaluar_actividad(actividad: dict) -> dict:
    """Valida una actividad académica y calcula sus puntajes, nivel cualitativo, alerta y explicación.

    Args:
        actividad: Diccionario con los atributos de entrada de la actividad
            (nombre_actividad, curso opcional, tiempo_restante, esfuerzo_estimado, importancia).

    Returns:
        Nuevo diccionario enriquecido con los campos calculados:
        p_urgencia, p_esfuerzo, p_importancia, puntaje_total, nivel_cualitativo,
        nivel_prioridad, alerta_deficit, mensaje_alerta y explicacion.

    Raises:
        ValueError: Si alguno de los campos obligatorios falla las validaciones de presencia,
            rango o pertenencia.
    """
    if not isinstance(actividad, dict):
        raise ValueError("La actividad debe ser proporcionada como un diccionario.")

    resultado: dict = {}
    for clave, valor in actividad.items():
        resultado[clave] = valor

    # 1. Validación de presencia en nombre de actividad y curso SIN convertir None a "None"
    nombre_raw = (
        resultado.get("nombre_actividad")
        if "nombre_actividad" in resultado
        else resultado.get("nombre")
    )
    ok_nombre, msg_nombre = validar_presencia(nombre_raw, "nombre_actividad")
    if not ok_nombre:
        raise ValueError(msg_nombre)
    nombre_actividad: str = str(nombre_raw).strip()

    if "curso" in resultado:
        curso_raw = resultado["curso"]
        ok_curso, msg_curso = validar_presencia(curso_raw, "curso")
        if not ok_curso:
            raise ValueError(msg_curso)
        resultado["curso"] = str(curso_raw).strip()

    # 2. Extracción y validación de tiempo restante
    if "tiempo_restante" not in resultado or resultado["tiempo_restante"] is None:
        raise ValueError("Error de presencia: El campo 'tiempo_restante' es obligatorio.")
    tiempo_raw = resultado["tiempo_restante"]
    ok_tiempo, msg_tiempo = validar_rango_tiempo(tiempo_raw)
    if not ok_tiempo:
        raise ValueError(msg_tiempo)
    tiempo_restante: float = float(tiempo_raw)

    # 3. Extracción y validación de esfuerzo estimado
    esfuerzo_raw = (
        resultado.get("esfuerzo_estimado")
        if "esfuerzo_estimado" in resultado
        else resultado.get("esfuerzo")
    )
    if esfuerzo_raw is None:
        raise ValueError("Error de presencia: El campo 'esfuerzo_estimado' es obligatorio.")
    ok_esfuerzo, msg_esfuerzo = validar_rango_esfuerzo(esfuerzo_raw)
    if not ok_esfuerzo:
        raise ValueError(msg_esfuerzo)
    esfuerzo_estimado: float = float(esfuerzo_raw)

    # 4. Extracción y validación de importancia
    importancia_raw = resultado.get("importancia")
    ok_imp, msg_imp = validar_pertenencia_importancia(importancia_raw)
    if not ok_imp:
        raise ValueError(msg_imp)
    importancia: str = str(importancia_raw).strip().upper()

    # 5. Cálculo de puntajes parciales y puntaje total
    p_urgencia: int = calcular_puntos_urgencia(tiempo_restante)
    p_esfuerzo: int = calcular_puntos_esfuerzo(esfuerzo_estimado)
    p_importancia: int = calcular_puntos_importancia(importancia)
    puntaje_total: int = p_urgencia + p_esfuerzo + p_importancia

    # 6. Nivel cualitativo y consistencia temporal
    nivel_cualitativo: str = obtener_nivel_cualitativo(puntaje_total)
    alerta_deficit, mensaje_alerta = verificar_consistencia_temporal(
        esfuerzo_estimado, tiempo_restante
    )

    # 7. Enriquecimiento del diccionario de salida
    resultado["nombre_actividad"] = nombre_actividad
    resultado["tiempo_restante"] = tiempo_restante
    resultado["esfuerzo_estimado"] = esfuerzo_estimado
    resultado["importancia"] = importancia
    resultado["p_urgencia"] = p_urgencia
    resultado["p_esfuerzo"] = p_esfuerzo
    resultado["p_importancia"] = p_importancia
    resultado["puntaje_total"] = puntaje_total
    resultado["nivel_cualitativo"] = nivel_cualitativo
    resultado["nivel_prioridad"] = nivel_cualitativo
    resultado["alerta_deficit"] = alerta_deficit
    resultado["mensaje_alerta"] = mensaje_alerta
    resultado["explicacion"] = generar_explicacion(resultado)

    return resultado
