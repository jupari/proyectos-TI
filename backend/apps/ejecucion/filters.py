import django_filters

from .models import GastoEjecutado, RegistroEjecucion


class FiltroRegistroEjecucion(django_filters.FilterSet):
    periodo_inicio__gte = django_filters.DateFilter(field_name="periodo_inicio", lookup_expr="gte")
    periodo_fin__lte = django_filters.DateFilter(field_name="periodo_fin", lookup_expr="lte")
    mis_registros = django_filters.BooleanFilter(method="filtrar_mis_registros")

    class Meta:
        model = RegistroEjecucion
        fields = ["proyecto", "tarea", "recurso", "periodicidad", "estado_aprobacion"]

    def filtrar_mis_registros(self, queryset, name, value):
        if not value:
            return queryset
        recurso = getattr(self.request.user, "recurso", None)
        if recurso is None:
            return queryset.none()
        return queryset.filter(recurso=recurso)


class FiltroGastoEjecutado(django_filters.FilterSet):
    class Meta:
        model = GastoEjecutado
        fields = ["proyecto", "rubro", "estado_aprobacion"]
