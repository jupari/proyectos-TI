"""Única definición válida de las fórmulas de control (docs/modelo-datos.md
§10). Los serializers de proyecto (y, en fases posteriores, los de
seguimiento) reutilizan `resumen_ejecucion` y `semaforo_calculado` en vez de
reimplementar las fórmulas.

En esta fase (05) no existen todavía asignaciones, tareas, registros de
ejecución reales ni hitos cumplidos salvo los que siembre `seed_demo`: las
funciones ya quedan completas con sus fórmulas finales y solo se van
poblando sus fuentes en las fases siguientes, tal como pide el plan."""

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.core.calculos import division_segura
from apps.core.choices import EstadoAprobacion, EstadoHito, EstadoTarea, Semaforo

CERO = Decimal("0")


def _suma(relacion, campo, **filtros):
    return relacion.filter(activo=True, **filtros).aggregate(total=Sum(campo))["total"] or CERO


def _metricas(proyecto, fecha_corte):
    horas_planeadas = _suma(proyecto.asignaciones, "horas_planeadas")
    horas_ejecutadas = _suma(
        proyecto.registros_ejecucion, "horas", estado_aprobacion=EstadoAprobacion.APROBADO
    )
    costo_planeado = _suma(proyecto.asignaciones, "costo_planeado") + _suma(
        proyecto.rubros, "monto_planeado"
    )
    costo_ejecutado = _suma(
        proyecto.registros_ejecucion, "costo", estado_aprobacion=EstadoAprobacion.APROBADO
    ) + _suma(proyecto.gastos_ejecutados, "monto", estado_aprobacion=EstadoAprobacion.APROBADO)
    horas_pendientes_aprobacion = _suma(proyecto.registros_ejecucion, "horas") - horas_ejecutadas

    pct_horas = division_segura(horas_ejecutadas, horas_planeadas)
    pct_horas = float(pct_horas) * 100 if pct_horas is not None else None

    pct_dinero = division_segura(costo_ejecutado, costo_planeado)
    pct_dinero = float(pct_dinero) * 100 if pct_dinero is not None else None

    dias_totales_plan = (proyecto.fecha_fin_plan - proyecto.fecha_inicio_plan).days
    dias_transcurridos = max(
        0, min((fecha_corte - proyecto.fecha_inicio_plan).days, dias_totales_plan)
    )
    pct_tiempo = division_segura(dias_transcurridos, dias_totales_plan)
    pct_tiempo = pct_tiempo * 100 if pct_tiempo is not None else None

    avance = proyecto.avance_reportado
    avance_float = float(avance)

    spi = division_segura(avance_float, pct_tiempo)

    costo_planeado_segun_avance = (avance / Decimal("100")) * costo_planeado
    cpi = division_segura(float(costo_planeado_segun_avance), float(costo_ejecutado))
    desviacion_presupuestal = costo_ejecutado - costo_planeado_segun_avance

    hitos_cumplidos = proyecto.hitos.filter(activo=True, estado=EstadoHito.CUMPLIDO).count()
    hitos_incumplidos = proyecto.hitos.filter(activo=True, estado=EstadoHito.INCUMPLIDO).count()

    tareas_no_terminadas = proyecto.tareas.filter(activo=True).exclude(
        estado__in=[EstadoTarea.COMPLETADA, EstadoTarea.CANCELADA]
    )
    tareas_abiertas = tareas_no_terminadas.count()
    tareas_vencidas = tareas_no_terminadas.filter(fecha_fin_plan__lt=fecha_corte).count()

    return {
        "horas_planeadas": horas_planeadas,
        "horas_ejecutadas": horas_ejecutadas,
        "pct_horas": pct_horas,
        "costo_planeado": costo_planeado,
        "costo_ejecutado": costo_ejecutado,
        "pct_dinero": pct_dinero,
        "pct_tiempo": pct_tiempo,
        "avance": avance,
        "spi": spi,
        "cpi": cpi,
        "desviacion_presupuestal": desviacion_presupuestal,
        "horas_pendientes_aprobacion": horas_pendientes_aprobacion,
        "hitos_cumplidos": hitos_cumplidos,
        "hitos_incumplidos": hitos_incumplidos,
        "tareas_abiertas": tareas_abiertas,
        "tareas_vencidas": tareas_vencidas,
    }


def _evaluar_semaforo(metricas):
    """Tabla de docs/modelo-datos.md §10, evaluada en orden; el primer caso
    que aplica gana. Un insumo ausente (`None`) nunca dispara por sí solo
    una condición: una comparación con `None` siempre es falsa."""

    def _mayor(valor, umbral):
        return valor is not None and valor > umbral

    def _menor(valor, umbral):
        return valor is not None and valor < umbral

    pct_dinero = metricas["pct_dinero"]
    pct_horas = metricas["pct_horas"]
    pct_tiempo = metricas["pct_tiempo"]
    avance = float(metricas["avance"])
    cpi = metricas["cpi"]
    spi = metricas["spi"]
    hitos_incumplidos = metricas["hitos_incumplidos"]

    def _atraso(umbral):
        return pct_tiempo is not None and avance < pct_tiempo - umbral

    if _mayor(pct_dinero, 100) or _mayor(pct_horas, 110) or hitos_incumplidos > 0:
        return Semaforo.ROJO
    if _atraso(15) or _menor(cpi, 0.85) or _menor(spi, 0.85):
        return Semaforo.ROJO
    if _atraso(5) or _menor(cpi, 0.95) or _mayor(pct_dinero, 90):
        return Semaforo.AMARILLO
    return Semaforo.VERDE


def resumen_ejecucion(proyecto, fecha_corte=None):
    fecha_corte = fecha_corte or timezone.localdate()
    metricas = _metricas(proyecto, fecha_corte)
    return {
        "fecha_corte": fecha_corte,
        **metricas,
        "semaforo": _evaluar_semaforo(metricas),
    }


def semaforo_calculado(proyecto, fecha_corte=None):
    fecha_corte = fecha_corte or timezone.localdate()
    return _evaluar_semaforo(_metricas(proyecto, fecha_corte))
