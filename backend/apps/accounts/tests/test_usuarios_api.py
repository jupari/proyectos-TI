"""docs/api-contrato.md §8: `usuarios` es `ADMIN: L C E B`, `PMO: L`. PMO
necesita listar usuarios para elegir gerente/líder técnico al crear un
proyecto (fase 05-proyectos-presupuesto)."""

import pytest
from rest_framework.test import APIClient

from conftest import crear_usuario_con_rol

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


@pytest.mark.parametrize(
    ("codigo_rol", "esperado"),
    [("ADMIN", 200), ("PMO", 200), ("LIDER", 403), ("RECURSO", 403), ("CONSULTA", 403)],
)
def test_listar_usuarios_segun_rol(roles, cliente, codigo_rol, esperado):
    usuario = crear_usuario_con_rol(codigo_rol)
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.get("/api/v1/usuarios/")

    assert respuesta.status_code == esperado


def test_pmo_no_puede_crear_usuarios(roles, cliente):
    pmo = crear_usuario_con_rol("PMO")
    cliente.force_authenticate(user=pmo)

    respuesta = cliente.post(
        "/api/v1/usuarios/",
        {"email": "nuevo@seguimiento.local", "nombres": "Nuevo", "apellidos": "Usuario"},
        format="json",
    )

    assert respuesta.status_code == 403
