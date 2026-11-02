from rest_framework.routers import DefaultRouter

from .views import AsignacionRecursoViewSet, RecursoViewSet, TarifaRecursoViewSet

router = DefaultRouter()
router.register("recursos", RecursoViewSet, basename="recurso")
router.register("tarifas-recurso", TarifaRecursoViewSet, basename="tarifa-recurso")
router.register("asignaciones", AsignacionRecursoViewSet, basename="asignacion")

urlpatterns = router.urls
