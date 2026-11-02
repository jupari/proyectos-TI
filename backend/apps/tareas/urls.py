from rest_framework.routers import DefaultRouter

from .views import DependenciaTareaViewSet, TareaViewSet

router = DefaultRouter()
router.register("tareas", TareaViewSet, basename="tarea")
router.register("dependencias-tarea", DependenciaTareaViewSet, basename="dependencia-tarea")

urlpatterns = router.urls
