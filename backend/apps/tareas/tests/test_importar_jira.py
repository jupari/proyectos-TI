import datetime
from unittest.mock import MagicMock

import pytest
from rest_framework.exceptions import ValidationError

from apps.core.choices import EstadoSprint, EstadoTarea, Prioridad, TipoTarea
from apps.proyectos.tests.factories import ProyectoFactory
from apps.recursos.tests.factories import RecursoFactory
from apps.tareas.importar_jira import avance_de, importar_tareas_jira
from apps.tareas.models import Sprint, Tarea
from apps.tareas.tests.factories import TareaFactory

pytestmark = pytest.mark.django_db

CAMPO_SPRINT = "customfield_10020"
EPICA = {
    "key": "PDT-1",
    "fields": {"summary": "Portal", "issuetype": {"name": "Epic", "hierarchyLevel": 1}},
}


def _incidencia(clave, tipo="Story", estado="En curso", categoria="indeterminate", **campos):
    base = {
        "summary": f"Resumen {clave}",
        "issuetype": {"name": tipo, "hierarchyLevel": 0, "subtask": False},
        "status": {"name": estado, "statusCategory": {"key": categoria}},
        "priority": {"name": "High"},
        "timeoriginalestimate": 28800,
        "timespent": 14400,
        "created": "2026-03-02T10:00:00.000+0000",
    }
    base.update(campos)
    return {"id": clave.split("-")[1], "key": clave, "fields": base}


def _cliente(incidencias, truncado=False):
    cliente = MagicMock()
    cliente.buscar_incidencias.return_value = {
        "incidencias": incidencias,
        "campo_sprint": CAMPO_SPRINT,
        "truncado": truncado,
    }
    return cliente


def _lote():
    sprint = [
        {
            "id": 7,
            "name": "Sprint 7",
            "state": "active",
            "startDate": "2026-03-09T09:00:00Z",
            "endDate": "2026-03-20T18:00:00Z",
        }
    ]
    historia = _incidencia(
        "PDT-2",
        parent=EPICA,
        assignee={"accountId": "acc-1", "displayName": "Ana"},
        **{CAMPO_SPRINT: sprint},
    )
    subtarea = _incidencia(
        "PDT-3",
        tipo="Sub-task",
        estado="Listo",
        categoria="done",
        issuetype={"name": "Sub-task", "subtask": True, "hierarchyLevel": -1},
        parent={"key": "PDT-2", "fields": {"summary": "x", "issuetype": {"name": "Story"}}},
        resolutiondate="2026-03-12T10:00:00.000+0000",
        timespent=28800,
        **{CAMPO_SPRINT: sprint},
    )
    epica = _incidencia(
        "PDT-1",
        tipo="Epic",
        summary="Portal",
        issuetype={"name": "Epic", "hierarchyLevel": 1, "subtask": False},
    )
    return [epica, subtarea, historia]


def test_importa_historia_y_subtarea_con_sprint_epica_y_responsable():
    proyecto = ProyectoFactory(clave_jira="PDT")
    ana = RecursoFactory(jira_account_id="acc-1")

    resumen = importar_tareas_jira("PDT", cliente=_cliente(_lote()))

    assert resumen["creadas"] == 2 and resumen["actualizadas"] == 0
    assert resumen["sprints_creados"] == 1
    assert resumen["errores"] == []
    historia = Tarea.objects.get(clave_jira="PDT-2")
    subtarea = Tarea.objects.get(clave_jira="PDT-3")
    assert historia.proyecto_id == proyecto.id
    assert historia.tipo == TipoTarea.HISTORIA
    assert historia.responsable_id == ana.id
    assert historia.epica_clave == "PDT-1" and historia.epica_nombre == "Portal"
    assert historia.prioridad == Prioridad.ALTA
    assert historia.fecha_inicio_plan == datetime.date(2026, 3, 9)
    assert historia.fecha_fin_plan == datetime.date(2026, 3, 20)
    assert subtarea.tarea_padre_id == historia.id
    assert subtarea.estado == EstadoTarea.COMPLETADA
    assert subtarea.epica_clave == "PDT-1"  # la hereda de su historia
    # La historia toma su avance de la subtarea (completada = 100).
    historia.refresh_from_db()
    assert historia.avance == 100
    sprint = Sprint.objects.get(proyecto=proyecto, id_jira=7)
    assert sprint.estado == EstadoSprint.ACTIVO and historia.sprint_id == sprint.id
    # El avance del proyecto se calcula una sola vez, al terminar.
    proyecto.refresh_from_db()
    assert proyecto.avance_tareas == 100


def test_reimportar_actualiza_sin_duplicar_y_conserva_las_fechas_del_plan():
    proyecto = ProyectoFactory(clave_jira="PDT")
    importar_tareas_jira("PDT", cliente=_cliente(_lote()))
    historia = Tarea.objects.get(clave_jira="PDT-2")
    historia.fecha_fin_plan = datetime.date(2026, 4, 30)  # ajuste hecho en la aplicación
    historia.save()

    resumen = importar_tareas_jira("PDT", cliente=_cliente(_lote()))

    assert resumen["creadas"] == 0 and resumen["actualizadas"] == 2
    assert resumen["sprints_actualizados"] == 1
    assert Tarea.objects.filter(proyecto=proyecto).count() == 2
    historia.refresh_from_db()
    assert historia.fecha_fin_plan == datetime.date(2026, 4, 30)


def test_reimportar_reactiva_la_tarea_borrada_logicamente():
    ProyectoFactory(clave_jira="PDT")
    importar_tareas_jira("PDT", cliente=_cliente(_lote()))
    Tarea.objects.filter(clave_jira="PDT-3").update(activo=False)

    importar_tareas_jira("PDT", cliente=_cliente(_lote()))

    assert Tarea.objects.get(clave_jira="PDT-3").activo is True


def test_proyecto_sin_asociar_se_rechaza_con_mensaje_claro():
    ProyectoFactory(clave_jira="OTRO")

    with pytest.raises(ValidationError) as error:
        importar_tareas_jira("PDT", cliente=_cliente([]))

    assert "Asócielo primero" in str(error.value.detail)


def test_clave_ya_importada_en_otro_proyecto_es_un_error_y_no_frena_el_resto():
    ProyectoFactory(clave_jira="PDT")
    TareaFactory(proyecto=ProyectoFactory(), clave_jira="PDT-2")

    resumen = importar_tareas_jira("PDT", cliente=_cliente(_lote()))

    assert [e["clave"] for e in resumen["errores"]] == ["PDT-2"]
    assert "otro proyecto" in resumen["errores"][0]["detalle"]
    assert resumen["creadas"] == 1  # la subtarea se importa igual


def test_dry_run_no_deja_nada_en_la_base():
    ProyectoFactory(clave_jira="PDT")

    resumen = importar_tareas_jira("PDT", dry_run=True, cliente=_cliente(_lote()))

    assert resumen["creadas"] == 2
    assert Tarea.objects.filter(clave_jira__startswith="PDT-").count() == 0
    assert Sprint.objects.count() == 0


def test_avance_en_curso_es_lo_registrado_sobre_lo_estimado_con_tope_90():
    en_curso = {"estado": EstadoTarea.EN_PROGRESO, "horas_estimadas": 10, "horas_registradas": 4}
    pasada = {"estado": EstadoTarea.EN_PROGRESO, "horas_estimadas": 10, "horas_registradas": 25}
    sin_dato = {"estado": EstadoTarea.EN_PROGRESO, "horas_estimadas": None, "horas_registradas": 3}

    assert avance_de(en_curso) == 40
    assert avance_de(pasada) == 90
    assert avance_de(sin_dato) == 0
    assert avance_de({"estado": EstadoTarea.COMPLETADA}) == 100


def test_asocia_al_recurso_por_nombre_sin_importar_tildes_ni_orden():
    ProyectoFactory(clave_jira="PDT")
    juan = RecursoFactory(nombre="Pérez Ana María", jira_account_id=None)
    otro = RecursoFactory(nombre="Luis Mora", jira_account_id=None)
    lote = _lote()
    lote[2]["fields"]["assignee"] = {"accountId": "acc-9", "displayName": "ana maria PEREZ"}

    resumen = importar_tareas_jira("PDT", cliente=_cliente(lote))

    juan.refresh_from_db()
    otro.refresh_from_db()
    assert juan.jira_account_id == "acc-9" and otro.jira_account_id is None
    assert Tarea.objects.get(clave_jira="PDT-2").responsable_id == juan.id
    assert resumen["sin_responsable_asociado"] == []


def test_no_asocia_si_el_nombre_coincide_con_dos_recursos():
    ProyectoFactory(clave_jira="PDT")
    RecursoFactory(nombre="Ana Pérez", jira_account_id=None)
    RecursoFactory(nombre="Perez Ana", jira_account_id=None)
    lote = _lote()
    lote[2]["fields"]["assignee"] = {"accountId": "acc-9", "displayName": "Ana Pérez"}

    resumen = importar_tareas_jira("PDT", cliente=_cliente(lote))

    assert Tarea.objects.get(clave_jira="PDT-2").responsable_id is None
    assert resumen["sin_responsable_asociado"] == ["Ana Pérez"]


def test_guarda_las_horas_registradas_en_jira_sin_tocar_las_aprobadas():
    ProyectoFactory(clave_jira="PDT")

    importar_tareas_jira("PDT", cliente=_cliente(_lote()))

    subtarea = Tarea.objects.get(clave_jira="PDT-3")
    assert subtarea.horas_jira == 8  # timespent de 28800 s
    assert subtarea.horas_ejecutadas == 0
