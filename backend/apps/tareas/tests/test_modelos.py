import pytest
from django.db import IntegrityError, transaction

from apps.tareas.tests.factories import DependenciaTareaFactory, TareaFactory

pytestmark = pytest.mark.django_db


def test_dependencia_tarea_consigo_misma_falla():
    tarea = TareaFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        DependenciaTareaFactory(tarea_origen=tarea, tarea_destino=tarea)
