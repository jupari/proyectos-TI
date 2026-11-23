import datetime

import pytest
from rest_framework.test import APIClient

from apps.core.choices import EstadoSprint, EstadoTarea
from apps.proyectos.tests.factories import ProyectoFactory
from apps.recursos.tests.factories import RecursoFactory
from apps.tablero.sprints import burndown_sprint, metricas_sprint, mi_trabajo, sprints_del_proyecto
from apps.tareas.models import Sprint
from apps.tareas.tests.factories import TareaFactory
from conftest import crear_usuario_con_rol

pytestmark = pytest.mark.django_db

INICIO = datetime.date(2026, 3, 2)
FIN = datetime.date(2026, 3, 6)  # lunes a viernes: 5 días


def _sprint(proyecto, id_jira=1, estado=EstadoSprint.CERRADO, **extra):
    return Sprint.objects.create(
        proyecto=proyecto,
        id_jira=id_jira,
        nombre=f"Sprint {id_jira}",
        estado=estado,
        fecha_inicio=extra.pop("fecha_inicio", INICIO),
        fecha_fin=extra.pop("fecha_fin", FIN),
        **extra,
    )


def _tarea(proyecto, sprint, horas, estado=EstadoTarea.PENDIENTE, cierre=None, **extra):
    return TareaFactory(
        proyecto=proyecto,
        sprint=sprint,
        horas_estimadas=horas,
        estado=estado,
        fecha_fin_real=cierre,
        **extra,
    )


def test_las_metricas_cuentan_solo_tareas_hoja_para_no_duplicar_horas():
    proyecto = ProyectoFactory()
    sprint = _sprint(proyecto)
    historia = _tarea(proyecto, sprint, 8)
    _tarea(proyecto, sprint, 6, EstadoTarea.COMPLETADA, tarea_padre=historia)
    _tarea(proyecto, sprint, 4, tarea_padre=historia)
    _tarea(proyecto, sprint, 100, EstadoTarea.CANCELADA)  # no cuenta

    metricas = metricas_sprint(sprint)

    assert metricas["tareas_total"] == 2  # las dos subtareas; la historia no cuenta
    assert metricas["horas_comprometidas"] == 10.0
    assert metricas["horas_completadas"] == 6.0
    assert metricas["porcentaje_completado"] == 60.0


def test_velocidad_promedio_usa_los_ultimos_sprints_cerrados():
    proyecto = ProyectoFactory()
    for numero, horas in enumerate([10, 20, 30, 40], start=1):
        sprint = _sprint(
            proyecto,
            numero,
            fecha_inicio=INICIO + datetime.timedelta(weeks=numero),
            fecha_fin=FIN + datetime.timedelta(weeks=numero),
        )
        _tarea(proyecto, sprint, horas, EstadoTarea.COMPLETADA)
    inicio_activo = INICIO + datetime.timedelta(weeks=9)
    activo = _sprint(proyecto, 9, EstadoSprint.ACTIVO, fecha_inicio=inicio_activo)
    _tarea(proyecto, activo, 50, EstadoTarea.COMPLETADA)  # no entra: sigue abierto

    resultado = sprints_del_proyecto(proyecto)

    assert resultado["sprints_en_velocidad"] == 3
    assert resultado["velocidad_promedio"] == 30.0  # (20 + 30 + 40) / 3
    assert resultado["sprints"][0]["id"] == str(activo.id)  # el más reciente primero


def test_burndown_de_sprint_cerrado_baja_con_cada_tarea_completada():
    proyecto = ProyectoFactory()
    sprint = _sprint(proyecto)
    _tarea(proyecto, sprint, 10, EstadoTarea.COMPLETADA, cierre=datetime.date(2026, 3, 3))
    _tarea(proyecto, sprint, 10, EstadoTarea.COMPLETADA, cierre=datetime.date(2026, 3, 5))
    _tarea(proyecto, sprint, 20)  # nunca se cerró

    datos = burndown_sprint(sprint)

    assert datos["disponible"] is True
    assert len(datos["fechas"]) == 5
    assert datos["ideal"] == [40.0, 30.0, 20.0, 10.0, 0.0]
    assert datos["real"] == [40.0, 30.0, 30.0, 20.0, 20.0]


def test_burndown_de_sprint_activo_no_dibuja_los_dias_futuros():
    proyecto = ProyectoFactory()
    sprint = _sprint(proyecto, estado=EstadoSprint.ACTIVO)
    _tarea(proyecto, sprint, 10, EstadoTarea.COMPLETADA, cierre=datetime.date(2026, 3, 2))

    datos = burndown_sprint(sprint, hoy=datetime.date(2026, 3, 4))

    assert datos["real"] == [0.0, 0.0, 0.0, None, None]


def test_burndown_sin_fechas_avisa_en_vez_de_fallar():
    proyecto = ProyectoFactory()
    sprint = _sprint(proyecto, fecha_inicio=None, fecha_fin=None)
    sprint.fecha_inicio = sprint.fecha_fin = None
    sprint.save()

    datos = burndown_sprint(sprint)

    assert datos["disponible"] is False
    assert "fechas" in datos["motivo"]


def test_mi_trabajo_trae_las_abiertas_del_recurso_con_el_sprint_activo_primero(roles):
    usuario = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=usuario)
    proyecto = ProyectoFactory()
    cerrado = _sprint(proyecto, 1)
    activo = _sprint(proyecto, 2, EstadoSprint.ACTIVO)
    _tarea(proyecto, cerrado, 5, responsable=recurso, fecha_fin_plan=datetime.date(2026, 1, 10))
    _tarea(proyecto, activo, 5, responsable=recurso, fecha_fin_plan=datetime.date(2026, 12, 31))
    _tarea(proyecto, activo, 5, EstadoTarea.COMPLETADA, responsable=recurso)  # no es abierta
    _tarea(proyecto, activo, 5, responsable=RecursoFactory())  # de otra persona

    datos = mi_trabajo(usuario, hoy=datetime.date(2026, 3, 1))

    assert datos["recurso"]["id"] == str(recurso.id)
    assert [t["sprint_nombre"] for t in datos["tareas"]] == ["Sprint 2", "Sprint 1"]
    assert datos["tareas"][0]["sprint_activo"] is True
    assert datos["resumen"]["total"] == 2
    assert datos["resumen"]["vencidas"] == 1


def test_mi_trabajo_sin_recurso_explica_por_que_esta_vacio(roles):
    usuario = crear_usuario_con_rol("CONSULTA")

    datos = mi_trabajo(usuario)

    assert datos["recurso"] is None
    assert datos["tareas"] == []
    assert "recurso" in datos["mensaje"]


def test_api_respeta_el_alcance_por_rol_en_sprints_y_burndown(roles):
    lider = crear_usuario_con_rol("LIDER")
    propio = ProyectoFactory(gerente=lider)
    ajeno = ProyectoFactory(gerente=crear_usuario_con_rol("LIDER"))
    sprint_propio = _sprint(propio, 1)
    sprint_ajeno = _sprint(ajeno, 1)
    cliente = APIClient()
    cliente.force_authenticate(lider)

    assert cliente.get(f"/api/v1/tablero/sprints/?proyecto={propio.id}").status_code == 200
    assert cliente.get(f"/api/v1/tablero/sprints/?proyecto={ajeno.id}").status_code == 404
    assert cliente.get(f"/api/v1/tablero/sprints/{sprint_propio.id}/burndown/").status_code == 200
    assert cliente.get(f"/api/v1/tablero/sprints/{sprint_ajeno.id}/burndown/").status_code == 404
    assert cliente.get("/api/v1/tablero/sprints/").status_code == 400
    assert cliente.get("/api/v1/tablero/mi-trabajo/").status_code == 200
