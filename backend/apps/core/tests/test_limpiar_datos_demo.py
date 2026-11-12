"""`limpiar_datos_demo`: borra todo lo de `seed_demo` para empezar a cargar
datos reales, sin dejar la aplicación sin ningún usuario con el que entrar."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.catalogos.models import Area, PerfilRecurso, Portafolio
from apps.proyectos.models import Proyecto
from apps.recursos.models import Recurso

Usuario = get_user_model()

pytestmark = pytest.mark.django_db


def test_limpiar_datos_demo_borra_todo_salvo_los_superusuarios():
    call_command("seed_demo")
    assert Proyecto.objects.count() > 0
    assert Recurso.objects.count() > 0
    assert Usuario.objects.filter(is_superuser=False).count() > 0
    total_superusuarios_antes = Usuario.objects.filter(is_superuser=True).count()
    assert total_superusuarios_antes > 0

    call_command("limpiar_datos_demo", "--si")

    assert Proyecto.objects.count() == 0
    assert Recurso.objects.count() == 0
    assert Area.objects.count() == 0
    assert Portafolio.objects.count() == 0
    assert PerfilRecurso.objects.count() == 0
    assert Usuario.objects.filter(is_superuser=False).count() == 0
    assert Usuario.objects.filter(is_superuser=True).count() == total_superusuarios_antes


def test_limpiar_datos_demo_sin_confirmar_no_borra_nada(monkeypatch):
    call_command("seed_demo")

    monkeypatch.setattr("builtins.input", lambda _: "no")
    with pytest.raises(CommandError):
        call_command("limpiar_datos_demo")

    assert Proyecto.objects.count() > 0
    assert Recurso.objects.count() > 0
