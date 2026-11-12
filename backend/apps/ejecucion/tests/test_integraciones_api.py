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


# --- POST /integraciones/jira/importar/ --------------------------------------


@pytest.fixture(autouse=True)
def _jira_configurado(settings):
    settings.JIRA_BASE_URL = "https://empresa.atlassian.net"
    settings.JIRA_EMAIL = "admin@empresa.com"
    settings.JIRA_API_TOKEN = "token-jira-de-prueba"  # noqa: S105 (valor de prueba)
    settings.TEMPO_API_TOKEN = "token-tempo-de-prueba"  # noqa: S105 (valor de prueba)


def test_admin_dispara_la_importacion_con_las_fechas_que_elige(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)
    resumen_falso = {"creados": 2, "actualizados": 0, "omitidos": [], "errores": []}

    with patch(
        "apps.ejecucion.views.importar_horas_jira", return_value=resumen_falso
    ) as importar_mock:
        respuesta = cliente.post(
            "/api/v1/integraciones/jira/importar/",
            {"desde": "2026-01-01", "hasta": "2026-01-31"},
            format="json",
        )

    assert respuesta.status_code == 200
    assert respuesta.data == resumen_falso
    importar_mock.assert_called_once()
    args, kwargs = importar_mock.call_args
    assert args[0].isoformat() == "2026-01-01"
    assert args[1].isoformat() == "2026-01-31"
    assert kwargs["dry_run"] is False
    assert kwargs["auto_aprobar"] is None


def test_admin_elige_dry_run_y_aprobacion_automatica(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    with patch(
        "apps.ejecucion.views.importar_horas_jira",
        return_value={"creados": 0, "actualizados": 0, "omitidos": [], "errores": []},
    ) as importar_mock:
        cliente.post(
            "/api/v1/integraciones/jira/importar/",
            {"desde": "2026-01-01", "hasta": "2026-01-31", "dry_run": True, "auto_aprobar": True},
            format="json",
        )

    _, kwargs = importar_mock.call_args
    assert kwargs["dry_run"] is True
    assert kwargs["auto_aprobar"] is True


def test_importar_sin_fechas_da_400(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post("/api/v1/integraciones/jira/importar/", {}, format="json")

    assert respuesta.status_code == 400


def test_importar_con_hasta_antes_de_desde_da_400(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/integraciones/jira/importar/",
        {"desde": "2026-01-31", "hasta": "2026-01-01"},
        format="json",
    )

    assert respuesta.status_code == 400


def test_importar_sin_variables_de_entorno_da_400(roles, cliente, settings):
    settings.JIRA_BASE_URL = ""
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/integraciones/jira/importar/",
        {"desde": "2026-01-01", "hasta": "2026-01-31"},
        format="json",
    )

    assert respuesta.status_code == 400


@pytest.mark.parametrize("rol", ["PMO", "LIDER", "RECURSO", "CONSULTA"])
def test_otros_roles_no_pueden_disparar_la_importacion(roles, cliente, rol):
    usuario = crear_usuario_con_rol(rol)
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post(
        "/api/v1/integraciones/jira/importar/",
        {"desde": "2026-01-01", "hasta": "2026-01-31"},
        format="json",
    )

    assert respuesta.status_code == 403
