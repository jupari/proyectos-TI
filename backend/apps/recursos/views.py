from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.mixins import MixinAlcancePorRol
from apps.core.permissions import EsLiderDelProyectoOLectura, EsPmoOAdminOSoloLectura
from apps.core.views import ViewSetBase

from .filters import FiltroAsignacionRecurso, FiltroRecurso, FiltroTarifaRecurso
from .models import AsignacionRecurso, Recurso, TarifaRecurso
from .serializers import AsignacionRecursoSerializer, RecursoSerializer, TarifaRecursoSerializer
from .services import carga_recurso


class RecursoViewSet(ViewSetBase):
    queryset = Recurso.objects.select_related("perfil", "usuario")
    serializer_lectura_class = RecursoSerializer
    serializer_escritura_class = RecursoSerializer
    permission_classes = [EsPmoOAdminOSoloLectura]
    filterset_class = FiltroRecurso
    search_fields = ["nombre", "email"]
    ordering_fields = ["nombre", "capacidad_horas_mes"]

    @extend_schema(
        summary="Historial de tarifas del recurso", responses=TarifaRecursoSerializer(many=True)
    )
    @action(detail=True, methods=["get"])
    def tarifas(self, request, pk=None):
        recurso = self.get_object()
        serializer = TarifaRecursoSerializer(
            recurso.tarifas.filter(activo=True).order_by("-vigente_desde"), many=True
        )
        return Response(serializer.data)

    @extend_schema(
        summary="Carga mensual del recurso",
        description="Horas planeadas por mes entre `desde` y `hasta`, prorrateadas por días "
        "calendario de intersección con cada asignación (docs/plan/fase-06 §6.1).",
        parameters=[
            OpenApiParameter("desde", str, description="YYYY-MM-DD", required=True),
            OpenApiParameter("hasta", str, description="YYYY-MM-DD", required=True),
        ],
        responses={200: {"type": "array", "items": {"type": "object"}}},
    )
    @action(detail=True, methods=["get"])
    def carga(self, request, pk=None):
        recurso = self.get_object()
        desde = parse_date(request.query_params.get("desde", ""))
        hasta = parse_date(request.query_params.get("hasta", ""))
        if not desde or not hasta:
            raise ValidationError(
                {"desde": ["Debe indicar ?desde= y ?hasta= en formato YYYY-MM-DD."]}
            )
        return Response(carga_recurso(recurso, desde, hasta))

    @extend_schema(
        summary="Asignaciones del recurso", responses=AsignacionRecursoSerializer(many=True)
    )
    @action(detail=True, methods=["get"])
    def asignaciones(self, request, pk=None):
        recurso = self.get_object()
        serializer = AsignacionRecursoSerializer(
            recurso.asignaciones.filter(activo=True), many=True
        )
        return Response(serializer.data)


class TarifaRecursoViewSet(ViewSetBase):
    queryset = TarifaRecurso.objects.select_related("recurso")
    serializer_lectura_class = TarifaRecursoSerializer
    serializer_escritura_class = TarifaRecursoSerializer
    permission_classes = [EsPmoOAdminOSoloLectura]
    filterset_class = FiltroTarifaRecurso
    ordering_fields = ["vigente_desde"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        datos = dict(serializer.data)
        datos["avisos"] = getattr(serializer, "avisos", [])
        headers = self.get_success_headers(serializer.data)
        return Response(datos, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        datos = dict(serializer.data)
        datos["avisos"] = getattr(serializer, "avisos", [])
        return Response(datos)


class AsignacionRecursoViewSet(MixinAlcancePorRol, ViewSetBase):
    serializer_lectura_class = AsignacionRecursoSerializer
    serializer_escritura_class = AsignacionRecursoSerializer
    permission_classes = [EsLiderDelProyectoOLectura]
    filterset_class = FiltroAsignacionRecurso
    ordering_fields = ["fecha_desde"]

    def get_queryset(self):
        queryset = AsignacionRecurso.objects.select_related("proyecto", "recurso", "fase")
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        return self.filtrar_por_rol(queryset)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        datos = dict(serializer.data)
        datos["advertencias"] = getattr(serializer, "advertencias", [])
        headers = self.get_success_headers(serializer.data)
        return Response(datos, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        datos = dict(serializer.data)
        datos["advertencias"] = getattr(serializer, "advertencias", [])
        return Response(datos)
