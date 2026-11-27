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


def test_admin_ve_las_tareas_de_todo_el_equipo_con_su_responsable(roles):
    admin = crear_usuario_con_rol("ADMIN")  # sin recurso propio
    ana = RecursoFactory(nombre="Ana")
    luis = RecursoFactory(nombre="Luis")
    proyecto = ProyectoFactory()
    sprint = _sprint(proyecto, 1, EstadoSprint.ACTIVO)
    _tarea(proyecto, sprint, 5, responsable=ana)
    _tarea(proyecto, sprint, 5, responsable=ana)
    _tarea(proyecto, sprint, 5, responsable=luis)
    _tarea(proyecto, sprint, 5)  # sin asignar
    _tarea(proyecto, sprint, 5, EstadoTarea.COMPLETADA, responsable=ana)  # ya cerrada

    datos = mi_trabajo(admin)

    assert datos["alcance"] == "equipo"
    assert datos["resumen"]["total"] == 4
    assert {t["responsable_nombre"] for t in datos["tareas"]} == {"Ana", "Luis", None}
    por_nombre = {r["nombre"]: r["total"] for r in datos["responsables"]}
    assert por_nombre == {"Ana": 2, "Luis": 1, "Sin asignar": 1}
    assert datos["responsables"][-1]["id"] is None  # «Sin asignar» al final


def test_quien_no_es_admin_solo_ve_lo_suyo_aunque_haya_mas_tareas(roles):
    usuario = crear_usuario_con_rol("LIDER")
    propio = RecursoFactory(usuario=usuario)
    proyecto = ProyectoFactory()
    sprint = _sprint(proyecto, 1, EstadoSprint.ACTIVO)
    _tarea(proyecto, sprint, 5, responsable=propio)
    _tarea(proyecto, sprint, 5, responsable=RecursoFactory())
    _tarea(proyecto, sprint, 5)

    datos = mi_trabajo(usuario)

    assert datos["alcance"] == "personal"
    assert datos["resumen"]["total"] == 1
    assert datos["responsables"] == []


def _abrir_excel(respuesta):
    import io

    from openpyxl import load_workbook

    return load_workbook(io.BytesIO(respuesta.content))


def test_exportar_excel_trae_tareas_con_horas_y_resumen_por_responsable(roles):
    admin = crear_usuario_con_rol("ADMIN")
    proyecto = ProyectoFactory()
    ana = RecursoFactory(nombre="Ana")
    TareaFactory(
        proyecto=proyecto, responsable=ana, horas_estimadas=10, horas_jira=6, clave_jira="PDT-1"
    )
    TareaFactory(
        proyecto=proyecto,
        responsable=ana,
        horas_estimadas=4,
        horas_jira=2,
        estado=EstadoTarea.COMPLETADA,
    )
    TareaFactory(proyecto=proyecto, responsable=None, horas_estimadas=3, horas_jira=1)
    cliente = APIClient()
    cliente.force_authenticate(admin)

    respuesta = cliente.get("/api/v1/tablero/mi-trabajo/exportar/")

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("application/vnd.openxmlformats")
    libro = _abrir_excel(respuesta)
    tareas = libro["Tareas"]
    assert tareas.max_row >= 4  # encabezado + 3 tareas (+ total)
    filas = list(tareas.iter_rows(min_row=2, max_row=4, values_only=True))
    assert sum(fila[11] for fila in filas) == 9  # horas en Jira
    resumen = {fila[0]: fila for fila in libro["Resumen"].iter_rows(values_only=True)}
    assert resumen["Ana"][1:4] == (2, 14.0, 8.0)
    assert resumen["Sin asignar"][1:4] == (1, 3.0, 1.0)


def test_exportar_excel_respeta_filtros_y_alcance(roles):
    proyecto = ProyectoFactory()
    yo = RecursoFactory()
    otra = RecursoFactory()
    usuario = crear_usuario_con_rol("RECURSO")
    yo.usuario = usuario
    yo.save()
    TareaFactory(proyecto=proyecto, responsable=yo, estado=EstadoTarea.EN_PROGRESO)
    TareaFactory(proyecto=proyecto, responsable=yo, estado=EstadoTarea.PENDIENTE)
    TareaFactory(proyecto=proyecto, responsable=otra)
    cliente = APIClient()
    cliente.force_authenticate(usuario)

    todas = _abrir_excel(cliente.get("/api/v1/tablero/mi-trabajo/exportar/"))["Tareas"]
    filtradas = _abrir_excel(
        cliente.get("/api/v1/tablero/mi-trabajo/exportar/", {"estado": "EN_PROGRESO"})
    )["Tareas"]

    def con_tarea(hoja):
        return [f for f in hoja.iter_rows(min_row=2, max_row=4, values_only=True) if f[3]]

    assert len(con_tarea(todas)) == 2  # solo las suyas
    assert len(con_tarea(filtradas)) == 1
