"""Configuración para pruebas automáticas."""
from .base import *  # noqa: F403
from .base import env

DEBUG = False

DATABASES["default"]["NAME"] = env("POSTGRES_DB", default="seguimiento") + "_test"  # noqa: F405

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
