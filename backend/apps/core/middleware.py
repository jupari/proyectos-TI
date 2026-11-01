import contextvars

_peticion_actual_var = contextvars.ContextVar("peticion_actual", default=None)


class MiddlewareUsuarioActual:
    """Guarda la petición actual en un ContextVar (seguro con concurrencia)
    para que `apps.core.signals` pueda resolver el usuario autenticado.

    No se guarda el usuario ya resuelto: en la autenticación JWT de DRF,
    `request.user` solo queda poblado dentro de la vista (en
    `APIView.initial()`), que corre *después* de que este middleware ya haya
    llamado a `get_response`. Por eso se guarda la referencia a la petición y
    `obtener_usuario_actual()` lee `request.user` en el momento en que se
    invoca (desde la señal, ya con la autenticación resuelta).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _peticion_actual_var.set(request)
        try:
            return self.get_response(request)
        finally:
            _peticion_actual_var.reset(token)


def obtener_usuario_actual():
    request = _peticion_actual_var.get()
    if request is None:
        return None
    usuario = getattr(request, "user", None)
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        return None
    return usuario
