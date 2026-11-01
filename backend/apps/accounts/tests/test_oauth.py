import time
from unittest.mock import patch

import pytest
from django.core import signing
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts import oauth
from apps.accounts.exceptions import ErrorOAuthNoConfigurado
from apps.accounts.tests.factories import UsuarioFactory
from apps.core.choices import ProveedorAuth

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _google_configurado(settings):
    settings.GOOGLE_CLIENT_ID = "client-id-de-prueba"
    settings.GOOGLE_CLIENT_SECRET = "secreto-de-prueba"  # noqa: S105 (valor de prueba)
    settings.GOOGLE_REDIRECT_URI = "http://localhost:4200/auth/google/callback"
    settings.GOOGLE_DOMINIOS_PERMITIDOS = []


def _info_valida(**overrides):
    info = {
        "sub": "sub-123",
        "email": "nueva@empresa.com",
        "email_verified": True,
        "given_name": "Nueva",
        "family_name": "Persona",
        "picture": "https://ejemplo.com/foto.jpg",
    }
    info.update(overrides)
    return info


def test_construir_url_autorizacion_incluye_pkce_y_state():
    url, state = oauth.construir_url_autorizacion("challenge-abc")

    assert "code_challenge=challenge-abc" in url
    assert "code_challenge_method=S256" in url
    assert "client_id=client-id-de-prueba" in url
    assert state


def test_construir_url_autorizacion_sin_configurar_lanza_503(settings):
    settings.GOOGLE_CLIENT_ID = ""
    settings.GOOGLE_CLIENT_SECRET = ""

    with pytest.raises(ErrorOAuthNoConfigurado):
        oauth.construir_url_autorizacion("challenge-abc")


def test_validar_state_vencido_falla():
    with patch("django.core.signing.time.time", return_value=time.time() - 700):
        state_viejo = signing.dumps({"n": "x"}, salt=oauth.FIRMA_SALT)

    with pytest.raises(ValidationError):
        oauth.validar_state(state_viejo)


def test_validar_state_valido_no_lanza():
    state = signing.dumps({"n": "x"}, salt=oauth.FIRMA_SALT)
    oauth.validar_state(state)


@patch("apps.accounts.oauth.google_id_token.verify_oauth2_token")
def test_verificar_id_token_valido(mock_verify):
    mock_verify.return_value = _info_valida()

    info = oauth.verificar_id_token("token-falso")

    assert info["email"] == "nueva@empresa.com"


@patch("apps.accounts.oauth.google_id_token.verify_oauth2_token")
def test_verificar_id_token_aud_incorrecto_falla(mock_verify):
    mock_verify.side_effect = ValueError("Token has wrong audience")

    with pytest.raises(ValidationError):
        oauth.verificar_id_token("token-falso")


@patch("apps.accounts.oauth.google_id_token.verify_oauth2_token")
def test_verificar_id_token_email_no_verificado_falla(mock_verify):
    mock_verify.return_value = _info_valida(email_verified=False)

    with pytest.raises(ValidationError):
        oauth.verificar_id_token("token-falso")


@patch("apps.accounts.oauth.requests_lib.post")
def test_canjear_codigo_devuelve_id_token(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"id_token": "id-token-falso"}

    resultado = oauth.canjear_codigo("codigo", "verificador")

    assert resultado == "id-token-falso"
    mock_post.assert_called_once()


@patch("apps.accounts.oauth.requests_lib.post")
def test_canjear_codigo_con_error_de_google_falla(mock_post):
    mock_post.return_value.status_code = 400

    with pytest.raises(ValidationError):
        oauth.canjear_codigo("codigo-malo", "verificador")


def test_obtener_o_crear_usuario_crea_usuario_nuevo_con_rol_consulta(roles):
    usuario = oauth.obtener_o_crear_usuario(_info_valida())

    assert usuario.proveedor_auth == ProveedorAuth.GOOGLE
    assert usuario.google_sub == "sub-123"
    assert not usuario.has_usable_password()
    assert usuario.groups.filter(rol_meta__codigo="CONSULTA").exists()


def test_obtener_o_crear_usuario_vincula_cuenta_local_existente():
    existente = UsuarioFactory(email="vinculada@empresa.com", proveedor_auth=ProveedorAuth.LOCAL)

    usuario = oauth.obtener_o_crear_usuario(
        _info_valida(email="vinculada@empresa.com", sub="sub-999")
    )

    assert usuario.id == existente.id
    usuario.refresh_from_db()
    assert usuario.google_sub == "sub-999"


def test_obtener_o_crear_usuario_reconoce_por_google_sub():
    primero = oauth.obtener_o_crear_usuario(_info_valida(sub="sub-repetido"))
    segundo = oauth.obtener_o_crear_usuario(
        _info_valida(sub="sub-repetido", email="otra@empresa.com")
    )

    assert primero.id == segundo.id


def test_obtener_o_crear_usuario_dominio_no_permitido_falla(settings):
    settings.GOOGLE_DOMINIOS_PERMITIDOS = ["empresa.com"]

    with pytest.raises(PermissionDenied):
        oauth.obtener_o_crear_usuario(_info_valida(email="externo@otrodominio.com"))
