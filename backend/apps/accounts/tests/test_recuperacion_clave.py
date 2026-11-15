import re

import pytest
from django.core import mail
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


def _uid_y_token_del_ultimo_correo():
    cuerpo = mail.outbox[-1].body
    coincidencia = re.search(r"uid=([^&\s]+)&token=([^\s]+)", cuerpo)
    return coincidencia.group(1), coincidencia.group(2)


def test_recuperar_clave_con_email_existente_envia_correo_con_enlace(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", email="persona@demo.local", password="ClaveVieja123")

    respuesta = cliente.post(
        "/api/v1/auth/recuperar-clave/", {"email": usuario.email}, format="json"
    )

    assert respuesta.status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [usuario.email]
    uid, token = _uid_y_token_del_ultimo_correo()
    assert uid and token


def test_recuperar_clave_con_email_inexistente_responde_generico_sin_enviar_correo(roles, cliente):
    respuesta = cliente.post(
        "/api/v1/auth/recuperar-clave/", {"email": "nadie@demo.local"}, format="json"
    )

    assert respuesta.status_code == 200
    assert len(mail.outbox) == 0


def test_recuperar_clave_de_cuenta_google_no_envia_correo(roles, cliente):
    usuario = crear_usuario_con_rol("CONSULTA", proveedor_auth=ProveedorAuth.GOOGLE)
    usuario.set_unusable_password()
    usuario.save()

    respuesta = cliente.post(
        "/api/v1/auth/recuperar-clave/", {"email": usuario.email}, format="json"
    )

    assert respuesta.status_code == 200
    assert len(mail.outbox) == 0


def test_restablecer_clave_con_enlace_valido_cambia_la_clave_y_permite_login(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", email="persona@demo.local", password="ClaveVieja123")
    cliente.post("/api/v1/auth/recuperar-clave/", {"email": usuario.email}, format="json")
    uid, token = _uid_y_token_del_ultimo_correo()

    respuesta = cliente.post(
        "/api/v1/auth/restablecer-clave/",
        {"uid": uid, "token": token, "clave_nueva": "ClaveNueva456!"},
        format="json",
    )

    assert respuesta.status_code == 204
    usuario.refresh_from_db()
    assert usuario.check_password("ClaveNueva456!")
    assert usuario.debe_cambiar_clave is False

    login = cliente.post(
        "/api/v1/auth/login/",
        {"email": usuario.email, "password": "ClaveNueva456!"},
        format="json",
    )
    assert login.status_code == 200
    assert login.data["requiere_codigo"] is True


def test_restablecer_clave_con_token_invalido_se_rechaza(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", email="persona@demo.local", password="ClaveVieja123")
    cliente.post("/api/v1/auth/recuperar-clave/", {"email": usuario.email}, format="json")
    uid, _ = _uid_y_token_del_ultimo_correo()

    respuesta = cliente.post(
        "/api/v1/auth/restablecer-clave/",
        {"uid": uid, "token": "token-inventado", "clave_nueva": "ClaveNueva456!"},
        format="json",
    )

    assert respuesta.status_code == 400
    usuario.refresh_from_db()
    assert usuario.check_password("ClaveVieja123")


def test_restablecer_clave_con_uid_invalido_se_rechaza(roles, cliente):
    respuesta = cliente.post(
        "/api/v1/auth/restablecer-clave/",
        {"uid": "no-es-base64-valido", "token": "cualquiera", "clave_nueva": "ClaveNueva456!"},
        format="json",
    )

    assert respuesta.status_code == 400


def test_restablecer_clave_debil_se_rechaza(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", email="persona@demo.local", password="ClaveVieja123")
    cliente.post("/api/v1/auth/recuperar-clave/", {"email": usuario.email}, format="json")
    uid, token = _uid_y_token_del_ultimo_correo()

    respuesta = cliente.post(
        "/api/v1/auth/restablecer-clave/",
        {"uid": uid, "token": token, "clave_nueva": "corta1"},
        format="json",
    )

    assert respuesta.status_code == 400
    usuario.refresh_from_db()
    assert usuario.check_password("ClaveVieja123")


def test_restablecer_clave_con_token_ya_usado_no_sirve_dos_veces(roles, cliente):
    usuario = crear_usuario_con_rol("RECURSO", email="persona@demo.local", password="ClaveVieja123")
    cliente.post("/api/v1/auth/recuperar-clave/", {"email": usuario.email}, format="json")
    uid, token = _uid_y_token_del_ultimo_correo()

    primera = cliente.post(
        "/api/v1/auth/restablecer-clave/",
        {"uid": uid, "token": token, "clave_nueva": "ClaveNueva456!"},
        format="json",
    )
    assert primera.status_code == 204

    segunda = cliente.post(
        "/api/v1/auth/restablecer-clave/",
        {"uid": uid, "token": token, "clave_nueva": "OtraClave789!"},
        format="json",
    )
    assert segunda.status_code == 400
