"""Pieza crítica del control presupuestal: resolución de tarifas y reglas
de asignación (docs/modelo-datos.md §4 y §10)."""

import calendar
import datetime
from decimal import Decimal

from django.db.models import Q, Sum
from rest_framework.exceptions import ValidationError

from apps.core.calculos import division_segura, meses_entre, prorratear_por_mes
from apps.core.exceptions import ErrorReglaNegocio


def valor_hora_vigente(recurso, fecha):
    """Única función autorizada para resolver la tarifa de un recurso a una
    fecha dada (docs/modelo-datos.md §4). Orden de resolución:
    1. `TarifaRecurso` vigente a `fecha` (rango cerrado, `vigente_hasta`
       nulo significa "sin fin").
    2. `recurso.perfil.tarifa_hora_referencia`.
    3. Error accionable si no hay ninguna de las dos.
    """
    tarifa = (
        recurso.tarifas.filter(activo=True, vigente_desde__lte=fecha)
        .filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha))
        .order_by("-vigente_desde")
        .first()
    )
    if tarifa is not None:
        return tarifa.valor_hora
    if recurso.perfil is not None:
        return recurso.perfil.tarifa_hora_referencia
    raise ErrorReglaNegocio(
        f"El recurso {recurso.nombre} no tiene tarifa vigente al {fecha}; "
        "registre una tarifa o asígnele un perfil."
    )


def validar_vigencias(recurso, tarifa_nueva):
    """Valida (y ajusta) la vigencia de `tarifa_nueva` (instancia sin
    guardar o en edición) contra las demás tarifas activas del recurso.

    Si `tarifa_nueva` no tiene `vigente_hasta`, cierra automáticamente el
    día previo a `vigente_desde` la tarifa abierta anterior (si existe) y lo
    agrega a los avisos devueltos. Luego comprueba que no quede ningún
    solapamiento real; si lo hay, lanza `ErrorReglaNegocio` proponiendo el
    ajuste. Devuelve la lista de avisos (puede ser vacía).
    """
    avisos = []

    if tarifa_nueva.vigente_hasta is None:
        anteriores_abiertas = recurso.tarifas.filter(activo=True, vigente_hasta__isnull=True)
        if tarifa_nueva.pk:
            anteriores_abiertas = anteriores_abiertas.exclude(pk=tarifa_nueva.pk)
        anterior = (
            anteriores_abiertas.filter(vigente_desde__lt=tarifa_nueva.vigente_desde)
            .order_by("-vigente_desde")
            .first()
        )
        if anterior is not None:
            nuevo_fin = tarifa_nueva.vigente_desde - datetime.timedelta(days=1)
            anterior.vigente_hasta = nuevo_fin
            anterior.save(update_fields=["vigente_hasta", "actualizado_en"])
            avisos.append(
                f"Se cerró la tarifa vigente desde {anterior.vigente_desde} el {nuevo_fin}."
            )

    solapadas = recurso.tarifas.filter(activo=True)
    if tarifa_nueva.pk:
        solapadas = solapadas.exclude(pk=tarifa_nueva.pk)
    solapadas = solapadas.filter(
        Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=tarifa_nueva.vigente_desde)
    )
    if tarifa_nueva.vigente_hasta is not None:
        solapadas = solapadas.filter(vigente_desde__lte=tarifa_nueva.vigente_hasta)

    primera_solapada = solapadas.order_by("vigente_desde").first()
    if primera_solapada is not None:
        dia_previo = tarifa_nueva.vigente_desde - datetime.timedelta(days=1)
        raise ErrorReglaNegocio(
            {
                "vigente_desde": [
                    f"La vigencia se solapa con la tarifa desde {primera_solapada.vigente_desde}; "
                    f"cierre esa tarifa el {dia_previo} antes de crear esta."
                ]
            }
        )

    return avisos


def calcular_costo_planeado(asignacion):
    return asignacion.horas_planeadas * asignacion.valor_hora_plan


def _advertencias_sobreasignacion(asignacion):
    """Advertencia (no error) por cada mes en el que la dedicación acumulada
    del recurso, sumando `asignacion` a sus demás asignaciones activas,
    supere el 100% (docs/api-contrato.md §5)."""
    otras = asignacion.recurso.asignaciones.filter(activo=True)
    if asignacion.pk:
        otras = otras.exclude(pk=asignacion.pk)

    advertencias = []
    for anio, mes in meses_entre(asignacion.fecha_desde, asignacion.fecha_hasta):
        primer_dia = datetime.date(anio, mes, 1)
        ultimo_dia = datetime.date(anio, mes, calendar.monthrange(anio, mes)[1])
        dedicacion_otras = (
            otras.filter(fecha_desde__lte=ultimo_dia, fecha_hasta__gte=primer_dia).aggregate(
                total=Sum("porcentaje_dedicacion")
            )["total"]
            or 0
        )
        total = dedicacion_otras + asignacion.porcentaje_dedicacion
        if total > 100:
            advertencias.append(f"El recurso queda al {total}% en {anio}-{mes:02d}.")
    return advertencias


def validar_asignacion(asignacion):
    """Valida `asignacion` (instancia sin guardar o en edición) y devuelve
    la lista de advertencias de sobreasignación (nunca bloquean)."""
    proyecto = asignacion.proyecto
    recurso = asignacion.recurso

    if (
        asignacion.fecha_desde < proyecto.fecha_inicio_plan
        or asignacion.fecha_hasta > proyecto.fecha_fin_plan
    ):
        # docs/modelo-datos.md §4: esta regla específica responde 400, a
        # diferencia de las demás de esta función (422 vía ErrorReglaNegocio).
        raise ValidationError(
            {
                "fecha_desde": [
                    "El rango de la asignación debe caer dentro de las fechas plan del "
                    "proyecto."
                ]
            }
        )

    if not recurso.activo:
        raise ErrorReglaNegocio({"recurso": ["El recurso está inactivo."]})
    if recurso.fecha_retiro is not None and recurso.fecha_retiro < asignacion.fecha_hasta:
        raise ErrorReglaNegocio(
            {"fecha_hasta": [f"El recurso se retira el {recurso.fecha_retiro}."]}
        )

    return _advertencias_sobreasignacion(asignacion)


def carga_recurso(recurso, desde, hasta):
    """Horas planeadas y ejecutadas por mes entre `desde` y `hasta`. Lo
    planeado se prorratea por días calendario de intersección entre cada
    asignación y el mes (p. ej. una asignación del 01/02 al 31/03 con 200
    horas reparte esas 200 horas proporcional a los 28 días de febrero y
    los 31 de marzo que aporta cada uno al total de 59 días de la
    asignación). Lo ejecutado suma los registros `APROBADO` cuyo
    `periodo_inicio` cae en el mes (misma convención de simplificación que
    `apps.ejecucion.services.comparativo_por_mes`: un `SEMANAL` que cruza
    fin de mes no se fracciona)."""
    from apps.core.choices import EstadoAprobacion

    asignaciones = list(
        recurso.asignaciones.filter(activo=True, fecha_desde__lte=hasta, fecha_hasta__gte=desde)
    )
    registros = list(
        recurso.registros_ejecucion.filter(
            activo=True,
            estado_aprobacion=EstadoAprobacion.APROBADO,
            periodo_inicio__gte=desde,
            periodo_inicio__lte=hasta,
        )
    )

    resultado = []
    for anio, mes in meses_entre(desde, hasta):
        horas_planeadas = Decimal("0")
        for asignacion in asignaciones:
            horas_planeadas += prorratear_por_mes(
                asignacion.fecha_desde,
                asignacion.fecha_hasta,
                asignacion.horas_planeadas,
                anio,
                mes,
            )

        horas_ejecutadas = sum(
            (
                r.horas
                for r in registros
                if r.periodo_inicio.year == anio and r.periodo_inicio.month == mes
            ),
            Decimal("0"),
        )

        capacidad = recurso.capacidad_horas_mes
        pct_ocupacion = division_segura(horas_planeadas, capacidad)
        pct_ocupacion = float(pct_ocupacion) * 100 if pct_ocupacion is not None else None

        resultado.append(
            {
                "anio": anio,
                "mes": mes,
                "horas_planeadas": horas_planeadas,
                "horas_ejecutadas": horas_ejecutadas,
                "capacidad": capacidad,
                "pct_ocupacion": pct_ocupacion,
            }
        )
    return resultado
