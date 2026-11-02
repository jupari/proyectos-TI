import django_filters

from .models import Area, PerfilRecurso, Portafolio


class FiltroArea(django_filters.FilterSet):
    class Meta:
        model = Area
        fields = ["responsable"]


class FiltroPortafolio(django_filters.FilterSet):
    class Meta:
        model = Portafolio
        fields = ["responsable"]


class FiltroPerfilRecurso(django_filters.FilterSet):
    class Meta:
        model = PerfilRecurso
        fields = ["moneda"]
