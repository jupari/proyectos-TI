"""Permisos reutilizables de docs/api-contrato.md §8."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.core.roles import codigos_roles_de, resolver_proyecto_de_instancia


class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        return "ADMIN" in codigos_roles_de(request.user)


class EsPmoOAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(codigos_roles_de(request.user) & {"ADMIN", "PMO"})


class EsLiderDelProyecto(BasePermission):
    """Autoriza al gerente o líder técnico del proyecto del objeto, o a
    ADMIN/PMO. Debe combinarse con `MixinAlcancePorRol` en el `ViewSet` para
    que el listado no filtre menos que el detalle."""

    def has_object_permission(self, request, view, obj):
        codigos = codigos_roles_de(request.user)
        if codigos & {"ADMIN", "PMO"}:
            return True
        if "LIDER" not in codigos:
            return False
        proyecto = resolver_proyecto_de_instancia(obj)
        if proyecto is None:
            return False
        usuario = request.user
        return proyecto.gerente_id == usuario.id or proyecto.lider_tecnico_id == usuario.id


class EsDuenoDelRegistro(BasePermission):
    """Autoriza a quien registró el objeto (`registrado_por`), a quien es el
    `recurso.usuario` del objeto, o a quien es el `usuario` de su
    `responsable` (p. ej. una `Tarea`); ADMIN y PMO siempre pasan.

    Prueba las tres señales de pertenencia posibles en vez de quedarse con
    la primera que exista como atributo: un `registrado_por` nulo (p. ej.
    un registro que no lo usa) no debe bloquear la comprobación por
    `recurso`."""

    def has_object_permission(self, request, view, obj):
        codigos = codigos_roles_de(request.user)
        if codigos & {"ADMIN", "PMO"}:
            return True

        usuario = request.user

        registrado_por_id = getattr(obj, "registrado_por_id", None)
        if registrado_por_id is not None and registrado_por_id == usuario.id:
            return True

        recurso = getattr(obj, "recurso", None)
        if recurso is not None and recurso.usuario_id == usuario.id:
            return True

        responsable = getattr(obj, "responsable", None)
        if responsable is not None and getattr(responsable, "usuario_id", None) == usuario.id:
            return True

        return False


class SoloLectura(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class EsAdminOSoloLectura(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return "ADMIN" in codigos_roles_de(request.user)


class EsPmoOAdminOSoloLectura(BasePermission):
    """Lectura para cualquier autenticado, escritura solo ADMIN y PMO
    (catálogos, docs/api-contrato.md §3)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(codigos_roles_de(request.user) & {"ADMIN", "PMO"})
