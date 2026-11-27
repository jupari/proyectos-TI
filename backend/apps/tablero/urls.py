from django.urls import path

from .views import (
    BurndownSprintView,
    EjecucionMensualView,
    ExportarTableroView,
    MiTrabajoExportarView,
    MiTrabajoView,
    PlanCostosProyectoView,
    RecursosOcupacionView,
    ResumenGlobalView,
    SprintsProyectoView,
    TablaProyectosPorPeriodoView,
    TablaProyectosView,
    TareasResumenView,
)

urlpatterns = [
    path("tablero/resumen/", ResumenGlobalView.as_view(), name="tablero-resumen"),
    path("tablero/proyectos/", TablaProyectosView.as_view(), name="tablero-proyectos"),
    path(
        "tablero/proyectos-por-periodo/",
        TablaProyectosPorPeriodoView.as_view(),
        name="tablero-proyectos-por-periodo",
    ),
    path(
        "tablero/plan-costos/",
        PlanCostosProyectoView.as_view(),
        name="tablero-plan-costos",
    ),
    path(
        "tablero/ejecucion-mensual/",
        EjecucionMensualView.as_view(),
        name="tablero-ejecucion-mensual",
    ),
    path("tablero/recursos/", RecursosOcupacionView.as_view(), name="tablero-recursos"),
    path("tablero/tareas/", TareasResumenView.as_view(), name="tablero-tareas"),
    path(
        "tablero/mi-trabajo/exportar/",
        MiTrabajoExportarView.as_view(),
        name="tablero-mi-trabajo-exportar",
    ),
    path("tablero/sprints/", SprintsProyectoView.as_view(), name="tablero-sprints"),
    path(
        "tablero/sprints/<uuid:pk>/burndown/",
        BurndownSprintView.as_view(),
        name="tablero-sprint-burndown",
    ),
    path("tablero/mi-trabajo/", MiTrabajoView.as_view(), name="tablero-mi-trabajo"),
    path("tablero/exportar/", ExportarTableroView.as_view(), name="tablero-exportar"),
]
