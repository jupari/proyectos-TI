import datetime

import pytest

from apps.core.choices import EstadoProyecto, EstadoTarea
from apps.core.exceptions import ErrorConflicto, ErrorReglaNegocio
from apps.proyectos.services import (
    cambiar_estado,
    generar_codigo_proyecto,
    validar_pesos_fases,
    validar_presupuesto,
    validar_transicion,
)
from apps.recursos.tests.factories import AsignacionRecursoFactory
from apps.tareas.tests.factories import TareaFactory

from .factories import FaseProyectoFactory, ProyectoFactory, RubroPresupuestoFactory

pytestmark = pytest.mark.django_db


# --- validar_transicion / cambiar_estado ------------------------------------


def test_transicion_valida_no_lanza():
    proyecto = ProyectoFactory(estado=EstadoProyecto.BORRADOR)
    validar_transicion(proyecto, EstadoProyecto.PLANEACION)


def test_transicion_invalida_lanza_conflicto_con_transiciones_validas():
    proyecto = ProyectoFactory(estado=EstadoProyecto.BORRADOR)

    with pytest.raises(ErrorConflicto) as excinfo:
        validar_transicion(proyecto, EstadoProyecto.CERRADO)

    detalle = excinfo.value.detail
    assert "BORRADOR" in detalle["estado"][0]
    assert "CERRADO" in detalle["estado"][0]
    assert set(detalle["transiciones_validas"]) == {"PLANEACION", "CANCELADO"}


def test_pasar_a_ejecucion_sin_fecha_inicio_real_falla():
    proyecto = ProyectoFactory(estado=EstadoProyecto.PLANEACION, fecha_inicio_real=None)

    with pytest.raises(ErrorReglaNegocio) as excinfo:
        cambiar_estado(proyecto, EstadoProyecto.EJECUCION, "Arranca", usuario=None)

    assert "fecha_inicio_real" in excinfo.value.detail


def test_pasar_a_ejecucion_sin_asignaciones_falla():
    proyecto = ProyectoFactory(
        estado=EstadoProyecto.PLANEACION, fecha_inicio_real=datetime.date(2026, 1, 1)
    )

    with pytest.raises(ErrorReglaNegocio) as excinfo:
        cambiar_estado(proyecto, EstadoProyecto.EJECUCION, "Arranca", usuario=None)

    assert "asignaciones" in excinfo.value.detail


def test_pasar_a_ejecucion_con_fecha_y_asignacion_funciona():
    proyecto = ProyectoFactory(
        estado=EstadoProyecto.PLANEACION, fecha_inicio_real=datetime.date(2026, 1, 1)
    )
    AsignacionRecursoFactory(proyecto=proyecto)

    cambiar_estado(proyecto, EstadoProyecto.EJECUCION, "Arranca", usuario=None)

    proyecto.refresh_from_db()
    assert proyecto.estado == EstadoProyecto.EJECUCION


def test_cerrar_con_tareas_en_progreso_falla():
    proyecto = ProyectoFactory(
        estado=EstadoProyecto.EJECUCION, fecha_fin_real=datetime.date(2026, 12, 31)
    )
    TareaFactory(proyecto=proyecto, estado=EstadoTarea.EN_PROGRESO)

    with pytest.raises(ErrorReglaNegocio) as excinfo:
        cambiar_estado(proyecto, EstadoProyecto.CERRADO, "Cierre", usuario=None)

    assert "tareas" in excinfo.value.detail


def test_cerrar_sin_tareas_en_progreso_funciona():
    proyecto = ProyectoFactory(
        estado=EstadoProyecto.EJECUCION, fecha_fin_real=datetime.date(2026, 12, 31)
    )
    TareaFactory(proyecto=proyecto, estado=EstadoTarea.COMPLETADA)

    cambiar_estado(proyecto, EstadoProyecto.CERRADO, "Cierre", usuario=None)

    proyecto.refresh_from_db()
    assert proyecto.estado == EstadoProyecto.CERRADO


# --- validar_pesos_fases -----------------------------------------------------


def test_validar_pesos_fases_exactamente_100_no_lanza():
    proyecto = ProyectoFactory()
    FaseProyectoFactory(proyecto=proyecto, orden=1, peso=60)
    FaseProyectoFactory(proyecto=proyecto, orden=2, peso=40)

    validar_pesos_fases(proyecto)


def test_validar_pesos_fases_faltante_indica_cuanto_falta():
    proyecto = ProyectoFactory()
    FaseProyectoFactory(proyecto=proyecto, orden=1, peso=60)

    with pytest.raises(ErrorReglaNegocio) as excinfo:
        validar_pesos_fases(proyecto)

    assert "40" in excinfo.value.detail["peso"][0]


def test_validar_pesos_fases_excedente_indica_cuanto_sobra():
    proyecto = ProyectoFactory()
    FaseProyectoFactory(proyecto=proyecto, orden=1, peso=70)
    FaseProyectoFactory(proyecto=proyecto, orden=2, peso=50)

    with pytest.raises(ErrorReglaNegocio) as excinfo:
        validar_pesos_fases(proyecto)

    assert "20" in excinfo.value.detail["peso"][0]


# --- validar_presupuesto -----------------------------------------------------


def test_validar_presupuesto_suficiente_no_lanza():
    proyecto = ProyectoFactory(presupuesto_dinero=10_000_000)
    RubroPresupuestoFactory(proyecto=proyecto, monto_planeado=5_000_000)

    validar_presupuesto(proyecto)


def test_validar_presupuesto_insuficiente_lanza_con_mensaje_claro():
    proyecto = ProyectoFactory(presupuesto_dinero=1_000_000)
    RubroPresupuestoFactory(proyecto=proyecto, monto_planeado=5_000_000)

    with pytest.raises(ErrorReglaNegocio) as excinfo:
        validar_presupuesto(proyecto)

    assert "presupuesto_dinero" in excinfo.value.detail


# --- generar_codigo_proyecto -------------------------------------------------


def test_generar_codigo_proyecto_primero_del_anio():
    anio = datetime.date.today().year
    assert generar_codigo_proyecto() == f"PRY-{anio}-001"


def test_generar_codigo_proyecto_incrementa_secuencia():
    anio = datetime.date.today().year
    ProyectoFactory(codigo=f"PRY-{anio}-001")
    ProyectoFactory(codigo=f"PRY-{anio}-002")

    assert generar_codigo_proyecto() == f"PRY-{anio}-003"
