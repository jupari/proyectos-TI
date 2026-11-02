import datetime
from decimal import Decimal

import pytest

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
