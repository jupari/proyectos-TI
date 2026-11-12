"""fase 11 §11.1.4: `verificar_consistencia` debe no reportar diferencias
tras `seed_demo`, y debe detectar una diferencia real cuando algo escribe un
campo derivado por fuera de los caminos normales (`aprobar`/`rechazar`/
`reabrir`/`save()`)."""

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.ejecucion.tests.factories import GastoEjecutadoFactory, RegistroEjecucionFactory
from apps.proyectos.tests.factories import RubroPresupuestoFactory
from apps.recursos.tests.factories import AsignacionRecursoFactory
from apps.tareas.models import Tarea
from apps.tareas.tests.factories import TareaFactory

pytestmark = pytest.mark.django_db


def test_verificar_consistencia_sin_diferencias_tras_seed_demo():
    call_command("seed_demo")
    call_command("verificar_consistencia")  # no debe lanzar CommandError


def test_verificar_consistencia_detecta_tarea_desalineada():
    tarea = TareaFactory(horas_estimadas=40)
    RegistroEjecucionFactory(
        tarea=tarea, proyecto=tarea.proyecto, horas=8, estado_aprobacion="APROBADO"
    )
    # Se desalinea a mano, por fuera de `recalcular_tarea`.
    Tarea.objects.filter(pk=tarea.pk).update(horas_ejecutadas=Decimal("999.00"))

    with pytest.raises(CommandError, match="diferencia"):
        call_command("verificar_consistencia")


def test_verificar_consistencia_detecta_rubro_desalineado():
    rubro = RubroPresupuestoFactory(monto_planeado=1_000_000)
    GastoEjecutadoFactory(
        rubro=rubro, proyecto=rubro.proyecto, monto=200_000, estado_aprobacion="APROBADO"
    )
    rubro.monto_ejecutado = Decimal("999999.00")
    rubro.save(update_fields=["monto_ejecutado"])

    with pytest.raises(CommandError, match="diferencia"):
        call_command("verificar_consistencia")


def test_verificar_consistencia_detecta_asignacion_desalineada():
    asignacion = AsignacionRecursoFactory(horas_planeadas=100, valor_hora_plan=50_000)
    type(asignacion).objects.filter(pk=asignacion.pk).update(costo_planeado=Decimal("1.00"))

    with pytest.raises(CommandError, match="diferencia"):
        call_command("verificar_consistencia")
