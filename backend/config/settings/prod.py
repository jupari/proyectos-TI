"""Configuración de producción."""
from .base import *  # noqa: F403
from .base import BASE_DIR, env

DEBUG = False

# Render (y la mayoría de PaaS) terminan TLS en un proxy y reenvían la
# petición al contenedor por HTTP simple: sin este header, Django no sabe
# que la petición original era HTTPS y SECURE_SSL_REDIRECT entra en un
# bucle infinito de redirecciones.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

MIDDLEWARE.insert(  # noqa: F405
    1, "whitenoise.middleware.WhiteNoiseMiddleware"
)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = BASE_DIR / "staticfiles"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
