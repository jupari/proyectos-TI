import django_filters
from django.db.models import Q

from .models import Proyecto


class FiltroProyecto(django_filters.FilterSet):
    fecha_inicio_plan__gte = django_filters.DateFilter(
        field_name="fecha_inicio_plan", lookup_expr="gte"
    )
    fecha_fin_plan__lte = django_filters.DateFilter(field_name="fecha_fin_plan", lookup_expr="lte")
    mis_proyectos = django_filters.BooleanFilter(method="filtrar_mis_proyectos")

    class Meta:
        model = Proyecto
        fields = [
            "estado",
            "fase_operacion",
            "prioridad",
            "portafolio",
            "area_solicitante",
            "gerente",
            "lider_tecnico",
            "semaforo",
        ]

    def filtrar_mis_proyectos(self, queryset, name, value):
        if not value:
            return queryset
        usuario = self.request.user
        filtro = Q(gerente=usuario) | Q(lider_tecnico=usuario)
        recurso = getattr(usuario, "recurso", None)
        if recurso is not None:
            filtro |= Q(asignaciones__recurso=recurso, asignaciones__activo=True)
        return queryset.filter(filtro).distinct()
