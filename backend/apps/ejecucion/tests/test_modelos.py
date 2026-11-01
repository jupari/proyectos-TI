import datetime

import pytest
from django.db import IntegrityError, transaction

from apps.ejecucion.models import RegistroEjecucion
from apps.ejecucion.tests.factories import RegistroEjecucionFactory
from apps.tareas.tests.factories import TareaFactory

pytestmark = pytest.mark.django_db


def test_registro_ejecucion_duplicado_falla():
    """Misma tupla (recurso, proyecto, tarea, periodicidad, periodo_inicio) no se repite.

    Se fija una `tarea` concreta (no null): Postgres no considera dos NULL
    iguales para una restricción UNIQUE, así que con `tarea=None` el
    constraint nunca se dispararía.
    """
    tarea = TareaFactory()
    primero = RegistroEjecucionFactory(
        proyecto=tarea.proyecto,
        tarea=tarea,
        periodicidad="DIARIA",
        periodo_inicio=datetime.date(2026, 2, 2),
        periodo_fin=datetime.date(2026, 2, 2),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        # Se usa el modelo directamente (no la factory) para forzar el INSERT
        # duplicado; la factory resolvería esta misma llamada con get_or_create.
        RegistroEjecucion.objects.create(
            recurso=primero.recurso,
            proyecto=primero.proyecto,
            tarea=primero.tarea,
            periodicidad="DIARIA",
            periodo_inicio=datetime.date(2026, 2, 2),
            periodo_fin=datetime.date(2026, 2, 2),
            horas=4,
            valor_hora_aplicado=70000,
        )


def test_registro_ejecucion_horas_no_positivas_falla():
    with pytest.raises(IntegrityError), transaction.atomic():
        RegistroEjecucionFactory(horas=0)
