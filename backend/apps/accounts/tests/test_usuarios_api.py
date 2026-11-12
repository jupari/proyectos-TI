"""docs/api-contrato.md §8: `usuarios` es `ADMIN: L C E B`, `PMO: L`. PMO
necesita listar usuarios para elegir gerente/líder técnico al crear un
proyecto (fase 05-proyectos-presupuesto)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
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


def test_admin_crea_usuario_y_la_respuesta_trae_la_clave_temporal_una_sola_vez(roles, cliente):
    """No hay envío de correo en esta versión (PLAN.md §10): la respuesta de
    creación es la única vez que la clave temporal viaja en texto plano,
    para que quien crea la cuenta pueda comunicarla. Un GET posterior no
    debe volver a exponerla."""
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/usuarios/",
        {
            "email": "nuevo@seguimiento.local",
            "nombres": "Nuevo",
            "apellidos": "Usuario",
            "roles": ["RECURSO"],
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["clave_temporal"]
    clave_temporal = respuesta.data["clave_temporal"]

    creado = Usuario.objects.get(email="nuevo@seguimiento.local")
    assert creado.check_password(clave_temporal)
    assert creado.debe_cambiar_clave is True
    assert list(creado.groups.values_list("rol_meta__codigo", flat=True)) == ["RECURSO"]

    detalle = cliente.get(f"/api/v1/usuarios/{creado.id}/")
    assert "clave_temporal" not in detalle.data
