"""Única definición válida de las fórmulas de control (docs/modelo-datos.md
§10). Los serializers de proyecto (y los de seguimiento) reutilizan
`resumen_ejecucion` y `semaforo_calculado` en vez de reimplementar las
fórmulas; las agregaciones del tablero (fase 10) hacen lo mismo a través de
`_metricas_desde_sumas`, el núcleo puro que comparten `_metricas` (una
instancia) y `tabla_proyectos` (muchas, por subconsulta) — nunca hay una
segunda copia de la fórmula.

El alcance por rol y los filtros de `/proyectos/` se resuelven en
`apps/tablero/views.py` (reutilizando `MixinAlcancePorRol.filtrar_por_rol` y
`FiltroProyecto`, los mismos que usa `ProyectoViewSet`): todas las funciones
de este módulo reciben el queryset de `Proyecto` ya acotado, nunca
`usuario` ni `filtros` en crudo. Así el alcance se aplica una sola vez, con
el mismo mecanismo que la lista de proyectos, en vez de reimplementarlo
cinco veces."""

from decimal import Decimal

from django.db.models import Count, DecimalField, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.core.calculos import (
    division_segura,
    meses_entre,
    prorratear_por_mes,
    prorratear_por_rango,
)
from apps.core.choices import (
    CategoriaRubro,
    EstadoAprobacion,
    EstadoCompromiso,
    EstadoHito,
    EstadoTarea,
    Semaforo,
)

CERO = Decimal("0")


def _suma(relacion, campo, **filtros):
    return relacion.filter(activo=True, **filtros).aggregate(total=Sum(campo))["total"] or CERO


def _metricas_desde_sumas(
    *,
    fecha_corte,
    fecha_inicio_plan,
    fecha_fin_plan,
    avance_reportado,
    horas_planeadas,
    horas_ejecutadas,
    costo_planeado,
    costo_ejecutado,
    horas_pendientes_aprobacion,
    hitos_cumplidos,
    hitos_incumplidos,
    tareas_abiertas,
    tareas_vencidas,
):
    """Núcleo puro de §10: a partir de sumas ya calculadas (por `_metricas`
    para un proyecto, por subconsulta masiva en `tabla_proyectos` para
    muchos), calcula porcentajes, índices y el resto del bloque
    `resumen_ejecucion`. Nunca recibe un `proyecto`; así no puede volver a
    hacer sus propias consultas."""
    pct_horas = division_segura(horas_ejecutadas, horas_planeadas)
    pct_horas = float(pct_horas) * 100 if pct_horas is not None else None

    pct_dinero = division_segura(costo_ejecutado, costo_planeado)
    pct_dinero = float(pct_dinero) * 100 if pct_dinero is not None else None

    dias_totales_plan = (fecha_fin_plan - fecha_inicio_plan).days
    dias_transcurridos = max(0, min((fecha_corte - fecha_inicio_plan).days, dias_totales_plan))
    pct_tiempo = division_segura(dias_transcurridos, dias_totales_plan)
    pct_tiempo = pct_tiempo * 100 if pct_tiempo is not None else None

    avance_float = float(avance_reportado)
    spi = division_segura(avance_float, pct_tiempo)

    costo_planeado_segun_avance = (avance_reportado / Decimal("100")) * costo_planeado
    cpi = division_segura(float(costo_planeado_segun_avance), float(costo_ejecutado))
    desviacion_presupuestal = costo_ejecutado - costo_planeado_segun_avance

    return {
        "horas_planeadas": horas_planeadas,
        "horas_ejecutadas": horas_ejecutadas,
        "pct_horas": pct_horas,
        "costo_planeado": costo_planeado,
        "costo_ejecutado": costo_ejecutado,
        "pct_dinero": pct_dinero,
        "pct_tiempo": pct_tiempo,
        "avance": avance_reportado,
        "spi": spi,
        "cpi": cpi,
        "desviacion_presupuestal": desviacion_presupuestal,
        "horas_pendientes_aprobacion": horas_pendientes_aprobacion,
        "hitos_cumplidos": hitos_cumplidos,
        "hitos_incumplidos": hitos_incumplidos,
        "tareas_abiertas": tareas_abiertas,
        "tareas_vencidas": tareas_vencidas,
    }


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
    horas_pendientes_aprobacion = _suma(
        proyecto.registros_ejecucion, "horas", estado_aprobacion=EstadoAprobacion.ENVIADO
    )

    hitos_cumplidos = proyecto.hitos.filter(activo=True, estado=EstadoHito.CUMPLIDO).count()
    hitos_incumplidos = proyecto.hitos.filter(activo=True, estado=EstadoHito.INCUMPLIDO).count()

    tareas_no_terminadas = proyecto.tareas.filter(activo=True).exclude(
        estado__in=[EstadoTarea.COMPLETADA, EstadoTarea.CANCELADA]
    )
    tareas_abiertas = tareas_no_terminadas.count()
    tareas_vencidas = tareas_no_terminadas.filter(fecha_fin_plan__lt=fecha_corte).count()

    return _metricas_desde_sumas(
        fecha_corte=fecha_corte,
        fecha_inicio_plan=proyecto.fecha_inicio_plan,
        fecha_fin_plan=proyecto.fecha_fin_plan,
        avance_reportado=proyecto.avance_reportado,
        horas_planeadas=horas_planeadas,
        horas_ejecutadas=horas_ejecutadas,
        costo_planeado=costo_planeado,
        costo_ejecutado=costo_ejecutado,
        horas_pendientes_aprobacion=horas_pendientes_aprobacion,
        hitos_cumplidos=hitos_cumplidos,
        hitos_incumplidos=hitos_incumplidos,
        tareas_abiertas=tareas_abiertas,
        tareas_vencidas=tareas_vencidas,
    )


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


# --- Tablero de control (fase 10) --------------------------------------------
#
# Todas las funciones de aquí en adelante reciben `proyectos`: el queryset de
# `Proyecto` que la vista ya acotó por rol y por los filtros de `/proyectos/`.


def resumen_global(proyectos):
    """Tarjetas globales del tablero: conteos por estado y semáforo, totales
    plan vs. ejecutado, proyectos en riesgo, horas pendientes de aprobación,
    compromisos vencidos, hitos incumplidos — todo acotado a `proyectos`."""
    from apps.ejecucion.models import GastoEjecutado, RegistroEjecucion
    from apps.proyectos.models import Hito, RubroPresupuesto
    from apps.recursos.models import AsignacionRecurso
    from apps.seguimiento.models import CompromisoSeguimiento

    por_estado = dict(
        proyectos.values("estado").annotate(total=Count("id")).values_list("estado", "total")
    )
    por_semaforo = dict(
        proyectos.values("semaforo").annotate(total=Count("id")).values_list("semaforo", "total")
    )

    asignaciones = AsignacionRecurso.objects.filter(proyecto__in=proyectos)
    registros = RegistroEjecucion.objects.filter(proyecto__in=proyectos)
    gastos = GastoEjecutado.objects.filter(proyecto__in=proyectos)

    horas_planeadas = _suma(asignaciones, "horas_planeadas")
    costo_planeado = _suma(asignaciones, "costo_planeado") + _suma(
        RubroPresupuesto.objects.filter(proyecto__in=proyectos), "monto_planeado"
    )
    horas_ejecutadas = _suma(registros, "horas", estado_aprobacion=EstadoAprobacion.APROBADO)
    costo_ejecutado = _suma(
        registros, "costo", estado_aprobacion=EstadoAprobacion.APROBADO
    ) + _suma(gastos, "monto", estado_aprobacion=EstadoAprobacion.APROBADO)
    horas_pendientes_aprobacion = _suma(
        registros, "horas", estado_aprobacion=EstadoAprobacion.ENVIADO
    )

    pct_horas = division_segura(horas_ejecutadas, horas_planeadas)
    pct_horas = float(pct_horas) * 100 if pct_horas is not None else None
    pct_dinero = division_segura(costo_ejecutado, costo_planeado)
    pct_dinero = float(pct_dinero) * 100 if pct_dinero is not None else None

    compromisos_vencidos = CompromisoSeguimiento.objects.filter(
        activo=True, estado=EstadoCompromiso.VENCIDO, seguimiento__proyecto__in=proyectos
    ).count()
    hitos_incumplidos = Hito.objects.filter(
        activo=True, estado=EstadoHito.INCUMPLIDO, proyecto__in=proyectos
    ).count()

    return {
        "total_proyectos": proyectos.count(),
        "por_estado": por_estado,
        "por_semaforo": por_semaforo,
        "proyectos_en_riesgo": por_semaforo.get(Semaforo.ROJO, 0),
        "horas_planeadas": horas_planeadas,
        "horas_ejecutadas": horas_ejecutadas,
        "pct_horas": pct_horas,
        "costo_planeado": costo_planeado,
        "costo_ejecutado": costo_ejecutado,
        "pct_dinero": pct_dinero,
        "horas_pendientes_aprobacion": horas_pendientes_aprobacion,
        "compromisos_vencidos": compromisos_vencidos,
        "hitos_incumplidos": hitos_incumplidos,
    }


def _subconsulta_suma(modelo, campo_fk, campo_valor, condicion=None):
    """`Coalesce(Subquery(...), 0)` correlacionada con `OuterRef("pk")` del
    `Proyecto` exterior: una subconsulta SQL por métrica, pero todas viajan
    en el mismo `SELECT` que `proyectos` — nunca una consulta adicional por
    fila ni por métrica. Evita el "fan-out" de anotar varios `Sum` sobre
    relaciones distintas en un solo `.annotate()` (multiplica filas y da
    totales incorrectos); cada métrica tiene su propia subconsulta aislada."""
    consulta = modelo.objects.filter(activo=True, **{campo_fk: OuterRef("pk")})
    if condicion is not None:
        consulta = consulta.filter(condicion)
    consulta = (
        consulta.order_by().values(campo_fk).annotate(total=Sum(campo_valor)).values("total")
    )
    return Coalesce(
        Subquery(consulta, output_field=DecimalField(max_digits=18, decimal_places=2)), CERO
    )


def _subconsulta_conteo(modelo, campo_fk, condicion=None):
    consulta = modelo.objects.filter(activo=True, **{campo_fk: OuterRef("pk")})
    if condicion is not None:
        consulta = consulta.filter(condicion)
    consulta = consulta.order_by().values(campo_fk).annotate(total=Count("id")).values("total")
    return Coalesce(Subquery(consulta, output_field=IntegerField()), 0)


def tabla_proyectos(proyectos):
    """Una fila por proyecto de `proyectos` con el bloque `resumen_ejecucion`
    completo. Resuelta con subconsultas correlacionadas: una sola consulta
    SQL trae todas las filas con todas sus métricas ya calculadas, para que
    el número de consultas sea independiente del número de proyectos
    (fase 10 §10.1; probado con `django_assert_num_queries`)."""
    from apps.ejecucion.models import GastoEjecutado, RegistroEjecucion
    from apps.proyectos.models import Hito, RubroPresupuesto
    from apps.recursos.models import AsignacionRecurso
    from apps.tareas.models import Tarea

    hoy = timezone.localdate()
    tareas_pendientes = ~Q(estado__in=[EstadoTarea.COMPLETADA, EstadoTarea.CANCELADA])

    proyectos = proyectos.select_related(
        "area_solicitante", "portafolio", "gerente", "lider_tecnico"
    ).annotate(
        _horas_planeadas=_subconsulta_suma(AsignacionRecurso, "proyecto", "horas_planeadas"),
        _costo_planeado_personal=_subconsulta_suma(
            AsignacionRecurso, "proyecto", "costo_planeado"
        ),
        _costo_planeado_rubros=_subconsulta_suma(RubroPresupuesto, "proyecto", "monto_planeado"),
        _horas_ejecutadas=_subconsulta_suma(
            RegistroEjecucion,
            "proyecto",
            "horas",
            Q(estado_aprobacion=EstadoAprobacion.APROBADO),
        ),
        _costo_ejecutado_horas=_subconsulta_suma(
            RegistroEjecucion,
            "proyecto",
            "costo",
            Q(estado_aprobacion=EstadoAprobacion.APROBADO),
        ),
        _costo_ejecutado_gastos=_subconsulta_suma(
            GastoEjecutado,
            "proyecto",
            "monto",
            Q(estado_aprobacion=EstadoAprobacion.APROBADO),
        ),
        _horas_pendientes=_subconsulta_suma(
            RegistroEjecucion,
            "proyecto",
            "horas",
            Q(estado_aprobacion=EstadoAprobacion.ENVIADO),
        ),
        _hitos_cumplidos=_subconsulta_conteo(Hito, "proyecto", Q(estado=EstadoHito.CUMPLIDO)),
        _hitos_incumplidos=_subconsulta_conteo(
            Hito, "proyecto", Q(estado=EstadoHito.INCUMPLIDO)
        ),
        _tareas_abiertas=_subconsulta_conteo(Tarea, "proyecto", tareas_pendientes),
        _tareas_vencidas=_subconsulta_conteo(
            Tarea, "proyecto", tareas_pendientes & Q(fecha_fin_plan__lt=hoy)
        ),
    )

    filas = []
    for proyecto in proyectos:
        metricas = _metricas_desde_sumas(
            fecha_corte=hoy,
            fecha_inicio_plan=proyecto.fecha_inicio_plan,
            fecha_fin_plan=proyecto.fecha_fin_plan,
            avance_reportado=proyecto.avance_reportado,
            horas_planeadas=proyecto._horas_planeadas,
            horas_ejecutadas=proyecto._horas_ejecutadas,
            costo_planeado=proyecto._costo_planeado_personal + proyecto._costo_planeado_rubros,
            costo_ejecutado=proyecto._costo_ejecutado_horas + proyecto._costo_ejecutado_gastos,
            horas_pendientes_aprobacion=proyecto._horas_pendientes,
            hitos_cumplidos=proyecto._hitos_cumplidos,
            hitos_incumplidos=proyecto._hitos_incumplidos,
            tareas_abiertas=proyecto._tareas_abiertas,
            tareas_vencidas=proyecto._tareas_vencidas,
        )
        filas.append(
            {
                "id": str(proyecto.id),
                "codigo": proyecto.codigo,
                "nombre": proyecto.nombre,
                "gerente": proyecto.gerente.nombre_completo if proyecto.gerente_id else None,
                "estado": proyecto.estado,
                "resumen_ejecucion": {
                    "fecha_corte": hoy,
                    **metricas,
                    "semaforo": _evaluar_semaforo(metricas),
                },
            }
        )
    return filas


def ejecucion_mensual(proyectos, desde=None, hasta=None):
    """Serie mensual `[{mes, horas_plan, horas_ejec, costo_plan, costo_ejec,
    horas_ejec_acum, costo_ejec_acum}]` agregada sobre `proyectos`. Mismo
    prorrateo de `apps.ejecucion.services.comparativo_por_mes` (un solo
    proyecto), generalizado a varios a la vez; si no se dan `desde`/`hasta`
    se usa el rango que cubren las asignaciones y registros encontrados."""
    from apps.ejecucion.models import RegistroEjecucion
    from apps.recursos.models import AsignacionRecurso

    asignaciones = list(AsignacionRecurso.objects.filter(activo=True, proyecto__in=proyectos))
    registros = list(
        RegistroEjecucion.objects.filter(
            activo=True, estado_aprobacion=EstadoAprobacion.APROBADO, proyecto__in=proyectos
        )
    )

    if desde is None or hasta is None:
        fechas = [a.fecha_desde for a in asignaciones] + [a.fecha_hasta for a in asignaciones]
        fechas += [r.periodo_inicio for r in registros] + [r.periodo_fin for r in registros]
        if not fechas:
            return []
        desde = desde or min(fechas)
        hasta = hasta or max(fechas)

    horas_ejec_acum = CERO
    costo_ejec_acum = CERO
    resultado = []
    for anio, mes in meses_entre(desde, hasta):
        horas_plan = CERO
        costo_plan = CERO
        for asignacion in asignaciones:
            horas_plan += prorratear_por_mes(
                asignacion.fecha_desde,
                asignacion.fecha_hasta,
                asignacion.horas_planeadas,
                anio,
                mes,
            )
            costo_plan += prorratear_por_mes(
                asignacion.fecha_desde,
                asignacion.fecha_hasta,
                asignacion.costo_planeado,
                anio,
                mes,
            )

        horas_ejec = CERO
        costo_ejec = CERO
        for registro in registros:
            if registro.periodo_inicio.year == anio and registro.periodo_inicio.month == mes:
                horas_ejec += registro.horas
                costo_ejec += registro.costo

        horas_ejec_acum += horas_ejec
        costo_ejec_acum += costo_ejec
        resultado.append(
            {
                "mes": f"{anio}-{mes:02d}",
                "horas_plan": horas_plan,
                "horas_ejec": horas_ejec,
                "costo_plan": costo_plan,
                "costo_ejec": costo_ejec,
                "horas_ejec_acum": horas_ejec_acum,
                "costo_ejec_acum": costo_ejec_acum,
            }
        )
    return resultado


def tabla_proyectos_por_periodo(proyectos, desde, hasta):
    """Una fila por proyecto con sus horas planeadas y ejecutadas dentro de
    `[desde, hasta]` (típicamente una semana o un mes elegidos a mano,
    fase 10 adenda), más una fila de totales. A diferencia de
    `tabla_proyectos` (histórico completo del proyecto, sin fecha), esto
    filtra por periodo: lo planeado se prorratea por intersección de días
    calendario con cada asignación (`prorratear_por_rango`, igual
    convención que `ejecucion_mensual`/`comparativo_por_mes` pero sin
    partir el periodo en meses, para que una semana no se calcule de más
    prorrateando el mes entero); lo ejecutado suma los `RegistroEjecucion`
    `APROBADO` cuyo `periodo_inicio` cae en el rango."""
    from apps.ejecucion.models import RegistroEjecucion
    from apps.recursos.models import AsignacionRecurso

    asignaciones_por_proyecto = {}
    for asignacion in AsignacionRecurso.objects.filter(activo=True, proyecto__in=proyectos):
        asignaciones_por_proyecto.setdefault(asignacion.proyecto_id, []).append(asignacion)

    horas_ejec_por_proyecto = {
        fila["proyecto"]: fila["total"] or CERO
        for fila in RegistroEjecucion.objects.filter(
            activo=True,
            estado_aprobacion=EstadoAprobacion.APROBADO,
            proyecto__in=proyectos,
            periodo_inicio__gte=desde,
            periodo_inicio__lte=hasta,
        )
        .values("proyecto")
        .annotate(total=Sum("horas"))
    }

    filas = []
    total_plan = CERO
    total_ejec = CERO
    for proyecto in proyectos:
        horas_plan = CERO
        for asignacion in asignaciones_por_proyecto.get(proyecto.id, []):
            horas_plan += prorratear_por_rango(
                asignacion.fecha_desde,
                asignacion.fecha_hasta,
                asignacion.horas_planeadas,
                desde,
                hasta,
            )
        horas_ejec = horas_ejec_por_proyecto.get(proyecto.id, CERO)
        pct_horas = division_segura(horas_ejec, horas_plan)
        filas.append(
            {
                "id": str(proyecto.id),
                "codigo": proyecto.codigo,
                "nombre": proyecto.nombre,
                "horas_plan": horas_plan,
                "horas_ejec": horas_ejec,
                "pct_horas": float(pct_horas) * 100 if pct_horas is not None else None,
            }
        )
        total_plan += horas_plan
        total_ejec += horas_ejec

    pct_total = division_segura(total_ejec, total_plan)
    return {
        "filas": sorted(filas, key=lambda f: f["nombre"]),
        "totales": {
            "horas_plan": total_plan,
            "horas_ejec": total_ejec,
            "pct_horas": float(pct_total) * 100 if pct_total is not None else None,
        },
    }


def _nuevo_acumulador(campos):
    return dict.fromkeys(campos, CERO)


def _sumar_en(acumulador, valores):
    for campo in acumulador:
        acumulador[campo] += valores[campo]


def _armar_bloque(categoria, etiqueta, filas, campos, claves_mes):
    """Agrega `filas` (cada una con `por_mes`/`total` ya calculados) en un
    bloque con subtotal por mes y subtotal total — misma forma para el
    bloque de personal (4 campos: horas/valor x plan/ejec) y los de rubro
    (2 campos: solo valor), para no repetir la lógica de acumular dos veces."""
    subtotal_por_mes = {clave: _nuevo_acumulador(campos) for clave in claves_mes}
    subtotal_total = _nuevo_acumulador(campos)
    for fila in filas:
        for clave in claves_mes:
            _sumar_en(subtotal_por_mes[clave], fila["por_mes"][clave])
        _sumar_en(subtotal_total, fila["total"])
    return {
        "categoria": categoria,
        "etiqueta": etiqueta,
        "filas": filas,
        "subtotal": {"por_mes": subtotal_por_mes, "total": subtotal_total},
    }


def plan_costos_proyecto(proyecto, desde=None, hasta=None):
    """Plan de costos de UN proyecto (fase 15), inspirado en una plantilla de
    flujo de pagos mensual: por cada mes del rango, costo planeado vs.
    ejecutado, desglosado en un bloque "Personal" (una fila por recurso, con
    horas y valor) y un bloque por cada categoría de `RubroPresupuesto` con
    datos en el proyecto (`CategoriaRubro`: LICENCIAS, INFRAESTRUCTURA,
    SERVICIOS, CAPACITACION, OTROS — solo valor, sin horas), más subtotal por
    bloque y un total general en dinero.

    Sin `desde`/`hasta` se usa la planeación completa del proyecto
    (`fecha_inicio_plan`–`fecha_fin_plan`). Reutiliza el mismo prorrateo que
    `ejecucion_mensual` (`prorratear_por_mes`) para el personal; los rubros
    no tienen fecha propia, así que su `monto_planeado` se reparte en partes
    iguales entre los meses del rango (no hay otra forma de saber cuándo se
    gastará, y así no hace falta pedir un dato nuevo).

    Los `RubroPresupuesto` con `categoria=PERSONAL` se excluyen del bloque
    por categoría: el personal de este reporte sale de `AsignacionRecurso`,
    no de un rubro (nada obliga hoy a que exista un rubro de personal, y
    mostrarlo aparte duplicaría el costo)."""
    from apps.ejecucion.models import GastoEjecutado, RegistroEjecucion
    from apps.proyectos.models import RubroPresupuesto
    from apps.recursos.models import AsignacionRecurso

    desde = desde or proyecto.fecha_inicio_plan
    hasta = hasta or proyecto.fecha_fin_plan
    meses = meses_entre(desde, hasta)
    claves_mes = [f"{anio}-{mes:02d}" for anio, mes in meses]
    campos_personal = ("horas_plan", "valor_plan", "horas_ejec", "valor_ejec")
    campos_dinero = ("valor_plan", "valor_ejec")

    # --- Personal: una fila por recurso, sumando todas sus asignaciones ----
    asignaciones_por_recurso = {}
    for asignacion in AsignacionRecurso.objects.filter(
        activo=True, proyecto=proyecto
    ).select_related("recurso", "recurso__perfil"):
        asignaciones_por_recurso.setdefault(asignacion.recurso_id, []).append(asignacion)

    registros_por_recurso = {}
    for registro in RegistroEjecucion.objects.filter(
        activo=True, estado_aprobacion=EstadoAprobacion.APROBADO, proyecto=proyecto
    ):
        registros_por_recurso.setdefault(registro.recurso_id, []).append(registro)

    filas_personal = []
    for recurso_id, asignaciones in asignaciones_por_recurso.items():
        recurso = asignaciones[0].recurso
        registros = registros_por_recurso.get(recurso_id, [])
        por_mes = {}
        total = _nuevo_acumulador(campos_personal)
        for (anio, mes), clave in zip(meses, claves_mes, strict=True):
            horas_plan = sum(
                (
                    prorratear_por_mes(a.fecha_desde, a.fecha_hasta, a.horas_planeadas, anio, mes)
                    for a in asignaciones
                ),
                CERO,
            )
            valor_plan = sum(
                (
                    prorratear_por_mes(a.fecha_desde, a.fecha_hasta, a.costo_planeado, anio, mes)
                    for a in asignaciones
                ),
                CERO,
            )
            registros_del_mes = [
                r
                for r in registros
                if (r.periodo_inicio.year, r.periodo_inicio.month) == (anio, mes)
            ]
            horas_ejec = sum((r.horas for r in registros_del_mes), CERO)
            valor_ejec = sum((r.costo for r in registros_del_mes), CERO)
            valores = {
                "horas_plan": horas_plan,
                "valor_plan": valor_plan,
                "horas_ejec": horas_ejec,
                "valor_ejec": valor_ejec,
            }
            por_mes[clave] = valores
            _sumar_en(total, valores)

        # Si el recurso tiene más de una asignación en el proyecto, el rol y
        # la tarifa que se muestran son los de la primera: las horas y el
        # costo sí suman todas, pero mostrar varios roles/tarifas a la vez
        # no cabe en una sola fila.
        primera = asignaciones[0]
        filas_personal.append(
            {
                "id": str(recurso_id),
                "nombre": recurso.nombre,
                "perfil": recurso.perfil.nombre if recurso.perfil else None,
                "rol": primera.rol_en_proyecto,
                "valor_hora": primera.valor_hora_plan,
                "dedicacion_pct": primera.porcentaje_dedicacion,
                "por_mes": por_mes,
                "total": total,
            }
        )
    filas_personal.sort(key=lambda f: f["nombre"])
    bloques = [
        _armar_bloque(
            "PERSONAL",
            CategoriaRubro.PERSONAL.label,
            filas_personal,
            campos_personal,
            claves_mes,
        )
    ]

    # --- Un bloque por cada categoría de rubro (no-personal) con datos -----
    cantidad_meses = len(meses) or 1
    rubros_por_categoria = {}
    for rubro in RubroPresupuesto.objects.filter(activo=True, proyecto=proyecto).exclude(
        categoria=CategoriaRubro.PERSONAL
    ):
        rubros_por_categoria.setdefault(rubro.categoria, []).append(rubro)

    gastos_por_rubro = {}
    for gasto in GastoEjecutado.objects.filter(
        activo=True, estado_aprobacion=EstadoAprobacion.APROBADO, proyecto=proyecto
    ):
        gastos_por_rubro.setdefault(gasto.rubro_id, []).append(gasto)

    for categoria, rubros in rubros_por_categoria.items():
        filas_categoria = []
        for rubro in sorted(rubros, key=lambda r: r.descripcion):
            valor_plan_mensual = rubro.monto_planeado / cantidad_meses
            gastos = gastos_por_rubro.get(rubro.id, [])
            por_mes = {}
            total = _nuevo_acumulador(campos_dinero)
            for (anio, mes), clave in zip(meses, claves_mes, strict=True):
                valor_ejec = sum(
                    (g.monto for g in gastos if (g.fecha.year, g.fecha.month) == (anio, mes)),
                    CERO,
                )
                valores = {"valor_plan": valor_plan_mensual, "valor_ejec": valor_ejec}
                por_mes[clave] = valores
                _sumar_en(total, valores)
            filas_categoria.append(
                {
                    "id": str(rubro.id),
                    "nombre": rubro.descripcion,
                    "por_mes": por_mes,
                    "total": total,
                }
            )
        bloques.append(
            _armar_bloque(
                categoria,
                CategoriaRubro(categoria).label,
                filas_categoria,
                campos_dinero,
                claves_mes,
            )
        )

    total_general = _armar_bloque(
        None,
        "Total general",
        [{"por_mes": b["subtotal"]["por_mes"], "total": b["subtotal"]["total"]} for b in bloques],
        campos_dinero,
        claves_mes,
    )

    return {
        "meses": claves_mes,
        "bloques": bloques,
        "total_general": total_general["subtotal"],
    }


def ocupacion_recursos(proyectos, desde, hasta, perfil=None):
    """Por cada recurso con alguna asignación activa en `proyectos` dentro
    de `[desde, hasta]`: horas planeadas, ejecutadas, capacidad y % de
    ocupación, reutilizando `apps.recursos.services.carga_recurso` (misma
    fórmula que la fase 06, nunca una copia).

    La ocupación de cada recurso se calcula sobre TODOS sus proyectos, no
    solo los visibles para el usuario actual (`proyectos` solo decide qué
    recursos *entran* en la lista): un % de ocupación recortado a una
    porción del trabajo del recurso dejaría de significar lo que dice
    medir — si está sobreasignado en conjunto, debe verse sobreasignado
    aquí también."""
    from apps.recursos.models import AsignacionRecurso, Recurso
    from apps.recursos.services import carga_recurso

    ids_recurso = list(
        AsignacionRecurso.objects.filter(
            activo=True,
            proyecto__in=proyectos,
            fecha_desde__lte=hasta,
            fecha_hasta__gte=desde,
        )
        .values_list("recurso_id", flat=True)
        .distinct()
    )
    recursos = Recurso.objects.filter(activo=True, id__in=ids_recurso).select_related("perfil")
    if perfil:
        recursos = recursos.filter(perfil_id=perfil)

    resultado = []
    for recurso in recursos:
        for mes in carga_recurso(recurso, desde, hasta):
            resultado.append({"recurso": str(recurso.id), "recurso_nombre": recurso.nombre, **mes})
    return resultado


def resumen_tareas(proyectos):
    """Conteo de tareas de `proyectos` por estado, vencidas, creadas durante
    la ejecución y promedio de días de atraso de las vencidas."""
    from apps.tareas.models import Tarea

    tareas = Tarea.objects.filter(activo=True, proyecto__in=proyectos)
    por_estado = dict(
        tareas.values("estado").annotate(total=Count("id")).values_list("estado", "total")
    )

    hoy = timezone.localdate()
    no_terminadas = tareas.exclude(estado__in=[EstadoTarea.COMPLETADA, EstadoTarea.CANCELADA])
    fechas_vencidas = list(
        no_terminadas.filter(fecha_fin_plan__lt=hoy).values_list("fecha_fin_plan", flat=True)
    )
    creadas_durante_ejecucion = tareas.filter(creada_durante_ejecucion=True).count()
    promedio_dias_atraso = (
        sum((hoy - fecha).days for fecha in fechas_vencidas) / len(fechas_vencidas)
        if fechas_vencidas
        else None
    )

    return {
        "por_estado": por_estado,
        "total": sum(por_estado.values()),
        "vencidas": len(fechas_vencidas),
        "creadas_durante_ejecucion": creadas_durante_ejecucion,
        "promedio_dias_atraso": promedio_dias_atraso,
    }
