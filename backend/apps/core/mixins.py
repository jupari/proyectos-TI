class MixinAlcancePorRol:
    """Interfaz que cada ViewSet de negocio usa desde `get_queryset()` para
    acotar el listado al alcance del rol del usuario autenticado.

    La implementación real (ADMIN/PMO ven todo, LIDER solo sus proyectos,
    RECURSO solo donde está asignado, CONSULTA solo lectura) llega en la
    fase 03; aquí solo se define la interfaz para que las fases 05+ ya
    llamen a `filtrar_por_rol()` desde ahora.
    """

    def filtrar_por_rol(self, queryset):
        # TODO fase-03: aplicar el filtrado real según el rol de self.request.user.
        return queryset
