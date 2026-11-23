from rest_framework.authentication import BaseAuthentication


class SinAutenticacion(BaseAuthentication):
    """Para los endpoints públicos de acceso (login, código 2FA, recuperación):
    nunca valida el `Authorization` — un Bearer vencido de una sesión anterior no
    debe dar 401 antes de revisar el código — pero declara el esquema `Bearer`
    para que DRF siga respondiendo 401 (y no 403) cuando las credenciales son
    incorrectas."""

    def authenticate(self, request):
        return None

    def authenticate_header(self, request):
        return "Bearer"
