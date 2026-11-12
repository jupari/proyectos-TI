from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConfiguracionImportacionJiraView,
    GastoEjecutadoViewSet,
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
    *router.urls,
]
