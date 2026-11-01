"""Permisos reutilizables de docs/api-contrato.md §8.

En esta fase quedan vacíos de lógica de rol (solo exigen autenticación);
la fase 03 los completa con la matriz de permisos real.
"""

from rest_framework.permissions import BasePermission


class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        # TODO fase-03: exigir que el usuario tenga el rol ADMIN.
        return bool(request.user and request.user.is_authenticated)


class EsPmoOAdmin(BasePermission):
    def has_permission(self, request, view):
        # TODO fase-03: exigir rol PMO o ADMIN.
        return bool(request.user and request.user.is_authenticated)


class EsLiderDelProyecto(BasePermission):
    def has_object_permission(self, request, view, obj):
        # TODO fase-03: exigir que request.user sea el líder técnico (o gerente)
        # del proyecto al que pertenece `obj`.
        return bool(request.user and request.user.is_authenticated)


class EsDuenoDelRegistro(BasePermission):
    def has_object_permission(self, request, view, obj):
        # TODO fase-03: exigir que `obj` pertenezca al usuario (p. ej. su propio
        # registro de ejecución o su propia tarea asignada).
        return bool(request.user and request.user.is_authenticated)


class SoloLectura(BasePermission):
    def has_permission(self, request, view):
        # TODO fase-03: cuando se complete, seguirá siendo solo lectura para
        # el rol CONSULTA; aquí solo exige autenticación.
        return bool(request.user and request.user.is_authenticated)


class EsAdminOSoloLectura(BasePermission):
    def has_permission(self, request, view):
        # TODO fase-03: permitir escritura solo a ADMIN; lectura a cualquier
        # usuario autenticado.
        return bool(request.user and request.user.is_authenticated)
