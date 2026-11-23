import pytest
from django.db import IntegrityError, transaction

from apps.core.choices import EstadoSprint, TipoTarea
from apps.proyectos.tests.factories import ProyectoFactory
from apps.tareas.models import Sprint
from apps.tareas.tests.factories import DependenciaTareaFactory, TareaFactory

pytestmark = pytest.mark.django_db


def test_sprint_de_jira_es_unico_por_proyecto():
    proyecto = ProyectoFactory()
    Sprint.objects.create(proyecto=proyecto, id_jira=7, nombre="Sprint 7")
    with pytest.raises(IntegrityError), transaction.atomic():
        Sprint.objects.create(proyecto=proyecto, id_jira=7, nombre="Sprint 7 repetido")
    # El mismo id en otro proyecto sí es válido.
    Sprint.objects.create(proyecto=ProyectoFactory(), id_jira=7, nombre="Sprint 7")


def test_historia_con_sprint_y_epica_y_tarea_hija():
    proyecto = ProyectoFactory()
    sprint = Sprint.objects.create(
        proyecto=proyecto, id_jira=1, nombre="Sprint 1", estado=EstadoSprint.ACTIVO
    )
    historia = TareaFactory(
        proyecto=proyecto,
        tipo=TipoTarea.HISTORIA,
        sprint=sprint,
        epica_clave="PDTIRD-1",
        epica_nombre="Portal",
    )
    hija = TareaFactory(proyecto=proyecto, tarea_padre=historia, sprint=sprint)

    assert list(sprint.tareas.order_by("codigo")) == sorted(
        [historia, hija], key=lambda t: t.codigo
    )
    assert hija.tarea_padre == historia


def test_dependencia_tarea_consigo_misma_falla():
    tarea = TareaFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        DependenciaTareaFactory(tarea_origen=tarea, tarea_destino=tarea)
