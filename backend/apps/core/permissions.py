"""Permisos reutilizables de docs/api-contrato.md §8."""

from django.db.models import Q
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
    que el listado no filtre menos que el detalle.

    También implementa `has_permission` para que un `ViewSet` de un
    sub-recurso con FK directa a `Proyecto` (fases, hitos, rubros,
    asignaciones, ...) pueda usar esta clase tal cual, sin envolverla: en
    `create` no hay objeto todavía sobre el que aplicar
    `has_object_permission`, así que se resuelve el proyecto desde
    `campo_proyecto` en el cuerpo de la petición. Un `ViewSet` que cree el
    `Proyecto` mismo (no un sub-recurso) debe seguir sobreescribiendo
    `has_permission` para `create`, porque aquí no hay ningún `campo_proyecto`
    que mirar y el valor por defecto sería autorizar de más."""

    campo_proyecto = "proyecto"

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        if codigos & {"ADMIN", "PMO"}:
            return True
        if request.method in SAFE_METHODS:
            return True
        if "LIDER" not in codigos:
            return False
        if getattr(view, "action", None) != "create":
            return True

        from apps.proyectos.models import Proyecto

        proyecto_id = request.data.get(self.campo_proyecto)
        if not proyecto_id:
            return True
        usuario = request.user
        return Proyecto.objects.filter(
            Q(pk=proyecto_id) & (Q(gerente=usuario) | Q(lider_tecnico=usuario))
        ).exists()

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


class EsLiderDelProyectoOLectura(EsLiderDelProyecto):
    """Como `EsLiderDelProyecto`, pero la lectura (`SAFE_METHODS`) no se
    restringe a nivel de objeto: la usan los `ViewSet` de sub-recursos de
    proyecto (fases, hitos, rubros, asignaciones) cuyo alcance de *listado*
    ya acota `MixinAlcancePorRol`; el detalle no necesita ocultarse a quien
    ya conoce el id. No usar esta variante para permisos donde la lectura
    misma deba quedar restringida al dueño (para eso está la clase base)."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return super().has_object_permission(request, view, obj)


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
