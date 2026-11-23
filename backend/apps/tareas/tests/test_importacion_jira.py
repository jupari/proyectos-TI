from unittest.mock import MagicMock

import pytest

from apps.core.choices import EstadoTarea, TipoTarea
from apps.recursos.tests.factories import RecursoFactory
from apps.tareas.importacion_jira import (
    estado_app_para,
    normalizar_incidencia,
    simular_importacion_tareas,
    tipo_app_para,
)

pytestmark = pytest.mark.django_db

CAMPO_SPRINT = "customfield_10020"


def _incidencia(clave, tipo="Story", estado="En curso", categoria="indeterminate", **campos):
    base = {
        "summary": f"Resumen {clave}",
        "issuetype": {"name": tipo, "hierarchyLevel": 0, "subtask": False},
        "status": {"name": estado, "statusCategory": {"key": categoria}},
        "timeoriginalestimate": 28800,
    }
    base.update(campos)
    return {"id": clave.split("-")[1], "key": clave, "fields": base}


def test_estado_se_traduce_por_categoria_y_nombre():
    assert estado_app_para("Por hacer", "new") == EstadoTarea.PENDIENTE
    assert estado_app_para("En desarrollo", "indeterminate") == EstadoTarea.EN_PROGRESO
    assert estado_app_para("Bloqueado", "indeterminate") == EstadoTarea.BLOQUEADA
    assert estado_app_para("En revisión", "indeterminate") == EstadoTarea.EN_REVISION
    assert estado_app_para("Listo", "done") == EstadoTarea.COMPLETADA
    assert estado_app_para("Cancelado", "done") == EstadoTarea.CANCELADA


def test_tipo_de_incidencia_se_traduce():
    assert tipo_app_para({"name": "Story", "hierarchyLevel": 0}) == TipoTarea.HISTORIA
    assert tipo_app_para({"name": "Historia de usuario"}) == TipoTarea.HISTORIA
    assert tipo_app_para({"name": "Bug", "hierarchyLevel": 0}) == TipoTarea.INCIDENCIA
    assert tipo_app_para({"name": "Sub-task", "subtask": True}) == TipoTarea.TAREA
    assert tipo_app_para({"name": "Task", "hierarchyLevel": 0}) == TipoTarea.TAREA


def test_normalizar_toma_el_sprint_activo_y_la_epica_del_padre():
    crudo = _incidencia(
        "PDT-5",
        parent={
            "key": "PDT-1",
            "fields": {"summary": "Portal", "issuetype": {"name": "Epic", "hierarchyLevel": 1}},
        },
        **{
            CAMPO_SPRINT: [
                {"id": 1, "name": "Sprint 1", "state": "closed"},
                {
                    "id": 2,
                    "name": "Sprint 2",
                    "state": "active",
                    "startDate": "2026-03-16T10:00:00Z",
                },
            ]
        },
    )

    fila = normalizar_incidencia(crudo, CAMPO_SPRINT)

    assert fila["sprint"]["nombre"] == "Sprint 2"
    assert fila["sprint"]["fecha_inicio"] == "2026-03-16"
    assert fila["epica_clave"] == "PDT-1"
    assert fila["epica_nombre"] == "Portal"
    assert fila["horas_estimadas"] == 8.0


def test_simulacion_resume_estados_sprints_epicas_y_responsables():
    RecursoFactory(jira_account_id="acc-1")
    epica = _incidencia(
        "PDT-1",
        tipo="Epic",
        summary="Portal",
        issuetype={"name": "Epic", "hierarchyLevel": 1, "subtask": False},
    )
    epica_padre = {
        "key": "PDT-1",
        "fields": {"summary": "Portal", "issuetype": {"name": "Epic", "hierarchyLevel": 1}},
    }
    historia = _incidencia(
        "PDT-2",
        parent=epica_padre,
        assignee={"accountId": "acc-1", "displayName": "Ana"},
        **{CAMPO_SPRINT: [{"id": 7, "name": "Sprint 7", "state": "active"}]},
    )
    subtarea = _incidencia(
        "PDT-3",
        tipo="Sub-task",
        estado="Bloqueado",
        parent={"key": "PDT-2", "fields": {"summary": "x", "issuetype": {"name": "Story"}}},
        issuetype={"name": "Sub-task", "subtask": True, "hierarchyLevel": -1},
        assignee={"accountId": "acc-9", "displayName": "Luis"},
        timeoriginalestimate=None,
    )
    bug = _incidencia("PDT-4", tipo="Bug", estado="Listo", categoria="done")
    cliente = MagicMock()
    cliente.buscar_incidencias.return_value = {
        "incidencias": [epica, historia, subtarea, bug],
        "campo_sprint": CAMPO_SPRINT,
        "truncado": False,
    }

    resumen = simular_importacion_tareas("PDT", cliente=cliente)

    assert resumen["total_incidencias"] == 3  # la épica no cuenta como tarea
    assert resumen["por_tipo"] == {"HISTORIA": 1, "TAREA": 1, "INCIDENCIA": 1}
    nombres = {e["nombre"]: e for e in resumen["estados"]}
    assert nombres["Bloqueado"]["estado_app"] == EstadoTarea.BLOQUEADA
    assert nombres["Listo"]["estado_app"] == EstadoTarea.COMPLETADA
    assert [s["nombre"] for s in resumen["sprints"]] == ["Sprint 7"]
    assert resumen["epicas"] == [{"clave": "PDT-1", "nombre": "Portal"}]
    assert resumen["sin_estimacion"] == 1
    assert resumen["sin_responsable"] == 1
    assert [p["nombre"] for p in resumen["responsables_sin_recurso"]] == ["Luis"]
    # La subtarea hereda la épica de su historia.
    assert next(m for m in resumen["muestra"] if m["clave"] == "PDT-3")["epica"] == "PDT-1"
