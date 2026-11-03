import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.choices import EstadoAprobacion
from apps.ejecucion.tests.factories import GastoEjecutadoFactory, RegistroEjecucionFactory
from apps.proyectos.models import Proyecto
from apps.proyectos.tests.factories import HitoFactory, ProyectoFactory, RubroPresupuestoFactory
from apps.recursos.services import carga_recurso
from apps.recursos.tests.factories import AsignacionRecursoFactory, RecursoFactory
from apps.tareas.tests.factories import TareaFactory

from ..services import ejecucion_mensual, resumen_ejecucion, resumen_global, tabla_proyectos

pytestmark = pytest.mark.django_db


def test_resumen_ejecucion_costo_planeado_suma_asignaciones_y_rubros():
    """docs/plan/fase-06 §6.2.7: desde esta fase, `horas_planeadas` y la
    parte de personal de `costo_planeado` tienen fuente real en
    `AsignacionRecurso` (antes de esta fase daban 0 siempre)."""
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 12, 31)
    )
    AsignacionRecursoFactory(
        proyecto=proyecto, horas_planeadas=400, valor_hora_plan=70_000
    )  # costo_planeado = 28_000_000
    AsignacionRecursoFactory(
        proyecto=proyecto,
        horas_planeadas=200,
        valor_hora_plan=80_000,
        fecha_desde=datetime.date(2026, 2, 1),
        fecha_hasta=datetime.date(2026, 7, 31),
    )  # costo_planeado = 16_000_000
    RubroPresupuestoFactory(proyecto=proyecto, monto_planeado=5_000_000)

    resumen = resumen_ejecucion(proyecto, fecha_corte=datetime.date(2026, 6, 1))

    assert resumen["horas_planeadas"] == Decimal("600.00")
    assert resumen["costo_planeado"] == Decimal("49000000.00")
    # sin ejecución todavía (fase 08): lo ejecutado sigue en cero, no en null.
    assert resumen["horas_ejecutadas"] == Decimal("0")
    assert resumen["pct_horas"] == 0.0


def test_resumen_ejecucion_con_ejecucion_real_cuenta_solo_lo_aprobado(roles):
    """docs/plan/fase-08-ejecucion-ingesta.md §8.1.5: desde esta fase
    `horas_ejecutadas` y `costo_ejecutado` tienen fuente real en
    `RegistroEjecucion`/`GastoEjecutado`; solo suma lo `APROBADO`, y
    `horas_pendientes_aprobacion` cuenta únicamente lo `ENVIADO` (ni
    `BORRADOR` ni `RECHAZADO`). Los valores esperados se calculan a mano
    aquí, no reutilizando las fórmulas de `_metricas`."""
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1),
        fecha_fin_plan=datetime.date(2026, 12, 31),
        avance_reportado=Decimal("30.00"),
    )
    AsignacionRecursoFactory(proyecto=proyecto, horas_planeadas=400, valor_hora_plan=70_000)
    rubro = RubroPresupuestoFactory(proyecto=proyecto, monto_planeado=5_000_000)

    RegistroEjecucionFactory(
        proyecto=proyecto,
        horas=100,
        valor_hora_aplicado=70_000,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        periodo_inicio=datetime.date(2026, 2, 1),
        periodo_fin=datetime.date(2026, 2, 1),
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        horas=20,
        valor_hora_aplicado=70_000,
        estado_aprobacion=EstadoAprobacion.ENVIADO,
        periodo_inicio=datetime.date(2026, 2, 2),
        periodo_fin=datetime.date(2026, 2, 2),
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        horas=15,
        valor_hora_aplicado=70_000,
        estado_aprobacion=EstadoAprobacion.RECHAZADO,
        periodo_inicio=datetime.date(2026, 2, 3),
        periodo_fin=datetime.date(2026, 2, 3),
    )
    GastoEjecutadoFactory(
        proyecto=proyecto,
        rubro=rubro,
        monto=2_000_000,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        numero_documento="FAC-APROBADO",
    )
    GastoEjecutadoFactory(
        proyecto=proyecto,
        rubro=rubro,
        monto=500_000,
        estado_aprobacion=EstadoAprobacion.ENVIADO,
        numero_documento="FAC-ENVIADO",
    )

    fecha_corte = datetime.date(2026, 5, 1)
    resumen = resumen_ejecucion(proyecto, fecha_corte=fecha_corte)

    costo_planeado = Decimal("28000000.00") + Decimal("5000000.00")
    costo_ejecutado = Decimal("7000000.00") + Decimal("2000000.00")

    assert resumen["horas_planeadas"] == Decimal("400.00")
    assert resumen["horas_ejecutadas"] == Decimal("100.00")
    assert resumen["horas_pendientes_aprobacion"] == Decimal("20.00")  # solo lo ENVIADO
    assert resumen["costo_planeado"] == costo_planeado
    assert resumen["costo_ejecutado"] == costo_ejecutado
    assert resumen["pct_horas"] == pytest.approx(25.0)  # 100/400
    assert resumen["pct_dinero"] == pytest.approx(float(costo_ejecutado / costo_planeado) * 100)

    dias_totales_plan = (proyecto.fecha_fin_plan - proyecto.fecha_inicio_plan).days
    dias_transcurridos = (fecha_corte - proyecto.fecha_inicio_plan).days
    pct_tiempo_esperado = dias_transcurridos / dias_totales_plan * 100
    assert resumen["pct_tiempo"] == pytest.approx(pct_tiempo_esperado)

    avance = 30.0
    spi_esperado = avance / pct_tiempo_esperado
    assert resumen["spi"] == pytest.approx(spi_esperado)

    costo_planeado_segun_avance = (avance / 100) * float(costo_planeado)
    cpi_esperado = costo_planeado_segun_avance / float(costo_ejecutado)
    assert resumen["cpi"] == pytest.approx(cpi_esperado)

    costo_planeado_segun_avance_decimal = (
        Decimal("30.00") / Decimal("100")
    ) * costo_planeado
    assert resumen["desviacion_presupuestal"] == (
        costo_ejecutado - costo_planeado_segun_avance_decimal
    )


# --- Tablero de control (fase 10) --------------------------------------------


def test_resumen_global_cuadra_con_la_suma_de_resumen_ejecucion_por_proyecto():
    """docs/plan/fase-10 §10.1.5: los totales del tablero deben coincidir
    con la suma de los proyectos individuales — nunca una fórmula paralela
    que pueda desviarse de `resumen_ejecucion`."""
    fecha_corte = datetime.date(2026, 6, 1)
    proyecto_1 = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 12, 31)
    )
    proyecto_2 = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 12, 31)
    )
    AsignacionRecursoFactory(proyecto=proyecto_1, horas_planeadas=400, valor_hora_plan=70_000)
    AsignacionRecursoFactory(proyecto=proyecto_2, horas_planeadas=300, valor_hora_plan=50_000)
    RegistroEjecucionFactory(
        proyecto=proyecto_1,
        horas=100,
        valor_hora_aplicado=70_000,
        periodo_inicio=datetime.date(2026, 2, 1),
        periodo_fin=datetime.date(2026, 2, 1),
    )
    RegistroEjecucionFactory(
        proyecto=proyecto_2,
        horas=50,
        valor_hora_aplicado=50_000,
        periodo_inicio=datetime.date(2026, 2, 2),
        periodo_fin=datetime.date(2026, 2, 2),
    )

    proyectos = Proyecto.objects.filter(id__in=[proyecto_1.id, proyecto_2.id])
    global_ = resumen_global(proyectos)

    suma_horas_planeadas = sum(
        resumen_ejecucion(p, fecha_corte=fecha_corte)["horas_planeadas"]
        for p in (proyecto_1, proyecto_2)
    )
    suma_horas_ejecutadas = sum(
        resumen_ejecucion(p, fecha_corte=fecha_corte)["horas_ejecutadas"]
        for p in (proyecto_1, proyecto_2)
    )
    suma_costo_planeado = sum(
        resumen_ejecucion(p, fecha_corte=fecha_corte)["costo_planeado"]
        for p in (proyecto_1, proyecto_2)
    )
    suma_costo_ejecutado = sum(
        resumen_ejecucion(p, fecha_corte=fecha_corte)["costo_ejecutado"]
        for p in (proyecto_1, proyecto_2)
    )

    assert global_["horas_planeadas"] == suma_horas_planeadas
    assert global_["horas_ejecutadas"] == suma_horas_ejecutadas
    assert global_["costo_planeado"] == suma_costo_planeado
    assert global_["costo_ejecutado"] == suma_costo_ejecutado
    assert global_["total_proyectos"] == 2


def test_tabla_proyectos_coincide_con_resumen_ejecucion_fila_por_fila():
    """`tabla_proyectos` resuelve las métricas con subconsultas masivas en
    vez de `_metricas` por instancia; deben dar exactamente el mismo
    resultado que `resumen_ejecucion` para el mismo proyecto."""
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1),
        fecha_fin_plan=datetime.date(2026, 12, 31),
        avance_reportado=Decimal("30.00"),
    )
    AsignacionRecursoFactory(proyecto=proyecto, horas_planeadas=400, valor_hora_plan=70_000)
    RubroPresupuestoFactory(proyecto=proyecto, monto_planeado=5_000_000)
    RegistroEjecucionFactory(
        proyecto=proyecto,
        horas=100,
        valor_hora_aplicado=70_000,
        periodo_inicio=datetime.date(2026, 2, 1),
        periodo_fin=datetime.date(2026, 2, 1),
    )
    HitoFactory(proyecto=proyecto, estado="INCUMPLIDO")
    TareaFactory(proyecto=proyecto, estado="PENDIENTE", fecha_fin_plan=datetime.date(2026, 1, 1))

    esperado = resumen_ejecucion(proyecto, fecha_corte=timezone.localdate())
    filas = tabla_proyectos(Proyecto.objects.filter(id=proyecto.id))

    assert len(filas) == 1
    obtenido = filas[0]["resumen_ejecucion"]
    for clave in (
        "horas_planeadas",
        "horas_ejecutadas",
        "pct_horas",
        "costo_planeado",
        "costo_ejecutado",
        "pct_dinero",
        "spi",
        "cpi",
        "desviacion_presupuestal",
        "hitos_cumplidos",
        "hitos_incumplidos",
        "tareas_abiertas",
        "tareas_vencidas",
        "semaforo",
    ):
        assert obtenido[clave] == esperado[clave], clave


def test_tabla_proyectos_sin_asignaciones_ni_rubros_devuelve_null_no_cero():
    """docs/plan/fase-10 §10.1.5: un proyecto sin plan debe devolver sus
    indicadores en `None`, no en `0`, y no debe lanzar división por cero."""
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 12, 31)
    )

    filas = tabla_proyectos(Proyecto.objects.filter(id=proyecto.id))

    resumen = filas[0]["resumen_ejecucion"]
    assert resumen["pct_horas"] is None
    assert resumen["pct_dinero"] is None
    assert resumen["cpi"] is None
    assert resumen["horas_planeadas"] == Decimal("0")
    assert resumen["costo_planeado"] == Decimal("0")


def test_tabla_proyectos_resuelve_en_pocas_consultas_independiente_del_numero_de_proyectos(
    django_assert_max_num_queries,
):
    """docs/plan/fase-10 §10.1: resuelto con subconsultas correlacionadas,
    así que el número de consultas no depende de cuántos proyectos haya."""
    for _ in range(50):
        proyecto = ProyectoFactory()
        AsignacionRecursoFactory(proyecto=proyecto, horas_planeadas=100, valor_hora_plan=50_000)

    with django_assert_max_num_queries(5):
        filas = tabla_proyectos(Proyecto.objects.filter(activo=True))

    assert len(filas) == 50


def test_ejecucion_mensual_reparte_el_plan_igual_que_carga_recurso():
    """docs/plan/fase-10 §10.1.5: `ejecucion_mensual` (muchos proyectos) y
    `carga_recurso` (fase 06, un recurso) deben prorratear el mismo plan
    con el mismo resultado cuando solo hay una asignación en juego."""
    recurso = RecursoFactory(capacidad_horas_mes=160)
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 12, 31)
    )
    AsignacionRecursoFactory(
        proyecto=proyecto,
        recurso=recurso,
        fecha_desde=datetime.date(2026, 2, 1),
        fecha_hasta=datetime.date(2026, 4, 30),
        horas_planeadas=900,
    )

    desde, hasta = datetime.date(2026, 2, 1), datetime.date(2026, 4, 30)
    carga = carga_recurso(recurso, desde, hasta)
    serie = ejecucion_mensual(Proyecto.objects.filter(id=proyecto.id), desde, hasta)

    assert len(carga) == len(serie) == 3
    for mes_carga, mes_serie in zip(carga, serie, strict=True):
        assert mes_serie["horas_plan"] == mes_carga["horas_planeadas"]
