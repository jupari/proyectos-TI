"""URLs raíz del proyecto."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import SaludView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/salud/", SaludView.as_view(), name="salud"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.catalogos.urls")),
    path("api/v1/", include("apps.proyectos.urls")),
    path("api/v1/", include("apps.recursos.urls")),
    path("api/v1/", include("apps.tareas.urls")),
    path("api/v1/", include("apps.ejecucion.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
