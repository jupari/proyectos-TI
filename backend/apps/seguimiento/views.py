from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from apps.core.exceptions import ErrorConflicto
from apps.core.mixins import MixinAlcancePorRol
from apps.core.permissions import EsLiderDelProyectoOLectura
from apps.core.roles import codigos_roles_de, resolver_proyecto_de_instancia
from apps.core.views import ViewSetBase
from apps.proyectos.serializers import HitoSerializer
from apps.tareas.serializers import TareaListaSerializer

from .filters import FiltroCompromisoSeguimiento, FiltroSeguimiento
from .models import CompromisoSeguimiento, Seguimiento
from .serializers import CompromisoSeguimientoSerializer, SeguimientoSerializer
from .services import convertir_en_tarea
from .services import precargar as precargar_datos
from .services import publicar as publicar_seguimiento
from .services import reabrir as reabrir_seguimiento

ESTADOS_EDITABLES_SEGUIMIENTO = ("BORRADOR",)


class PermisoSeguimiento(EsLiderDelProyectoOLectura):
    """ADMIN: todo. PMO y `LIDER` del proyecto: crear, editar y publicar.
    `reabrir` es exclusivo de `ADMIN` (ni siquiera PMO, a diferencia del
    resto de ciclos de aprobación de fases anteriores — así lo pide
    docs/plan/fase-09-seguimiento-expediente.md §9.3.3). `precargar` no
    tiene objeto todavía, así que se resuelve como `create`: el proyecto
    sale del cuerpo de la petición."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        action_actual = getattr(view, "action", None)
        if "ADMIN" in codigos:
            return True
        if request.method == "DELETE" or action_actual == "reabrir":
            return False
        if action_actual in ("create", "precargar"):
            if "PMO" in codigos:
                return True
            if "LIDER" in codigos:
                proyecto_id = request.data.get("proyecto")
                if not proyecto_id:
                    return True
                from apps.proyectos.models import Proyecto

                usuario = request.user
                return Proyecto.objects.filter(
                    Q(pk=proyecto_id) & (Q(gerente=usuario) | Q(lider_tecnico=usuario))
                ).exists()
            return False
        return super().has_permission(request, view)


class PermisoCompromisoSeguimiento(BasePermission):
    """Mismo espíritu que `PermisoSeguimiento`: el objeto no tiene
    `proyecto` directo, se resuelve vía `seguimiento.proyecto`
    (`RUTA_A_PROYECTO["CompromisoSeguimiento"]`)."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        if codigos & {"ADMIN", "PMO"}:
            return True
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        if view.action != "create":
            return "LIDER" in codigos
        if "LIDER" not in codigos:
            return False

        seguimiento = (
            Seguimiento.objects.filter(pk=request.data.get("seguimiento"))
            .select_related("proyecto")
            .first()
        )
        if seguimiento is None:
            return True  # datos incompletos: el serializer lo rechaza

        usuario = request.user
        proyecto = seguimiento.proyecto
        return proyecto.gerente_id == usuario.id or proyecto.lider_tecnico_id == usuario.id

    def has_object_permission(self, request, view, obj):
        codigos = codigos_roles_de(request.user)
        if codigos & {"ADMIN", "PMO"}:
            return True
        if request.method in SAFE_METHODS:
            return True
        if "LIDER" not in codigos:
            return False
        proyecto = resolver_proyecto_de_instancia(obj)
        usuario = request.user
        return proyecto is not None and (
            proyecto.gerente_id == usuario.id or proyecto.lider_tecnico_id == usuario.id
        )


class SeguimientoViewSet(MixinAlcancePorRol, ViewSetBase):
    serializer_lectura_class = SeguimientoSerializer
    serializer_escritura_class = SeguimientoSerializer
    permission_classes = [PermisoSeguimiento]
    filterset_class = FiltroSeguimiento
    ordering_fields = ["fecha_corte", "periodo_inicio"]

    def get_queryset(self):
        queryset = Seguimiento.objects.select_related("proyecto", "publicado_por")
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        return self.filtrar_por_rol(queryset)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.estado not in ESTADOS_EDITABLES_SEGUIMIENTO:
            raise ErrorConflicto(
                "El seguimiento ya está publicado. Reabra el seguimiento para modificarlo."
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @extend_schema(
        summary="Precarga los datos reales de un periodo (no guarda nada)",
        description="docs/plan/fase-09-seguimiento-expediente.md §9.1.1.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "proyecto": {"type": "string"},
                    "periodicidad": {"type": "string"},
                    "periodo_inicio": {"type": "string", "format": "date"},
                },
                "required": ["proyecto", "periodicidad", "periodo_inicio"],
            }
        },
        responses={200: {"type": "object"}},
    )
    @action(detail=False, methods=["post"])
    def precargar(self, request):
        from apps.proyectos.models import Proyecto

        proyecto_id = request.data.get("proyecto")
        periodicidad = request.data.get("periodicidad")
        periodo_inicio_raw = request.data.get("periodo_inicio")
        faltantes = [
            campo
            for campo, valor in (
                ("proyecto", proyecto_id),
                ("periodicidad", periodicidad),
                ("periodo_inicio", periodo_inicio_raw),
            )
            if not valor
        ]
        if faltantes:
            raise ValidationError({campo: ["Este campo es obligatorio."] for campo in faltantes})

        periodo_inicio = parse_date(periodo_inicio_raw)
        if not periodo_inicio:
            raise ValidationError({"periodo_inicio": ["Formato de fecha inválido."]})

        try:
            proyecto = Proyecto.objects.get(pk=proyecto_id, activo=True)
        except Proyecto.DoesNotExist as exc:
            raise NotFound("El proyecto no existe.") from exc

        datos = precargar_datos(proyecto, periodicidad, periodo_inicio)
        return Response(
            {
                "proyecto": str(proyecto.id),
                "periodicidad": datos["periodicidad"],
                "periodo_inicio": datos["periodo_inicio"].isoformat(),
                "periodo_fin": datos["periodo_fin"].isoformat(),
                "fecha_corte": datos["fecha_corte"].isoformat(),
                "horas_periodo": str(datos["horas_periodo"]),
                "costo_periodo": str(datos["costo_periodo"]),
                "horas_acumuladas": str(datos["horas_acumuladas"]),
                "costo_acumulado": str(datos["costo_acumulado"]),
                "semaforo_calculado": datos["semaforo_calculado"],
                "avance_reportado": str(datos["avance_reportado"]),
                "tareas_completadas_en_periodo": TareaListaSerializer(
                    datos["tareas_completadas_en_periodo"], many=True
                ).data,
                "tareas_vencidas": TareaListaSerializer(datos["tareas_vencidas"], many=True).data,
                "hitos_del_periodo": HitoSerializer(datos["hitos_del_periodo"], many=True).data,
                "tareas_creadas_en_periodo": TareaListaSerializer(
                    datos["tareas_creadas_en_periodo"], many=True
                ).data,
            }
        )

    @extend_schema(summary="Publica el seguimiento (BORRADOR → PUBLICADO)")
    @action(detail=True, methods=["post"])
    def publicar(self, request, pk=None):
        seguimiento = self.get_object()
        publicar_seguimiento(seguimiento, request.user)
        seguimiento.refresh_from_db()
        return Response(self.get_serializer(seguimiento).data)

    @extend_schema(summary="Reabre el seguimiento para corrección (solo ADMIN)")
    @action(detail=True, methods=["post"])
    def reabrir(self, request, pk=None):
        seguimiento = self.get_object()
        reabrir_seguimiento(seguimiento, request.user)
        seguimiento.refresh_from_db()
        return Response(self.get_serializer(seguimiento).data)


class CompromisoSeguimientoViewSet(MixinAlcancePorRol, ViewSetBase):
    serializer_lectura_class = CompromisoSeguimientoSerializer
    serializer_escritura_class = CompromisoSeguimientoSerializer
    permission_classes = [PermisoCompromisoSeguimiento]
    filterset_class = FiltroCompromisoSeguimiento
    ordering_fields = ["fecha_compromiso"]

    def get_queryset(self):
        queryset = CompromisoSeguimiento.objects.select_related(
            "seguimiento", "responsable", "tarea"
        )
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        return self.filtrar_por_rol(queryset)

    @extend_schema(
        summary="Convierte el compromiso en una tarea medible, visible en el cronograma",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "horas_estimadas": {"type": "string"},
                    "fecha_inicio_plan": {"type": "string", "format": "date"},
                    "fecha_fin_plan": {"type": "string", "format": "date"},
                    "responsable": {"type": "string", "format": "uuid"},
                    "fase": {"type": "string", "format": "uuid"},
                },
                "required": ["horas_estimadas"],
            }
        },
        responses={200: CompromisoSeguimientoSerializer},
    )
    @action(detail=True, methods=["post"], url_path="convertir-tarea")
    def convertir_tarea(self, request, pk=None):
        compromiso = self.get_object()

        horas_estimadas_raw = request.data.get("horas_estimadas")
        if not horas_estimadas_raw:
            raise ValidationError({"horas_estimadas": ["Este campo es obligatorio."]})
        try:
            horas_estimadas = Decimal(str(horas_estimadas_raw))
        except InvalidOperation as exc:
            raise ValidationError({"horas_estimadas": ["Debe ser un número."]}) from exc

        responsable = None
        responsable_id = request.data.get("responsable")
        if responsable_id:
            from apps.recursos.models import Recurso

            try:
                responsable = Recurso.objects.get(pk=responsable_id)
            except Recurso.DoesNotExist as exc:
                raise NotFound("El recurso responsable no existe.") from exc

        fase = None
        fase_id = request.data.get("fase")
        if fase_id:
            from apps.proyectos.models import FaseProyecto

            try:
                fase = FaseProyecto.objects.get(pk=fase_id)
            except FaseProyecto.DoesNotExist as exc:
                raise NotFound("La fase no existe.") from exc

        fecha_inicio_raw = request.data.get("fecha_inicio_plan")
        fecha_fin_raw = request.data.get("fecha_fin_plan")

        convertir_en_tarea(
            compromiso,
            request.user,
            horas_estimadas=horas_estimadas,
            fecha_inicio_plan=parse_date(fecha_inicio_raw) if fecha_inicio_raw else None,
            fecha_fin_plan=parse_date(fecha_fin_raw) if fecha_fin_raw else None,
            responsable=responsable,
            fase=fase,
        )
        compromiso.refresh_from_db()
        return Response(self.get_serializer(compromiso).data)
