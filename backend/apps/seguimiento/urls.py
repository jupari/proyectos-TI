from rest_framework.routers import DefaultRouter

from .views import CompromisoSeguimientoViewSet, SeguimientoViewSet

router = DefaultRouter()
router.register("seguimientos", SeguimientoViewSet, basename="seguimiento")
router.register(
    "compromisos-seguimiento", CompromisoSeguimientoViewSet, basename="compromiso-seguimiento"
)

urlpatterns = router.urls
