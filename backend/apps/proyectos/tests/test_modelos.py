import datetime

import pytest
from django.db import IntegrityError, transaction

from apps.proyectos.tests.factories import ProyectoFactory

pytestmark = pytest.mark.django_db


def test_proyecto_fecha_fin_antes_de_inicio_falla():
    with pytest.raises(IntegrityError), transaction.atomic():
        ProyectoFactory(
            fecha_inicio_plan=datetime.date(2026, 6, 1),
            fecha_fin_plan=datetime.date(2026, 1, 1),
        )
