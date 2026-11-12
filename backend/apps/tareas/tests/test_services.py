import datetime
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.accounts.tests.factories import UsuarioFactory
from apps.core.choices import EstadoProyecto, EstadoTarea, TipoDependencia
from apps.core.exceptions import ErrorConflicto
from apps.proyectos.tests.factories import ProyectoFactory
from apps.tareas.services import (
    cambiar_estado_tarea,
    detectar_ciclo,
    fechas_sugeridas,
    generar_codigo_tarea,
    marcar_creacion_durante_ejecucion,
    recalcular_avance,
    validar_jerarquia,
)
from apps.tareas.tests.factories import DependenciaTareaFactory, TareaFactory

pytestmark = pytest.mark.django_db


# --- generar_codigo_tarea ----------------------------------------------------


def test_generar_codigo_tarea_es_secuencial_por_proyecto():
    proyecto = ProyectoFactory(codigo="PRY-2026-050")
    TareaFactory(proyecto=proyecto, codigo=generar_codigo_tarea(proyecto))
    TareaFactory(proyecto=proyecto, codigo=generar_codigo_tarea(proyecto))

    assert generar_codigo_tarea(proyecto) == "PRY-2026-050-T003"


def test_generar_codigo_tarea_no_colisiona_entre_proyectos_distintos():
    proyecto_1 = ProyectoFactory(codigo="PRY-2026-051")
    proyecto_2 = ProyectoFactory(codigo="PRY-2026-052")

    assert generar_codigo_tarea(proyecto_1) == "PRY-2026-051-T001"
    assert generar_codigo_tarea(proyecto_2) == "PRY-2026-052-T001"


# --- validar_jerarquia --------------------------------------------------------


def test_validar_jerarquia_rechaza_padre_de_otro_proyecto():
    proyecto_1 = ProyectoFactory()
    proyecto_2 = ProyectoFactory()
    padre = TareaFactory(proyecto=proyecto_2)
    hija = TareaFactory(proyecto=proyecto_1)

    with pytest.raises(ValidationError):
        validar_jerarquia(hija, padre)


def test_validar_jerarquia_rechaza_ser_su_propio_ancestro():
    proyecto = ProyectoFactory()
    abuela = TareaFactory(proyecto=proyecto)
    madre = TareaFactory(proyecto=proyecto, tarea_padre=abuela)

    with pytest.raises(ValidationError):
        validar_jerarquia(abuela, madre)


def test_validar_jerarquia_admite_tres_niveles_y_rechaza_el_cuarto():
    proyecto = ProyectoFactory()
    nivel_1 = TareaFactory(proyecto=proyecto)
    nivel_2 = TareaFactory(proyecto=proyecto, tarea_padre=nivel_1)
    nivel_3 = TareaFactory(proyecto=proyecto, tarea_padre=nivel_2)

    nivel_4 = TareaFactory.build(proyecto=proyecto)
    with pytest.raises(ValidationError):
        validar_jerarquia(nivel_4, nivel_3)

    # El propio nivel_3 (padre=nivel_2, que es nivel 2) sí puede recibir hijas.
    otra_nivel_4 = TareaFactory.build(proyecto=proyecto)
    validar_jerarquia(otra_nivel_4, nivel_2)


# --- detectar_ciclo ------------------------------------------------------------


def test_detectar_ciclo_rechaza_con_la_ruta_completa():
    proyecto = ProyectoFactory()
    t001 = TareaFactory(proyecto=proyecto, codigo=f"{proyecto.codigo}-T001")
    t004 = TareaFactory(proyecto=proyecto, codigo=f"{proyecto.codigo}-T004")
    t009 = TareaFactory(proyecto=proyecto, codigo=f"{proyecto.codigo}-T009")
    DependenciaTareaFactory(tarea_origen=t001, tarea_destino=t004, tipo=TipoDependencia.FI)
    DependenciaTareaFactory(tarea_origen=t004, tarea_destino=t009, tipo=TipoDependencia.FI)

    with pytest.raises(ErrorConflicto) as excinfo:
        detectar_ciclo(t009, t001)

    assert excinfo.value.detail["ciclo"] == [t009.codigo, t001.codigo, t004.codigo, t009.codigo]


def test_detectar_ciclo_permite_dependencias_sin_ciclo():
    proyecto = ProyectoFactory()
    origen = TareaFactory(proyecto=proyecto)
    destino = TareaFactory(proyecto=proyecto)

    detectar_ciclo(origen, destino)  # no lanza


def test_detectar_ciclo_rechaza_autodependencia():
    tarea = TareaFactory()
    with pytest.raises(ErrorConflicto):
        detectar_ciclo(tarea, tarea)


# --- recalcular_avance --------------------------------------------------------


def test_recalcular_avance_promedia_ponderado_por_horas_estimadas():
    proyecto = ProyectoFactory()
    padre = TareaFactory(proyecto=proyecto, horas_estimadas=100, avance=0)
    TareaFactory(proyecto=proyecto, tarea_padre=padre, horas_estimadas=30, avance=100)
    TareaFactory(proyecto=proyecto, tarea_padre=padre, horas_estimadas=10, avance=0)

    recalcular_avance(padre)
    padre.refresh_from_db()

    assert padre.avance == Decimal("75.00")


def test_recalcular_avance_con_horas_estimadas_en_cero_usa_promedio_simple():
    proyecto = ProyectoFactory()
    padre = TareaFactory(proyecto=proyecto, horas_estimadas=100, avance=0)
    TareaFactory(proyecto=proyecto, tarea_padre=padre, horas_estimadas=0, avance=100)
    TareaFactory(proyecto=proyecto, tarea_padre=padre, horas_estimadas=0, avance=0)

    recalcular_avance(padre)
    padre.refresh_from_db()

    assert padre.avance == Decimal("50.00")


def test_recalcular_avance_sube_hasta_la_raiz():
    proyecto = ProyectoFactory()
    abuela = TareaFactory(proyecto=proyecto, horas_estimadas=100, avance=0)
    madre = TareaFactory(proyecto=proyecto, tarea_padre=abuela, horas_estimadas=50, avance=0)
    TareaFactory(proyecto=proyecto, tarea_padre=madre, horas_estimadas=50, avance=100)

    recalcular_avance(madre)

    abuela.refresh_from_db()
    madre.refresh_from_db()
    assert madre.avance == Decimal("100.00")
    assert abuela.avance == Decimal("100.00")


def test_recalcular_avance_sin_subtareas_no_hace_nada():
    tarea = TareaFactory(avance=42)
    recalcular_avance(tarea)
    tarea.refresh_from_db()
    assert tarea.avance == Decimal("42.00")


# --- marcar_creacion_durante_ejecucion -----------------------------------------


def test_marcar_creacion_durante_ejecucion_exige_motivo_si_proyecto_en_ejecucion():
    proyecto = ProyectoFactory(estado=EstadoProyecto.EJECUCION)
    tarea = TareaFactory.build(proyecto=proyecto, motivo_creacion="")

    with pytest.raises(ValidationError):
        marcar_creacion_durante_ejecucion(tarea)


def test_marcar_creacion_durante_ejecucion_marca_la_bandera_con_motivo():
    proyecto = ProyectoFactory(estado=EstadoProyecto.EJECUCION)
    tarea = TareaFactory.build(
        proyecto=proyecto, motivo_creacion="Cambio solicitado por el cliente"
    )

    marcar_creacion_durante_ejecucion(tarea)

    assert tarea.creada_durante_ejecucion is True


def test_marcar_creacion_durante_ejecucion_no_aplica_fuera_de_ejecucion():
    proyecto = ProyectoFactory(estado=EstadoProyecto.PLANEACION)
    tarea = TareaFactory.build(proyecto=proyecto, motivo_creacion="")

    marcar_creacion_durante_ejecucion(tarea)

    assert tarea.creada_durante_ejecucion is False


# --- cambiar_estado_tarea -------------------------------------------------------


def test_cambiar_estado_a_en_progreso_sin_fecha_la_pone_hoy():
    tarea = TareaFactory(estado=EstadoTarea.PENDIENTE, fecha_inicio_real=None)
    usuario = UsuarioFactory()

    cambiar_estado_tarea(tarea, EstadoTarea.EN_PROGRESO, usuario)
    tarea.refresh_from_db()

    assert tarea.estado == EstadoTarea.EN_PROGRESO
    assert tarea.fecha_inicio_real == datetime.date.today()


def test_cambiar_estado_a_completada_sin_fecha_la_pone_hoy_y_fija_avance_100():
    tarea = TareaFactory(estado=EstadoTarea.EN_PROGRESO, fecha_fin_real=None, avance=40)
    usuario = UsuarioFactory()

    cambiar_estado_tarea(tarea, EstadoTarea.COMPLETADA, usuario)
    tarea.refresh_from_db()

    assert tarea.estado == EstadoTarea.COMPLETADA
    assert tarea.fecha_fin_real == datetime.date.today()
    assert tarea.avance == Decimal("100.00")


def test_cambiar_estado_a_completada_cierra_el_compromiso_vinculado():
    from apps.core.choices import EstadoCompromiso
    from apps.seguimiento.tests.factories import CompromisoSeguimientoFactory

    tarea = TareaFactory(estado=EstadoTarea.EN_PROGRESO, fecha_fin_real=None)
    compromiso = CompromisoSeguimientoFactory(
        tarea=tarea, estado=EstadoCompromiso.ABIERTO
    )
    usuario = UsuarioFactory()

    cambiar_estado_tarea(tarea, EstadoTarea.COMPLETADA, usuario)
    tarea.refresh_from_db()
    compromiso.refresh_from_db()

    assert compromiso.estado == EstadoCompromiso.CUMPLIDO
    assert compromiso.fecha_cumplimiento == tarea.fecha_fin_real


def test_cambiar_estado_a_completada_con_subtarea_abierta_da_409():
    padre = TareaFactory(estado=EstadoTarea.EN_PROGRESO)
    TareaFactory(tarea_padre=padre, proyecto=padre.proyecto, estado=EstadoTarea.EN_PROGRESO)
    usuario = UsuarioFactory()

    with pytest.raises(ErrorConflicto):
        cambiar_estado_tarea(padre, EstadoTarea.COMPLETADA, usuario)


def test_cambiar_estado_a_completada_con_subtarea_cancelada_si_permite():
    padre = TareaFactory(estado=EstadoTarea.EN_PROGRESO)
    TareaFactory(tarea_padre=padre, proyecto=padre.proyecto, estado=EstadoTarea.CANCELADA)
    usuario = UsuarioFactory()

    cambiar_estado_tarea(padre, EstadoTarea.COMPLETADA, usuario)
    padre.refresh_from_db()

    assert padre.estado == EstadoTarea.COMPLETADA


def test_cambiar_estado_a_bloqueada_sin_nota_falla():
    tarea = TareaFactory(estado=EstadoTarea.EN_PROGRESO)
    usuario = UsuarioFactory()

    with pytest.raises(ValidationError):
        cambiar_estado_tarea(tarea, EstadoTarea.BLOQUEADA, usuario)


def test_cambiar_estado_a_bloqueada_con_nota_escribe_bitacora():
    from apps.expediente.models import EntradaBitacora

    tarea = TareaFactory(estado=EstadoTarea.EN_PROGRESO)
    usuario = UsuarioFactory()

    cambiar_estado_tarea(tarea, EstadoTarea.BLOQUEADA, usuario, nota="Esperando insumo del cliente")
    tarea.refresh_from_db()

    assert tarea.estado == EstadoTarea.BLOQUEADA
    entrada = EntradaBitacora.objects.filter(entidad="Tarea", entidad_id=tarea.id).latest(
        "creado_en"
    )
    assert entrada.datos_despues["nota"] == "Esperando insumo del cliente"


def test_cambiar_estado_recalcula_avance_del_padre():
    padre = TareaFactory(horas_estimadas=100, avance=0)
    hija = TareaFactory(tarea_padre=padre, proyecto=padre.proyecto, horas_estimadas=100, avance=0)
    usuario = UsuarioFactory()

    cambiar_estado_tarea(hija, EstadoTarea.COMPLETADA, usuario)
    padre.refresh_from_db()

    assert padre.avance == Decimal("100.00")


# --- fechas_sugeridas -----------------------------------------------------------


def test_fechas_sugeridas_sin_dependencias_devuelve_none():
    tarea = TareaFactory()
    resultado = fechas_sugeridas(tarea)
    assert resultado == {"fecha_inicio_sugerida": None, "fecha_fin_sugerida": None}


def test_fechas_sugeridas_toma_la_mas_tardia_de_las_dependencias_fi():
    proyecto = ProyectoFactory()
    destino = TareaFactory(
        proyecto=proyecto,
        fecha_inicio_plan=datetime.date(2026, 1, 1),
        fecha_fin_plan=datetime.date(2026, 1, 10),
    )
    predecesora_1 = TareaFactory(proyecto=proyecto, fecha_fin_plan=datetime.date(2026, 2, 1))
    predecesora_2 = TareaFactory(proyecto=proyecto, fecha_fin_plan=datetime.date(2026, 3, 1))
    DependenciaTareaFactory(
        tarea_origen=predecesora_1, tarea_destino=destino, tipo=TipoDependencia.FI, dias_desfase=0
    )
    DependenciaTareaFactory(
        tarea_origen=predecesora_2, tarea_destino=destino, tipo=TipoDependencia.FI, dias_desfase=2
    )

    resultado = fechas_sugeridas(destino)

    # predecesora_2 termina el 2026-03-01; +1 día de convención FI + 2 de desfase.
    assert resultado["fecha_inicio_sugerida"] == datetime.date(2026, 3, 4)
    # Duración original de la tarea: 9 días.
    assert resultado["fecha_fin_sugerida"] == datetime.date(2026, 3, 13)


def test_fechas_sugeridas_ignora_dependencias_que_no_son_fi():
    proyecto = ProyectoFactory()
    destino = TareaFactory(proyecto=proyecto)
    predecesora = TareaFactory(proyecto=proyecto, fecha_fin_plan=datetime.date(2026, 5, 1))
    DependenciaTareaFactory(
        tarea_origen=predecesora, tarea_destino=destino, tipo=TipoDependencia.II
    )

    resultado = fechas_sugeridas(destino)

    assert resultado["fecha_inicio_sugerida"] is None
