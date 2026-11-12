from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConfiguracionImportacionJiraView,
    GastoEjecutadoViewSet,
    ImportarHorasJiraView,
    IntegracionJiraProyectosView,
    RegistroEjecucionViewSet,
)

router = DefaultRouter()
router.register("registros-ejecucion", RegistroEjecucionViewSet, basename="registro-ejecucion")
router.register("gastos-ejecutados", GastoEjecutadoViewSet, basename="gasto-ejecutado")

urlpatterns = [
    path(
        "integraciones/jira/proyectos/",
        IntegracionJiraProyectosView.as_view(),
        name="integracion-jira-proyectos",
    ),
    path(
        "configuracion-importacion-jira/",
        ConfiguracionImportacionJiraView.as_view(),
        name="configuracion-importacion-jira",
    ),
    path(
        "integraciones/jira/importar/",
        ImportarHorasJiraView.as_view(),
        name="integracion-jira-importar",
    ),
    *router.urls,
]
