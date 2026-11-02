import datetime

import django_filters

from apps.core.choices import EstadoCompromiso

from .models import CompromisoSeguimiento, Seguimiento


class FiltroSeguimiento(django_filters.FilterSet):
    fecha_corte__gte = django_filters.DateFilter(field_name="fecha_corte", lookup_expr="gte")
    fecha_corte__lte = django_filters.DateFilter(field_name="fecha_corte", lookup_expr="lte")

    class Meta:
        model = Seguimiento
        fields = ["proyecto", "periodicidad", "estado"]


class FiltroCompromisoSeguimiento(django_filters.FilterSet):
    vencidos = django_filters.BooleanFilter(method="filtrar_vencidos")

    class Meta:
        model = CompromisoSeguimiento
        fields = ["estado", "responsable"]

    def filtrar_vencidos(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            estado=EstadoCompromiso.ABIERTO, fecha_compromiso__lt=datetime.date.today()
        )
