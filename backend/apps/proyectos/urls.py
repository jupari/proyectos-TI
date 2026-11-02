from rest_framework.routers import DefaultRouter

from .views import FaseProyectoViewSet, HitoViewSet, ProyectoViewSet, RubroPresupuestoViewSet

router = DefaultRouter()
router.register("proyectos", ProyectoViewSet, basename="proyecto")
router.register("fases-proyecto", FaseProyectoViewSet, basename="fase-proyecto")
router.register("hitos", HitoViewSet, basename="hito")
router.register("rubros-presupuesto", RubroPresupuestoViewSet, basename="rubro-presupuesto")

urlpatterns = router.urls
