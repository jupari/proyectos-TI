from django.urls import path

from .views import (
    EjecucionMensualView,
    ExportarTableroView,
    RecursosOcupacionView,
    ResumenGlobalView,
    TablaProyectosView,
    TareasResumenView,
)

urlpatterns = [
    path("tablero/resumen/", ResumenGlobalView.as_view(), name="tablero-resumen"),
    path("tablero/proyectos/", TablaProyectosView.as_view(), name="tablero-proyectos"),
    path(
        "tablero/ejecucion-mensual/",
        EjecucionMensualView.as_view(),
        name="tablero-ejecucion-mensual",
    ),
    path("tablero/recursos/", RecursosOcupacionView.as_view(), name="tablero-recursos"),
    path("tablero/tareas/", TareasResumenView.as_view(), name="tablero-tareas"),
    path("tablero/exportar/", ExportarTableroView.as_view(), name="tablero-exportar"),
]
