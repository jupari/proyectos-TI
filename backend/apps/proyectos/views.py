from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from apps.core.choices import EstadoAprobacion
from apps.core.exceptions import ErrorConflicto
from apps.core.mixins import MixinAlcancePorRol
from apps.core.permissions import EsLiderDelProyecto
from apps.core.roles import codigos_roles_de
from apps.core.views import ViewSetBase
from apps.tablero.services import resumen_ejecucion as calcular_resumen_ejecucion

from .filters import FiltroProyecto
from .models import FaseProyecto, Hito, Proyecto, RubroPresupuesto
from .serializers import (
    FaseProyectoSerializer,
    HitoSerializer,
    ProyectoDetalleSerializer,
    ProyectoEscrituraSerializer,
    ProyectoListaSerializer,
    RubroPresupuestoSerializer,
)
from .services import cambiar_estado


class PermisoProyecto(EsLiderDelProyecto):
    """Crear exige ADMIN o PMO; borrar exige ADMIN; editar exige ser
    gerente/líder técnico del proyecto (o ADMIN/PMO); leer no se restringe
    a nivel de objeto (el alcance de listado ya lo acota `MixinAlcancePorRol`)."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        if view.action == "create":
            return bool(codigos & {"ADMIN", "PMO"})
        if view.action == "destroy":
            return "ADMIN" in codigos
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return super().has_object_permission(request, view, obj)


class PermisoSubRecursoProyecto(EsLiderDelProyecto):
    """Igual que `EsLiderDelProyecto` para editar/borrar, más la comprobación
    en creación (sin objeto todavía) de que el `proyecto` enviado es uno de
    los que lidera, cuando el usuario es LIDER."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        if codigos & {"ADMIN", "PMO"}:
            return True
        if "LIDER" not in codigos:
            return request.method in SAFE_METHODS
        if view.action == "create":
            proyecto_id = request.data.get("proyecto")
            if not proyecto_id:
                return True
            return Proyecto.objects.filter(
                Q(pk=proyecto_id) & (Q(gerente=request.user) | Q(lider_tecnico=request.user))
            ).exists()
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return super().has_object_permission(request, view, obj)


class ProyectoViewSet(MixinAlcancePorRol, ViewSetBase):
    serializer_lectura_class = ProyectoListaSerializer
    serializer_escritura_class = ProyectoEscrituraSerializer
    permission_classes = [PermisoProyecto]
    filterset_class = FiltroProyecto
    search_fields = ["codigo", "nombre"]
    ordering_fields = [
        "codigo",
        "nombre",
        "estado",
        "prioridad",
        "fecha_inicio_plan",
        "fecha_fin_plan",
    ]

    def get_queryset(self):
        queryset = Proyecto.objects.select_related(
            "area_solicitante", "portafolio", "gerente", "lider_tecnico"
        )
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("fases", "hitos", "rubros")
        return self.filtrar_por_rol(queryset)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProyectoDetalleSerializer
        return super().get_serializer_class()

    def perform_destroy(self, instance):
        tiene_ejecucion_aprobada = instance.registros_ejecucion.filter(
            activo=True, estado_aprobacion=EstadoAprobacion.APROBADO
        ).exists()
        if tiene_ejecucion_aprobada:
            raise ErrorConflicto("No se puede eliminar un proyecto con ejecución aprobada.")
        super().perform_destroy(instance)

    @extend_schema(
        summary="Cambia el estado del proyecto",
        description="Valida la transición contra el grafo de estados y sus precondiciones "
        "(docs/modelo-datos.md §3) y registra el cambio en la bitácora.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "estado": {"type": "string"},
                    "observacion": {"type": "string"},
                },
                "required": ["estado", "observacion"],
            }
        },
        responses=ProyectoDetalleSerializer,
    )
    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado_action(self, request, pk=None):
        proyecto = self.get_object()
        faltantes = [
            campo for campo in ("estado", "observacion") if not request.data.get(campo)
        ]
        if faltantes:
            raise ValidationError({campo: ["Este campo es obligatorio."] for campo in faltantes})

        cambiar_estado(proyecto, request.data["estado"], request.data["observacion"], request.user)
        proyecto.refresh_from_db()
        serializer = ProyectoDetalleSerializer(proyecto, context=self.get_serializer_context())
        return Response(serializer.data)

    @extend_schema(
        summary="KPIs del proyecto",
        description="Bloque `resumen_ejecucion` completo (docs/api-contrato.md §7).",
        responses={200: {"type": "object"}},
    )
    @action(detail=True, methods=["get"])
    def resumen(self, request, pk=None):
        proyecto = self.get_object()
        resumen = calcular_resumen_ejecucion(proyecto)
        resumen["fecha_corte"] = resumen["fecha_corte"].isoformat()
        return Response(resumen)

    @extend_schema(summary="Fases del proyecto", responses=FaseProyectoSerializer(many=True))
    @action(detail=True, methods=["get"])
    def fases(self, request, pk=None):
        proyecto = self.get_object()
        serializer = FaseProyectoSerializer(proyecto.fases.filter(activo=True), many=True)
        return Response(serializer.data)

    @extend_schema(summary="Hitos del proyecto", responses=HitoSerializer(many=True))
    @action(detail=True, methods=["get"])
    def hitos(self, request, pk=None):
        proyecto = self.get_object()
        serializer = HitoSerializer(proyecto.hitos.filter(activo=True), many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Rubros de presupuesto del proyecto",
        responses=RubroPresupuestoSerializer(many=True),
    )
    @action(detail=True, methods=["get"])
    def rubros(self, request, pk=None):
        proyecto = self.get_object()
        serializer = RubroPresupuestoSerializer(proyecto.rubros.filter(activo=True), many=True)
        return Response(serializer.data)


class FaseProyectoViewSet(ViewSetBase):
    queryset = FaseProyecto.objects.select_related("proyecto")
    serializer_lectura_class = FaseProyectoSerializer
    serializer_escritura_class = FaseProyectoSerializer
    permission_classes = [PermisoSubRecursoProyecto]
    filterset_fields = ["proyecto", "estado"]
    ordering_fields = ["orden", "fecha_inicio_plan"]


class HitoViewSet(ViewSetBase):
    queryset = Hito.objects.select_related("proyecto")
    serializer_lectura_class = HitoSerializer
    serializer_escritura_class = HitoSerializer
    permission_classes = [PermisoSubRecursoProyecto]
    filterset_fields = ["proyecto", "estado", "es_entregable"]
    ordering_fields = ["fecha_plan"]


class RubroPresupuestoViewSet(ViewSetBase):
    queryset = RubroPresupuesto.objects.select_related("proyecto")
    serializer_lectura_class = RubroPresupuestoSerializer
    serializer_escritura_class = RubroPresupuestoSerializer
    permission_classes = [PermisoSubRecursoProyecto]
    filterset_fields = ["proyecto", "categoria"]
    ordering_fields = ["categoria"]
