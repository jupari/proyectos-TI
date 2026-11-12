from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from conftest import crear_usuario_con_rol

pytestmark = pytest.mark.django_db

RUTA_CLIENTE = "apps.ejecucion.views.ClienteJiraTempo"


@pytest.fixture
def cliente():
    return APIClient()


# --- GET /integraciones/jira/proyectos/ --------------------------------------


def test_admin_lista_proyectos_de_jira(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)
    cliente_jira = MagicMock()
    cliente_jira.listar_proyectos.return_value = [{"clave": "PROY", "nombre": "Proyecto demo"}]

    with patch(RUTA_CLIENTE, return_value=cliente_jira):
        respuesta = cliente.get("/api/v1/integraciones/jira/proyectos/")

    assert respuesta.status_code == 200
    assert respuesta.data == [{"clave": "PROY", "nombre": "Proyecto demo"}]


@pytest.mark.parametrize("rol", ["LIDER", "RECURSO", "CONSULTA"])
def test_otros_roles_no_pueden_listar_proyectos_de_jira(roles, cliente, rol):
    usuario = crear_usuario_con_rol(rol)
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.get("/api/v1/integraciones/jira/proyectos/")

    assert respuesta.status_code == 403


def test_error_del_cliente_jira_se_traduce_a_502(roles, cliente):
    from apps.ejecucion.integraciones.jira_tempo import ErrorIntegracionJira

    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)
    cliente_jira = MagicMock()
    cliente_jira.listar_proyectos.side_effect = ErrorIntegracionJira("no se pudo conectar")

    with patch(RUTA_CLIENTE, return_value=cliente_jira):
        respuesta = cliente.get("/api/v1/integraciones/jira/proyectos/")

    assert respuesta.status_code == 502
    assert respuesta.data["error"]["codigo"] == "INTEGRACION_JIRA"


# --- /configuracion-importacion-jira/ ----------------------------------------


def test_admin_puede_leer_y_cambiar_la_configuracion(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get("/api/v1/configuracion-importacion-jira/")
    assert respuesta.status_code == 200
    assert respuesta.data["auto_aprobar_importados"] is False

    respuesta = cliente.patch(
        "/api/v1/configuracion-importacion-jira/",
        {"auto_aprobar_importados": True},
        format="json",
    )
    assert respuesta.status_code == 200
    assert respuesta.data["auto_aprobar_importados"] is True

    respuesta = cliente.get("/api/v1/configuracion-importacion-jira/")
    assert respuesta.data["auto_aprobar_importados"] is True


@pytest.mark.parametrize("rol", ["PMO", "LIDER", "RECURSO", "CONSULTA"])
def test_otros_roles_no_pueden_ver_ni_cambiar_la_configuracion(roles, cliente, rol):
    usuario = crear_usuario_con_rol(rol)
    cliente.force_authenticate(user=usuario)

    assert cliente.get("/api/v1/configuracion-importacion-jira/").status_code == 403
    assert (
        cliente.patch(
            "/api/v1/configuracion-importacion-jira/",
            {"auto_aprobar_importados": True},
            format="json",
        ).status_code
        == 403
    )
