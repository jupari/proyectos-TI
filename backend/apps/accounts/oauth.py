"""Servicio de Google OAuth 2.0 (Authorization Code + PKCE). Sin lógica de
vista aquí: las vistas de `apps/accounts/views.py` solo orquestan estas
funciones y traducen sus excepciones al sobre de error estándar.
"""

import secrets
from urllib.parse import urlencode

import requests as requests_lib
from django.conf import settings
from django.contrib.auth.models import Group
from django.core import signing
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.exceptions import ErrorOAuthNoConfigurado
from apps.accounts.models import Usuario
from apps.core.choices import ProveedorAuth, TipoEvento
from apps.core.services import registrar_evento

FIRMA_SALT = "accounts.oauth.state"
CADUCIDAD_STATE_SEGUNDOS = 600

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 (no es un secreto)


def _configurado():
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def _exigir_configurado():
    if not _configurado():
        raise ErrorOAuthNoConfigurado()


def construir_url_autorizacion(code_challenge):
    """Devuelve `(url_autorizacion, state)`. El `code_challenge` lo calcula y
    envía el frontend a partir de su propio `code_verifier` (que nunca pasa
    por el backend en esta llamada)."""
    _exigir_configurado()

    state = signing.dumps({"n": secrets.token_urlsafe(16)}, salt=FIRMA_SALT)
    parametros = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(parametros)}", state


def validar_state(state):
    try:
        signing.loads(state, salt=FIRMA_SALT, max_age=CADUCIDAD_STATE_SEGUNDOS)
    except signing.BadSignature as exc:
        raise ValidationError({"state": ["El parámetro state no es válido o venció."]}) from exc


def canjear_codigo(code, code_verifier):
    """`POST https://oauth2.googleapis.com/token` → devuelve el `id_token`."""
    _exigir_configurado()

    respuesta = requests_lib.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        },
        timeout=10,
    )
    if respuesta.status_code != 200:
        raise ValidationError({"code": ["No se pudo validar el código de autorización de Google."]})
    return respuesta.json()["id_token"]


def verificar_id_token(id_token_str):
    """Usa `google.oauth2.id_token.verify_oauth2_token`: valida firma, `iss`,
    `aud` y `exp`. Nunca se decodifica el token a mano."""
    _exigir_configurado()

    try:
        info = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError as exc:
        raise ValidationError({"id_token": ["El token de Google no es válido."]}) from exc

    if not info.get("email_verified"):
        raise ValidationError({"id_token": ["El correo de Google no está verificado."]})
    return info


def obtener_o_crear_usuario(info):
    """Busca por `google_sub`; si no, por `email` (y vincula); si no existe,
    crea el usuario con el rol `CONSULTA` por defecto."""
    email = info["email"]
    dominio = email.rsplit("@", 1)[-1].lower()
    dominios_permitidos = settings.GOOGLE_DOMINIOS_PERMITIDOS
    if dominios_permitidos and dominio not in dominios_permitidos:
        raise PermissionDenied(f"El dominio «{dominio}» no está autorizado para iniciar sesión.")

    google_sub = info["sub"]
    usuario = Usuario.objects.filter(google_sub=google_sub).first()
    if usuario is not None:
        return usuario

    usuario = Usuario.objects.filter(email=email).first()
    if usuario is not None:
        usuario.google_sub = google_sub
        usuario.save(update_fields=["google_sub"])
        registrar_evento(
            tipo_evento=TipoEvento.ACTUALIZACION,
            entidad="Usuario",
            entidad_id=usuario.id,
            descripcion=f"Se vinculó la cuenta de Google al usuario {usuario.email}.",
            usuario=usuario,
        )
        return usuario

    usuario = Usuario.objects.create(
        email=email,
        google_sub=google_sub,
        nombres=info.get("given_name", ""),
        apellidos=info.get("family_name", ""),
        avatar_url=info.get("picture"),
        proveedor_auth=ProveedorAuth.GOOGLE,
        is_active=True,
    )
    usuario.set_unusable_password()
    usuario.save(update_fields=["password"])

    rol_consulta = Group.objects.filter(rol_meta__codigo="CONSULTA").first()
    if rol_consulta:
        usuario.groups.add(rol_consulta)

    registrar_evento(
        tipo_evento=TipoEvento.CREACION,
        entidad="Usuario",
        entidad_id=usuario.id,
        descripcion=(
            f"Usuario creado automáticamente al iniciar sesión con Google: {usuario.email}."
        ),
        usuario=usuario,
    )
    return usuario
