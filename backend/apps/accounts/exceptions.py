from apps.core.exceptions import ErrorApi


class ErrorOAuthNoConfigurado(ErrorApi):
    status_code = 503
    codigo = "OAUTH_NO_CONFIGURADO"
    default_detail = "El inicio de sesión con Google no está configurado en este entorno."
