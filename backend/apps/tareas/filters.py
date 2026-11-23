import datetime

import django_filters

from apps.core.choices import EstadoTarea

from .models import DependenciaTarea, Tarea

ESTADOS_NO_TERMINALES = [
    EstadoTarea.PENDIENTE,
    EstadoTarea.EN_PROGRESO,
    EstadoTarea.BLOQUEADA,
    EstadoTarea.EN_REVISION,
]


class FiltroTarea(django_filters.FilterSet):
    vencidas = django_filters.BooleanFilter(method="filtrar_vencidas")
    mis_tareas = django_filters.BooleanFilter(method="filtrar_mis_tareas")

    class Meta:
        model = Tarea
        fields = [
            "proyecto",
            "fase",
            "estado",
            "tipo",
            "prioridad",
            "responsable",
            "tarea_padre",
            "sprint",
            "creada_durante_ejecucion",
        ]

    def filtrar_vencidas(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            fecha_fin_plan__lt=datetime.date.today(), estado__in=ESTADOS_NO_TERMINALES
        )

    def filtrar_mis_tareas(self, queryset, name, value):
        if not value:
            return queryset
        recurso = getattr(self.request.user, "recurso", None)
        if recurso is None:
            return queryset.none()
        return queryset.filter(responsable=recurso)


class FiltroDependenciaTarea(django_filters.FilterSet):
    class Meta:
        model = DependenciaTarea
        fields = ["tarea_origen", "tarea_destino"]
