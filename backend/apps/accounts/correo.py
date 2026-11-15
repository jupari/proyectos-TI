"""Envío de correo de autenticación (fase 13): código de verificación en dos
pasos y enlace de recuperación de clave. Texto plano a propósito — es un
alcance básico, sin plantillas HTML.

Con `BREVO_API_KEY` configurada, el envío va por la API HTTP de Brevo
(`requests.post` normal, puerto 443) en vez del backend SMTP de Django:
Render (y varios PaaS gratuitos) bloquean las conexiones salientes por los
puertos SMTP habituales (25/465/587) para prevenir abuso, así que cualquier
proveedor por SMTP se cuelga ahí sin importar que las credenciales estén
bien. Sin `BREVO_API_KEY` (dev/test, o quien prefiera SMTP real), se usa
`django.core.mail.send_mail` de toda la vida.
"""

import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

from apps.core.exceptions import ErrorApi

logger = logging.getLogger("apps.accounts.correo")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
TIMEOUT_SEGUNDOS = 10


class ErrorEnvioCorreo(ErrorApi):
    status_code = 502
    codigo = "ERROR_CORREO"
    default_detail = "No se pudo enviar el correo. Intenta de nuevo en un momento."


def _enviar_via_api_brevo(asunto, mensaje, destinatario):
    try:
        respuesta = requests.post(
            BREVO_API_URL,
            json={
                "sender": {"email": settings.DEFAULT_FROM_EMAIL},
                "to": [{"email": destinatario}],
                "subject": asunto,
                "textContent": mensaje,
            },
            headers={
                "api-key": settings.BREVO_API_KEY,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.RequestException as exc:
        raise ErrorEnvioCorreo() from exc
    if respuesta.status_code >= 300:
        logger.error(
            "Brevo respondió %s al enviar a %s: %s",
            respuesta.status_code,
            destinatario,
            respuesta.text[:300],
        )
        raise ErrorEnvioCorreo()


def _enviar_via_smtp(asunto, mensaje, destinatario):
    try:
        # `EMAIL_TIMEOUT` (settings/base.py) evita que un SMTP colgado
        # bloquee el worker entero de gunicorn indefinidamente.
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("No se pudo enviar correo a %s: %s", destinatario, exc)
        raise ErrorEnvioCorreo() from exc


def _enviar(asunto, mensaje, destinatario):
    if settings.BREVO_API_KEY:
        _enviar_via_api_brevo(asunto, mensaje, destinatario)
    else:
        _enviar_via_smtp(asunto, mensaje, destinatario)


def enviar_codigo_2fa(usuario, codigo):
    _enviar(
        asunto="Tu código de verificación — Seguimiento TI",
        mensaje=(
            f"Hola {usuario.nombres},\n\n"
            f"Tu código de verificación es: {codigo}\n\n"
            f"Vence en {settings.OTP_LIFETIME_MINUTES} minutos. Si no intentaste "
            "iniciar sesión, ignora este correo."
        ),
        destinatario=usuario.email,
    )


def enviar_enlace_recuperacion(usuario, enlace):
    _enviar(
        asunto="Recupera tu clave — Seguimiento TI",
        mensaje=(
            f"Hola {usuario.nombres},\n\n"
            "Pediste recuperar tu clave. Entra a este enlace para elegir una nueva "
            f"(vence en {settings.PASSWORD_RESET_TIMEOUT // 60} minutos):\n\n{enlace}\n\n"
            "Si no fuiste tú, ignora este correo: tu clave actual sigue siendo válida."
        ),
        destinatario=usuario.email,
    )
