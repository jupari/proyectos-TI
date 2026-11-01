import django_filters


class FiltroBase(django_filters.FilterSet):
    """FilterSet base reutilizable: rango de fechas (`desde`/`hasta`) y `activo`.

    Un FilterSet concreto fija `campo_fecha_rango` con el nombre del campo de
    fecha sobre el que aplican `desde`/`hasta` (p. ej. `fecha_inicio_plan`).
    """

    campo_fecha_rango = None

    desde = django_filters.DateFilter(method="filtrar_desde")
    hasta = django_filters.DateFilter(method="filtrar_hasta")
    activo = django_filters.BooleanFilter()

    def filtrar_desde(self, queryset, name, value):
        if not self.campo_fecha_rango:
            return queryset
        return queryset.filter(**{f"{self.campo_fecha_rango}__gte": value})

    def filtrar_hasta(self, queryset, name, value):
        if not self.campo_fecha_rango:
            return queryset
        return queryset.filter(**{f"{self.campo_fecha_rango}__lte": value})
