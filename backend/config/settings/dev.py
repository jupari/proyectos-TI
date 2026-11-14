"""Configuración de desarrollo."""
from .base import *  # noqa: F403

DEBUG = True

# Los correos (código 2FA, enlace de recuperación) se imprimen en la
# consola del backend (`docker compose logs backend`) en vez de enviarse de
# verdad: así no hace falta tener credenciales SMTP reales para desarrollar.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
