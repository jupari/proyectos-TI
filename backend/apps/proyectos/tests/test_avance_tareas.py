from decimal import Decimal

import pytest

from apps.core.choices import EstadoTarea
from apps.proyectos.models import Proyecto
from apps.proyectos.services import (
    calcular_avance_tareas,
    pausar_recalculo_avance,
    recalcular_avance_proyecto,
)
from apps.proyectos.tests.factories import ProyectoFactory
from apps.seguimiento.services import precargar
from apps.tareas.tests.factories import TareaFactory

pytestmark = pytest.mark.django_db


def test_sin_tareas_no_hay_avance_calculado():
    assert calcular_avance_tareas(ProyectoFactory()) is None


def test_avance_es_el_promedio_ponderado_por_horas_de_las_tareas_raiz():
    proyecto = ProyectoFactory()
    TareaFactory(proyecto=proyecto, horas_estimadas=30, avance=100)
    TareaFactory(proyecto=proyecto, horas_estimadas=10, avance=0)

    assert calcular_avance_tareas(proyecto) == Decimal("75.00")


def test_las_canceladas_y_las_subtareas_no_cuentan_como_raiz():
    proyecto = ProyectoFactory()
    historia = TareaFactory(proyecto=proyecto, horas_estimadas=10, avance=50)
    TareaFactory(proyecto=proyecto, tarea_padre=historia, horas_estimadas=10, avance=50)
    TareaFactory(
        proyecto=proyecto, horas_estimadas=100, avance=0, estado=EstadoTarea.CANCELADA
    )

    assert calcular_avance_tareas(proyecto) == Decimal("50.00")


def test_sin_horas_estimadas_el_promedio_es_simple():
    proyecto = ProyectoFactory()
    TareaFactory.create_batch(2, proyecto=proyecto, horas_estimadas=0, avance=100)
    TareaFactory(proyecto=proyecto, horas_estimadas=0, avance=0)

    assert calcular_avance_tareas(proyecto) == Decimal("66.67")


def test_guardar_una_tarea_actualiza_avance_tareas_pero_no_el_reportado():
    proyecto = ProyectoFactory(avance_reportado=40)

    TareaFactory(proyecto=proyecto, horas_estimadas=10, avance=100)

    proyecto.refresh_from_db()
    assert proyecto.avance_tareas == Decimal("100.00")
    assert proyecto.avance_reportado == Decimal("40.00")


def test_con_avance_desde_tareas_el_reportado_sigue_a_las_tareas():
    proyecto = ProyectoFactory(avance_reportado=40, avance_desde_tareas=True)

    tarea = TareaFactory(proyecto=proyecto, horas_estimadas=10, avance=20)
    proyecto.refresh_from_db()
    assert proyecto.avance_reportado == Decimal("20.00")

    tarea.avance = 80
    tarea.save()
    proyecto.refresh_from_db()
    assert proyecto.avance_reportado == Decimal("80.00")


def test_borrar_una_tarea_recalcula():
    proyecto = ProyectoFactory()
    TareaFactory(proyecto=proyecto, horas_estimadas=10, avance=100)
    pendiente = TareaFactory(proyecto=proyecto, horas_estimadas=10, avance=0)
    proyecto.refresh_from_db()
    assert proyecto.avance_tareas == Decimal("50.00")

    pendiente.delete()

    proyecto.refresh_from_db()
    assert proyecto.avance_tareas == Decimal("100.00")


def test_pausar_evita_recalcular_en_cada_guardado_y_forzar_lo_hace_una_vez():
    proyecto = ProyectoFactory()

    with pausar_recalculo_avance():
        TareaFactory(proyecto=proyecto, horas_estimadas=10, avance=60)
        proyecto.refresh_from_db()
        assert proyecto.avance_tareas is None
        recalcular_avance_proyecto(proyecto, forzar=True)

    assert Proyecto.objects.get(pk=proyecto.pk).avance_tareas == Decimal("60.00")


def test_el_seguimiento_propone_el_avance_de_las_tareas():
    proyecto = ProyectoFactory(avance_reportado=10)
    TareaFactory(proyecto=proyecto, horas_estimadas=10, avance=55)
    proyecto.refresh_from_db()

    datos = precargar(proyecto, "MENSUAL", proyecto.fecha_inicio_plan)

    assert datos["avance_reportado"] == Decimal("55.00")
