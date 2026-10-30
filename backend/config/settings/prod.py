"""Configuración de producción."""
from .base import *  # noqa: F403
from .base import BASE_DIR, env

DEBUG = False

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

MIDDLEWARE.insert(  # noqa: F405
    1, "whitenoise.middleware.WhiteNoiseMiddleware"
)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = BASE_DIR / "staticfiles"
