from rest_framework.routers import DefaultRouter

from .views import GastoEjecutadoViewSet, RegistroEjecucionViewSet

router = DefaultRouter()
router.register("registros-ejecucion", RegistroEjecucionViewSet, basename="registro-ejecucion")
router.register("gastos-ejecutados", GastoEjecutadoViewSet, basename="gasto-ejecutado")

urlpatterns = router.urls
