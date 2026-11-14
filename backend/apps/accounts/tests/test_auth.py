import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.tests.conftest import crear_usuario_con_rol
from apps.core.choices import ProveedorAuth

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_de_throttle_limpio():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def cliente():
    return APIClient()


def test_login_devuelve_access_refresh_y_usuario(roles, cliente):
    usuario = crear_usuario_con_rol("LIDER", email="lider@demo.local", password="demo12345")

    respuesta = cliente.post(
        "/api/v1/auth/login/", {"email": usuario.email, "password": "demo12345"}, format="json"
    )

    assert respuesta.status_code == 200
    assert set(respuesta.data) == {"access", "refresh", "usuario"}
    assert respuesta.data["usuario"]["email"] == usuario.email
    assert respuesta.data["usuario"]["roles"] == ["LIDER"]


def test_login_clave_incorrecta_devuelve_401_con_sobre_de_error(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", password="demo12345")

    respuesta = cliente.post(
        "/api/v1/auth/login/", {"email": usuario.email, "password": "mala"}, format="json"
    )

    assert respuesta.status_code == 401
    assert respuesta.data["error"]["codigo"] == "NO_AUTENTICADO"


def test_login_usuario_google_no_puede_usar_clave(roles, cliente):
    usuario = crear_usuario_con_rol("CONSULTA", proveedor_auth=ProveedorAuth.GOOGLE)
    usuario.set_unusable_password()
    usuario.save()

    respuesta = cliente.post(
        "/api/v1/auth/login/", {"email": usuario.email, "password": "cualquiera"}, format="json"
    )

    assert respuesta.status_code == 401
    assert "Google" in respuesta.data["error"]["mensaje"]


def test_login_usuario_inactivo_devuelve_401(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", password="demo12345", is_active=False)

    respuesta = cliente.post(
        "/api/v1/auth/login/", {"email": usuario.email, "password": "demo12345"}, format="json"
    )

    assert respuesta.status_code == 401


def test_yo_devuelve_roles_y_permisos_ui_correctos(roles, cliente):
    usuario = crear_usuario_con_rol("PMO")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.get("/api/v1/auth/yo/")

    assert respuesta.status_code == 200
    assert respuesta.data["roles"] == ["PMO"]
    assert "proyectos.crear" in respuesta.data["permisos_ui"]
    assert "admin.usuarios" not in respuesta.data["permisos_ui"]
    assert "proyectos_liderados" in respuesta.data


def test_yo_patch_actualiza_datos_personales(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.patch("/api/v1/auth/yo/", {"cargo": "Nuevo cargo"}, format="json")

    assert respuesta.status_code == 200
    usuario.refresh_from_db()
    assert usuario.cargo == "Nuevo cargo"


def test_refresh_rota_el_token_y_el_anterior_queda_invalido(roles, cliente):
    usuario = crear_usuario_con_rol("LIDER", password="demo12345")
    login = cliente.post(
        "/api/v1/auth/login/", {"email": usuario.email, "password": "demo12345"}, format="json"
    )
    refresh_original = login.data["refresh"]

    primero = cliente.post("/api/v1/auth/refresh/", {"refresh": refresh_original}, format="json")
    assert primero.status_code == 200
    assert primero.data["refresh"] != refresh_original

    segundo = cliente.post("/api/v1/auth/refresh/", {"refresh": refresh_original}, format="json")
    assert segundo.status_code == 401


def test_logout_deja_el_refresh_inservible(roles, cliente):
    usuario = crear_usuario_con_rol("LIDER", password="demo12345")
    login = cliente.post(
        "/api/v1/auth/login/", {"email": usuario.email, "password": "demo12345"}, format="json"
    )
    refresh = login.data["refresh"]
    cliente.force_authenticate(user=usuario)

    salida = cliente.post("/api/v1/auth/logout/", {"refresh": refresh}, format="json")
    assert salida.status_code == 204

    siguiente = cliente.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
    assert siguiente.status_code == 401


def test_logout_con_refresh_invalido_no_bloquea_al_cliente(roles, cliente):
    usuario = crear_usuario_con_rol("LIDER")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post("/api/v1/auth/logout/", {"refresh": "token-invalido"}, format="json")

    assert respuesta.status_code == 204


def test_cambiar_clave(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", password="ClaveVieja123")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post(
        "/api/v1/auth/cambiar-clave/",
        {"clave_actual": "ClaveVieja123", "clave_nueva": "ClaveNueva456!"},
        format="json",
    )

    assert respuesta.status_code == 204
    usuario.refresh_from_db()
    assert usuario.check_password("ClaveNueva456!")
    assert usuario.debe_cambiar_clave is False


def test_cambiar_clave_actual_incorrecta_falla(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", password="ClaveVieja123")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post(
        "/api/v1/auth/cambiar-clave/",
        {"clave_actual": "incorrecta", "clave_nueva": "ClaveNueva456!"},
        format="json",
    )

    assert respuesta.status_code == 400


@pytest.mark.parametrize(
    "clave_debil",
    [
        "Corta12",  # menos de 10 caracteres
        "clavesinnumero",  # sin dígito
        "CLAVE12345",  # sin minúscula
        "clave12345",  # sin mayúscula
        "Password123",  # en la lista de claves comunes
    ],
)
def test_cambiar_clave_nueva_debil_se_rechaza(roles, cliente, clave_debil):
    usuario = crear_usuario_con_rol("RECURSO", password="ClaveVieja123")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post(
        "/api/v1/auth/cambiar-clave/",
        {"clave_actual": "ClaveVieja123", "clave_nueva": clave_debil},
        format="json",
    )

    assert respuesta.status_code == 400
    usuario.refresh_from_db()
    assert usuario.check_password("ClaveVieja123")


def test_seis_intentos_de_login_en_un_minuto_dan_429(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", password="demo12345")

    for _ in range(5):
        respuesta = cliente.post(
            "/api/v1/auth/login/",
            {"email": usuario.email, "password": "incorrecta"},
            format="json",
        )
        assert respuesta.status_code == 401

    sexta = cliente.post(
        "/api/v1/auth/login/", {"email": usuario.email, "password": "incorrecta"}, format="json"
    )
    assert sexta.status_code == 429
