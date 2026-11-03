import calendar
import datetime


def division_segura(numerador, denominador):
    """Devuelve `None` (en vez de `ZeroDivisionError`) cuando el denominador
    es cero o nulo, o el numerador es nulo.

    Todo porcentaje o índice de la aplicación pasa por aquí: la UI debe
    mostrar un guion, nunca un 0% engañoso (docs/modelo-datos.md §10).
    """
    if not denominador or numerador is None:
        return None
    return numerador / denominador


def meses_entre(desde, hasta):
    """Lista ordenada de `(año, mes)` que el rango `[desde, hasta]`
    atraviesa, ambos extremos incluidos. Única implementación: antes de la
    fase 10 existían tres copias de este bucle (`apps.recursos.services`,
    `apps.ejecucion.services` y, de haberla escrito de nuevo, esta fase)."""
    meses = []
    anio, mes = desde.year, desde.month
    while (anio, mes) <= (hasta.year, hasta.month):
        meses.append((anio, mes))
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1
    return meses


def prorratear_por_mes(fecha_desde, fecha_hasta, valor_total, anio, mes):
    """Porción de `valor_total` (repartido uniformemente entre
    `fecha_desde` y `fecha_hasta`) que cae en el mes calendario `(anio,
    mes)`, prorrateada por días de intersección (docs/plan/fase-06-recursos-
    asignacion.md §6.1: una asignación del 01/02 al 31/03 con 200 horas
    reparte esas 200 horas proporcional a los 28 días de febrero y los 31
    de marzo que aporta cada uno al total de 59 días de la asignación).
    Devuelve `0` (del mismo tipo que `valor_total`, típicamente `Decimal`)
    si el mes no interseca el rango."""
    total_dias = (fecha_hasta - fecha_desde).days + 1
    primer_dia_mes = datetime.date(anio, mes, 1)
    ultimo_dia_mes = datetime.date(anio, mes, calendar.monthrange(anio, mes)[1])

    inicio_interseccion = max(fecha_desde, primer_dia_mes)
    fin_interseccion = min(fecha_hasta, ultimo_dia_mes)
    if inicio_interseccion > fin_interseccion:
        return type(valor_total)(0)

    dias_interseccion = (fin_interseccion - inicio_interseccion).days + 1
    return valor_total * dias_interseccion / total_dias
