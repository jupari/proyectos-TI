"""Envío de correo de autenticación (fase 13): código de verificación en dos
pasos y enlace de recuperación de clave. Texto plano a propósito — es un
alcance básico, sin plantillas HTML."""

from django.conf import settings
from django.core.mail import send_mail


def enviar_codigo_2fa(usuario, codigo):
    send_mail(
        subject="Tu código de verificación — Seguimiento TI",
        message=(
            f"Hola {usuario.nombres},\n\n"
            f"Tu código de verificación es: {codigo}\n\n"
            f"Vence en {settings.OTP_LIFETIME_MINUTES} minutos. Si no intentaste "
            "iniciar sesión, ignora este correo."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
    )


def enviar_enlace_recuperacion(usuario, enlace):
    send_mail(
        subject="Recupera tu clave — Seguimiento TI",
        message=(
            f"Hola {usuario.nombres},\n\n"
            "Pediste recuperar tu clave. Entra a este enlace para elegir una nueva "
            f"(vence en {settings.PASSWORD_RESET_TIMEOUT // 60} minutos):\n\n{enlace}\n\n"
            "Si no fuiste tú, ignora este correo: tu clave actual sigue siendo válida."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
    )
