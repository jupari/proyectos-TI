"""Configuración base, compartida por dev, prod y test."""
import datetime
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # terceros
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # apps propias
    "apps.core",
    "apps.accounts",
    "apps.catalogos",
    "apps.recursos",
    "apps.proyectos",
    "apps.tareas",
    "apps.ejecucion",
    "apps.seguimiento",
    "apps.expediente",
    "apps.tablero",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.MiddlewareUsuarioActual",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
    }
}

# Política básica de contraseñas (fase 13): longitud mínima + variedad de
# caracteres + no estar en la lista de claves comunes. Los usuarios creados
# por un admin reciben una clave temporal aleatoria y no pasan por acá (ver
# `UsuarioAdminEscrituraSerializer.create`); eligen su propia clave recién en
# `CambiarClaveSerializer`, que sí llama a `validate_password`.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "apps.accounts.validadores.ValidadorComplejidadClave"},
]

AUTH_USER_MODEL = "accounts.Usuario"

LANGUAGE_CODE = "es-co"
TIME_ZONE = env("TIME_ZONE", default="America/Bogota")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MONEDA_BASE = env("MONEDA_BASE", default="COP")
MAX_UPLOAD_MB = env.int("MAX_UPLOAD_MB", default=25)
EXTENSIONES_PERMITIDAS = env.list("EXTENSIONES_PERMITIDAS", default=[])

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.PaginacionEstandar",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.manejador_excepciones",
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/min",
        "verificar-codigo": "10/min",
        # DRF solo admite un período simple (sec/min/hour/day) en el rate,
        # no "N por cada X minutos" — "3/hour" es la aproximación más
        # cercana a la intención original de "3 cada 10 minutos".
        "reenviar-codigo": "3/hour",
        "recuperar-clave": "3/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API Seguimiento de Proyectos TI",
    "DESCRIPTION": "API del panel administrativo de seguimiento de proyectos de TI.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Varios modelos tienen un campo `estado` con su propio TextChoices
    # (docs/modelo-datos.md): sin esto, drf-spectacular genera nombres de
    # enum colisionados ("Estado2f9Enum") al no poder distinguirlos por nombre
    # de campo. Se añaden aquí a medida que cada fase expone el campo en un
    # serializer.
    "ENUM_NAME_OVERRIDES": {
        "EstadoProyectoEnum": "apps.core.choices.EstadoProyecto",
        "EstadoFaseEnum": "apps.core.choices.EstadoFase",
        "EstadoHitoEnum": "apps.core.choices.EstadoHito",
        "EstadoTareaEnum": "apps.core.choices.EstadoTarea",
        "TipoTareaEnum": "apps.core.choices.TipoTarea",
        "TipoDependenciaEnum": "apps.core.choices.TipoDependencia",
        "SemaforoCalculadoEnum": "apps.core.choices.Semaforo",
    },
}

GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
GOOGLE_REDIRECT_URI = env("GOOGLE_REDIRECT_URI", default="")
GOOGLE_DOMINIOS_PERMITIDOS = env.list("GOOGLE_DOMINIOS_PERMITIDOS", default=[])

# Integración Jira + Tempo (fase 12); vacío si no se usa.
JIRA_BASE_URL = env("JIRA_BASE_URL", default="")
JIRA_EMAIL = env("JIRA_EMAIL", default="")
JIRA_API_TOKEN = env("JIRA_API_TOKEN", default="")
TEMPO_API_TOKEN = env("TEMPO_API_TOKEN", default="")

# Envío de correo (fase 13: código de verificación en dos pasos y enlace de
# recuperación de clave). `EMAIL_BACKEND` lo define cada entorno
# (dev/test/prod) por separado, no acá.
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)
# URL pública del frontend, para construir el enlace de recuperación de
# clave que va dentro del correo (el backend no la conoce por ningún otro
# medio: no hay nada que la derive de ALLOWED_HOSTS ni de CORS_ALLOWED_ORIGINS).
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:4200")

OTP_LIFETIME_MINUTES = env.int("OTP_LIFETIME_MINUTES", default=10)
OTP_MAX_INTENTOS = env.int("OTP_MAX_INTENTOS", default=5)
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT", default=3600)
