from datetime import UTC, datetime

from django.db import connection
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import PaginacionEstandar
from apps.core.serializers import RespuestaSaludSerializer

VERSION = "0.1.0"


class SaludView(APIView):
    """Endpoint público de verificación de vida y conexión a base de datos."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Estado de salud de la API",
        description="Endpoint público que confirma que la API responde y que la base de "
        "datos está alcanzable.",
        responses=RespuestaSaludSerializer,
    )
    def get(self, request):
        try:
            connection.ensure_connection()
            estado_base_datos = "ok"
        except Exception:
            estado_base_datos = "error"

        return Response(
            {
                "estado": "ok",
                "version": VERSION,
                "base_datos": estado_base_datos,
                "hora": datetime.now(UTC).isoformat(),
            }
        )


class _ComunViewSetMixin:
    """Comportamiento compartido por ViewSetBase y ViewSetSoloLectura."""

    pagination_class = PaginacionEstandar
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    serializer_lectura_class = None
    serializer_escritura_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        return queryset

    def get_serializer_class(self):
        lectura = self.serializer_lectura_class or self.serializer_escritura_class
        escritura = self.serializer_escritura_class or self.serializer_lectura_class
        if self.action in ("list", "retrieve"):
            return lectura or self.serializer_class
        return escritura or self.serializer_class


class ViewSetBase(_ComunViewSetMixin, viewsets.ModelViewSet):
    """ModelViewSet base de las apps de negocio (fases 05 en adelante)."""

    def perform_destroy(self, instance):
        usuario = self.request.user if self.request.user.is_authenticated else None
        instance.eliminar_logico(usuario=usuario)


class ViewSetSoloLectura(_ComunViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """ReadOnlyModelViewSet base para bitácora y tablero."""
