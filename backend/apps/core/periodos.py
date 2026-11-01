"""Funciones puras de periodos. Las usan las fases 08 (ejecución) y 09
(seguimiento) para no reimplementar la normalización de periodos diaria,
semanal y mensual."""

import calendar
import datetime

from apps.core.choices import Periodicidad


def normalizar_periodo(periodicidad, fecha):
    """Devuelve `(periodo_inicio, periodo_fin)` para la periodicidad dada,
    de forma que el periodo contenga a `fecha`.

    - `DIARIA`: el mismo día.
    - `SEMANAL`: de lunes a domingo.
    - `MENSUAL`: del primer al último día del mes.
    """
    if periodicidad == Periodicidad.DIARIA:
        return fecha, fecha
    if periodicidad == Periodicidad.SEMANAL:
        inicio = fecha - datetime.timedelta(days=fecha.weekday())
        fin = inicio + datetime.timedelta(days=6)
        return inicio, fin
    if periodicidad == Periodicidad.MENSUAL:
        inicio = fecha.replace(day=1)
        ultimo_dia = calendar.monthrange(fecha.year, fecha.month)[1]
        fin = fecha.replace(day=ultimo_dia)
        return inicio, fin
    raise ValueError(f"Periodicidad desconocida: {periodicidad!r}")


def periodos_entre(periodicidad, desde, hasta):
    """Lista de periodos `(periodo_inicio, periodo_fin)` que cubren, de forma
    contigua y sin solapes, el rango `[desde, hasta]`."""
    if desde > hasta:
        return []

    periodos = []
    inicio_actual, fin_actual = normalizar_periodo(periodicidad, desde)
    while inicio_actual <= hasta:
        periodos.append((inicio_actual, fin_actual))
        siguiente_fecha = fin_actual + datetime.timedelta(days=1)
        inicio_actual, fin_actual = normalizar_periodo(periodicidad, siguiente_fecha)
    return periodos


def dias_habiles(desde, hasta):
    """Cuenta días hábiles (lunes a viernes) entre dos fechas, ambas incluidas.

    Limitación documentada: no considera festivos, solo fines de semana.
    """
    if desde > hasta:
        return 0

    dias = 0
    fecha = desde
    while fecha <= hasta:
        if fecha.weekday() < 5:
            dias += 1
        fecha += datetime.timedelta(days=1)
    return dias
