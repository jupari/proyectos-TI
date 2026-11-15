"""Envío de correo de autenticación (fase 13): código de verificación en dos
pasos y enlace de recuperación de clave. Texto plano a propósito — es un
alcance básico, sin plantillas HTML."""

import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.core.exceptions import ErrorApi

logger = logging.getLogger("apps.accounts.correo")


class ErrorEnvioCorreo(ErrorApi):
    status_code = 502
    codigo = "ERROR_CORREO"
    default_detail = "No se pudo enviar el correo. Intenta de nuevo en un momento."


def _enviar(asunto, mensaje, destinatario):
    try:
        # Sin `timeout`, un SMTP que se cuelga (red, IP bloqueada, servidor
        # caído) bloquea la petición indefinidamente: el worker de gunicorn
        # termina muerto por su propio timeout (o por quedarse sin memoria),
        # tumbando con un 500 opaco en vez de un error claro para la persona.
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
