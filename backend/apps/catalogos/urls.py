from rest_framework.routers import DefaultRouter

from .views import AreaViewSet, PerfilRecursoViewSet, PortafolioViewSet

router = DefaultRouter()
router.register("areas", AreaViewSet, basename="area")
router.register("portafolios", PortafolioViewSet, basename="portafolio")
router.register("perfiles-recurso", PerfilRecursoViewSet, basename="perfil-recurso")

urlpatterns = router.urls
