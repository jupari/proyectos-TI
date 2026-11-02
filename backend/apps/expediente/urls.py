from rest_framework.routers import DefaultRouter

from .views import BitacoraViewSet, DocumentoExpedienteViewSet

router = DefaultRouter()
router.register(
    "documentos-expediente", DocumentoExpedienteViewSet, basename="documento-expediente"
)
router.register("bitacora", BitacoraViewSet, basename="bitacora")

urlpatterns = router.urls
