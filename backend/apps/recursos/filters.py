import django_filters

from .models import AsignacionRecurso, Recurso, TarifaRecurso


class FiltroRecurso(django_filters.FilterSet):
    sin_asignacion = django_filters.BooleanFilter(method="filtrar_sin_asignacion")

    class Meta:
        model = Recurso
        fields = ["tipo", "perfil", "usuario"]

    def filtrar_sin_asignacion(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.exclude(asignaciones__activo=True).distinct()


class FiltroTarifaRecurso(django_filters.FilterSet):
    class Meta:
        model = TarifaRecurso
        fields = ["recurso"]


class FiltroAsignacionRecurso(django_filters.FilterSet):
    class Meta:
        model = AsignacionRecurso
        fields = ["proyecto", "recurso", "fase"]
