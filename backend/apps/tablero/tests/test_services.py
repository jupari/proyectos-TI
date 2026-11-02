import datetime
from decimal import Decimal

import pytest

from apps.core.choices import EstadoAprobacion
from apps.ejecucion.tests.factories import GastoEjecutadoFactory, RegistroEjecucionFactory
from apps.proyectos.tests.factories import ProyectoFactory, RubroPresupuestoFactory
from apps.recursos.tests.factories import AsignacionRecursoFactory

from ..services import resumen_ejecucion

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
