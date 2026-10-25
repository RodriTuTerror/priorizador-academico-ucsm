"""Validación de actividades académicas: Presencia, Rango (0 < e <= 80), Pertenencia y Consistencia (e <= t).

Módulo perteneciente al Núcleo Algorítmico Determinista (Fase II).
Restricción arquitectónica: 100% Python estándar, cero librerías externas.
"""

IMPORTANCIAS_VALIDAS: tuple[str, ...] = ("ALTA", "MEDIA", "BAJA")
EXTENSIONES_PERMITIDAS: tuple[str, ...] = (".pdf", ".py", ".zip", ".docx", ".md")
ESFUERZO_MINIMO_EXCLUSIVO: float = 0.0
ESFUERZO_MAXIMO_INCLUSIVO: float = 80.0
TIEMPO_MINIMO_EXCLUSIVO: float = 0.0


def validar_presencia(valor: str, nombre_campo: str) -> tuple[bool, str]:
    """Verifica que un campo de texto obligatorio no sea nulo ni esté vacío.

    Args:
        valor: Cadena de texto a evaluar.
        nombre_campo: Nombre descriptivo del campo para el mensaje de error.

    Returns:
        Tupla (es_valido, mensaje_error). Si es válido, mensaje_error es "".
    """
    if valor is None or not isinstance(valor, str):
        return (
            False,
            f"Error de presencia: El campo '{nombre_campo}' debe ser una cadena de texto válida.",
        )
    if valor.strip() == "":
        return (
            False,
            f"Error de presencia: El campo '{nombre_campo}' no puede estar vacío.",
        )
    return (True, "")


def validar_rango_tiempo(tiempo_restante: float) -> tuple[bool, str]:
    """Verifica que el tiempo restante sea un número finito estrictamente mayor a 0.0 horas.

    Args:
        tiempo_restante: Horas disponibles hasta el vencimiento de la actividad.

    Returns:
        Tupla (es_valido, mensaje_error). Si es válido, mensaje_error es "".
    """
    if isinstance(tiempo_restante, bool) or not isinstance(tiempo_restante, (int, float)):
        return (
            False,
            "Error de rango: El tiempo restante debe ser un valor numérico.",
        )
    valor_tiempo: float = float(tiempo_restante)
    # En IEEE 754, cualquier comparación `<` o `>` con NaN evalúa a False; además se rechaza +inf
    if not (valor_tiempo > TIEMPO_MINIMO_EXCLUSIVO and valor_tiempo != float("inf")):
        return (
            False,
            f"Error de rango: El tiempo restante ({valor_tiempo} h) debe ser un número finito mayor a 0.0 horas.",
        )
    return (True, "")


def validar_rango_esfuerzo(esfuerzo: float) -> tuple[bool, str]:
    """Verifica que el esfuerzo estimado sea un número finito dentro del rango (0.0, 80.0] horas.

    Args:
        esfuerzo: Horas estimadas de dedicación para completar la actividad.

    Returns:
        Tupla (es_valido, mensaje_error). Si es válido, mensaje_error es "".
    """
    if isinstance(esfuerzo, bool) or not isinstance(esfuerzo, (int, float)):
        return (
            False,
            "Error de rango: El esfuerzo estimado debe ser un valor numérico.",
        )
    valor_esfuerzo: float = float(esfuerzo)
    # Negar el intervalo encadenado rechaza automáticamente NaN, -inf, +inf, <= 0.0 y > 80.0
    if not (ESFUERZO_MINIMO_EXCLUSIVO < valor_esfuerzo <= ESFUERZO_MAXIMO_INCLUSIVO):
        return (
            False,
            f"Error de rango: El esfuerzo estimado ({valor_esfuerzo} h) debe estar en el intervalo (0.0, 80.0] horas.",
        )
    return (True, "")


def validar_pertenencia_importancia(importancia: str) -> tuple[bool, str]:
    """Verifica que el nivel de importancia pertenezca al dominio {'ALTA', 'MEDIA', 'BAJA'}.

    Args:
        importancia: Etiqueta de importancia ingresada para la actividad.

    Returns:
        Tupla (es_valido, mensaje_error). Si es válido, mensaje_error es "".
    """
    if importancia is None or not isinstance(importancia, str):
        return (
            False,
            "Error de pertenencia: La importancia debe ser una cadena de texto.",
        )
    valor_normalizado: str = importancia.strip().upper()
    pertenece: bool = False
    for nivel_permitido in IMPORTANCIAS_VALIDAS:
        if valor_normalizado == nivel_permitido:
            pertenece = True
            break

    if not pertenece:
        return (
            False,
            f"Error de pertenencia: La importancia '{importancia}' no es válida. Valores permitidos: ALTA, MEDIA, BAJA.",
        )
    return (True, "")


def validar_extension_archivo(nombre_archivo: str) -> tuple[bool, str]:
    """Verifica que el nombre o ruta de archivo tenga nombre base y extensión permitida (.pdf, .py, .zip, .docx, .md).

    Args:
        nombre_archivo: Nombre o ruta del archivo a validar.

    Returns:
        Tupla (es_valido, mensaje_error). Si es válido, mensaje_error es "".
    """
    es_presente, msg_presencia = validar_presencia(nombre_archivo, "nombre_archivo")
    if not es_presente:
        return (False, msg_presencia)

    nombre_limpio: str = nombre_archivo.strip()
    ultimo_slash: int = nombre_limpio.rfind("/")
    ultimo_backslash: int = nombre_limpio.rfind("\\")
    indice_separador: int = (
        ultimo_slash if ultimo_slash > ultimo_backslash else ultimo_backslash
    )
    nombre_base: str = (
        nombre_limpio[indice_separador + 1 :] if indice_separador >= 0 else nombre_limpio
    )

    indice_punto: int = nombre_base.rfind(".")
    if indice_punto <= 0:
        return (
            False,
            f"Error de pertenencia: El archivo '{nombre_limpio}' no posee un nombre base o extensión válida.",
        )

    extension: str = nombre_base[indice_punto:].lower()
    extension_valida: bool = False
    for ext_permitida in EXTENSIONES_PERMITIDAS:
        if extension == ext_permitida:
            extension_valida = True
            break

    if not extension_valida:
        return (
            False,
            f"Error de pertenencia: La extensión '{extension}' no está permitida. Use: .pdf, .py, .zip, .docx, .md.",
        )
    return (True, "")


def verificar_consistencia_temporal(esfuerzo: float, tiempo_restante: float) -> tuple[bool, str]:
    """Evalúa si existe déficit temporal cuando el esfuerzo estimado supera el tiempo restante.

    Args:
        esfuerzo: Horas estimadas que tomará realizar la actividad.
        tiempo_restante: Horas disponibles antes del cierre de la entrega.

    Returns:
        Tupla (hay_deficit, mensaje_alerta). Devuelve (True, mensaje) si esfuerzo > tiempo_restante,
        o (False, "") si existe tiempo suficiente (esfuerzo <= tiempo_restante).

    Raises:
        ValueError: Si esfuerzo o tiempo_restante no son valores numéricos válidos en rango.
    """
    ok_esfuerzo, msg_esfuerzo = validar_rango_esfuerzo(esfuerzo)
    if not ok_esfuerzo:
        raise ValueError(msg_esfuerzo)

    ok_tiempo, msg_tiempo = validar_rango_tiempo(tiempo_restante)
    if not ok_tiempo:
        raise ValueError(msg_tiempo)

    valor_esfuerzo: float = float(esfuerzo)
    valor_tiempo: float = float(tiempo_restante)
    if valor_esfuerzo > valor_tiempo:
        deficit: float = round(valor_esfuerzo - valor_tiempo, 2)
        return (
            True,
            f"¡ALERTA DE DÉFICIT TEMPORAL! El esfuerzo estimado ({valor_esfuerzo:.2f} h) "
            f"supera el tiempo restante ({valor_tiempo:.2f} h) por {deficit:.2f} h.",
        )
    return (False, "")
