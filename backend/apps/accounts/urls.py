from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CambiarClaveView,
    GoogleAutorizarView,
    GoogleCallbackView,
    LoginView,
    LogoutView,
    RolViewSet,
    UsuarioViewSet,
    YoView,
)

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("roles", RolViewSet, basename="rol")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/yo/", YoView.as_view(), name="auth-yo"),
    path("auth/cambiar-clave/", CambiarClaveView.as_view(), name="auth-cambiar-clave"),
    path("auth/google/autorizar/", GoogleAutorizarView.as_view(), name="auth-google-autorizar"),
    path("auth/google/callback/", GoogleCallbackView.as_view(), name="auth-google-callback"),
    *router.urls,
]
