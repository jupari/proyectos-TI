import pytest
from django.core.management import call_command


@pytest.fixture
def roles(db):
    """Siembra los cinco roles del sistema (idempotente)."""
    call_command("seed_roles")


def crear_usuario_con_rol(codigo_rol, **kwargs):
    from django.contrib.auth.models import Group

    from apps.accounts.tests.factories import UsuarioFactory

    usuario = UsuarioFactory(**kwargs)
    grupo = Group.objects.get(rol_meta__codigo=codigo_rol)
    usuario.groups.add(grupo)
    return usuario
