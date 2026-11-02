from django.db.models import Q

from apps.core.roles import ROLES_ALCANCE_TOTAL, codigos_roles_de, prefijo_proyecto


class MixinAlcancePorRol:
    """Acota el queryset de un `ViewSet` al alcance del rol del usuario
    (PLAN.md §5): ADMIN/PMO/CONSULTA ven todo; LIDER solo lo de sus
    proyectos (como gerente o líder técnico); RECURSO solo lo de los
    proyectos donde tiene una asignación activa, y además solo sus propias
    tareas y registros de ejecución. Un usuario sin rol no ve nada.
    """

    def filtrar_por_rol(self, queryset):
        usuario = self.request.user
        if not usuario or not usuario.is_authenticated:
            return queryset.none()

        codigos = codigos_roles_de(usuario)
        if codigos & ROLES_ALCANCE_TOTAL:
            return queryset
        if "LIDER" in codigos:
            return self._alcance_lider(queryset, usuario)
        if "RECURSO" in codigos:
            return self._alcance_recurso(queryset, usuario)
        return queryset.none()

    def _alcance_lider(self, queryset, usuario):
        prefijo = prefijo_proyecto(queryset.model)
        if prefijo is None:
            return queryset.none()
        return queryset.filter(
            Q(**{f"{prefijo}gerente": usuario}) | Q(**{f"{prefijo}lider_tecnico": usuario})
        ).distinct()

    def _alcance_recurso(self, queryset, usuario):
        recurso = getattr(usuario, "recurso", None)
        if recurso is None:
            return queryset.none()

        prefijo = prefijo_proyecto(queryset.model)
        if prefijo is None:
            return queryset.none()

        base = queryset.filter(
            **{
                f"{prefijo}asignaciones__recurso": recurso,
                f"{prefijo}asignaciones__activo": True,
            }
        ).distinct()

        nombre_modelo = queryset.model.__name__
        if nombre_modelo == "Tarea":
            return base.filter(responsable=recurso)
        if nombre_modelo in ("RegistroEjecucion", "AsignacionRecurso"):
            return base.filter(recurso=recurso)
        return base
