from django.db.models import Q
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from apps.core.mixins import MixinAlcancePorRol
from apps.core.roles import codigos_roles_de, resolver_proyecto_de_instancia
from apps.core.views import ViewSetBase

from .filters import FiltroDependenciaTarea, FiltroTarea
from .models import DependenciaTarea, Tarea
from .serializers import (
    DependenciaTareaSerializer,
    TareaDetalleSerializer,
    TareaEscrituraSerializer,
    TareaListaSerializer,
)
from .services import cambiar_estado_tarea, fechas_sugeridas


class PermisoTarea(BasePermission):
    """ADMIN: todo. PMO: todo salvo borrar. LIDER: todo en sus proyectos
    (gerente/líder técnico) salvo borrar. RECURSO: solo sobre tareas donde
    es `responsable`; no puede borrar. La lectura (`list`/`retrieve`) no se
    restringe aquí a nivel de objeto porque el alcance ya lo acota
    `MixinAlcancePorRol`; "no reasignar el responsable a otro" se valida en
    `TareaEscrituraSerializer`, porque depende del cuerpo enviado, no solo
    del objeto."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        if "ADMIN" in codigos:
            return True
        if request.method == "DELETE":
            return False
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        if view.action != "create":
            return bool(codigos & {"PMO", "LIDER", "RECURSO"})

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
        if "RECURSO" in codigos:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        codigos = codigos_roles_de(request.user)
        if "ADMIN" in codigos:
            return True
        if request.method == "DELETE":
            return False
        if request.method in SAFE_METHODS:
            return True
        if "PMO" in codigos:
            return True
        if "LIDER" in codigos:
            proyecto = resolver_proyecto_de_instancia(obj)
            usuario = request.user
            return proyecto is not None and (
                proyecto.gerente_id == usuario.id or proyecto.lider_tecnico_id == usuario.id
            )
        if "RECURSO" in codigos:
            recurso = getattr(request.user, "recurso", None)
            return recurso is not None and obj.responsable_id == recurso.id
        return False


class PermisoDependenciaTarea(BasePermission):
    """Mismo espíritu que `PermisoTarea`, pero el objeto no tiene
    `proyecto`/`responsable` directos: se resuelven desde `tarea_origen`
    (su `RUTA_A_PROYECTO` es `tarea_origen.proyecto`)."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        if codigos & {"ADMIN", "PMO"}:
            return True
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        if view.action != "create":
            return bool(codigos & {"LIDER", "RECURSO"})

        origen = Tarea.objects.filter(pk=request.data.get("tarea_origen")).select_related(
            "proyecto"
        ).first()
        if origen is None:
            return True  # datos incompletos: el serializer los rechaza

        if "LIDER" in codigos:
            usuario = request.user
            return (
                origen.proyecto.gerente_id == usuario.id
                or origen.proyecto.lider_tecnico_id == usuario.id
            )
        if "RECURSO" in codigos:
            recurso = getattr(request.user, "recurso", None)
            return recurso is not None and origen.responsable_id == recurso.id
        return False

    def has_object_permission(self, request, view, obj):
        codigos = codigos_roles_de(request.user)
        if codigos & {"ADMIN", "PMO"}:
            return True
        if request.method in SAFE_METHODS:
            return True
        if "LIDER" in codigos:
            proyecto = obj.tarea_origen.proyecto
            usuario = request.user
            return proyecto.gerente_id == usuario.id or proyecto.lider_tecnico_id == usuario.id
        if "RECURSO" in codigos:
            recurso = getattr(request.user, "recurso", None)
            return recurso is not None and (
                obj.tarea_origen.responsable_id == recurso.id
                or obj.tarea_destino.responsable_id == recurso.id
            )
        return False


class TareaViewSet(MixinAlcancePorRol, ViewSetBase):
    serializer_lectura_class = TareaListaSerializer
    serializer_escritura_class = TareaEscrituraSerializer
    permission_classes = [PermisoTarea]
    filterset_class = FiltroTarea
    search_fields = ["codigo", "nombre"]
    ordering_fields = ["orden", "fecha_inicio_plan", "fecha_fin_plan", "prioridad", "codigo"]

    def get_queryset(self):
        queryset = Tarea.objects.select_related("proyecto", "fase", "responsable", "tarea_padre")
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                "subtareas__responsable",
                "dependencias_entrantes__tarea_origen",
                "dependencias_salientes__tarea_destino",
            )
        return self.filtrar_por_rol(queryset)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TareaDetalleSerializer
        return super().get_serializer_class()

    @extend_schema(
        summary="Cambia el estado de la tarea",
        description="Aplica las precondiciones por estado de "
        "docs/plan/fase-07-tareas-programacion.md §7.1 y registra el cambio en la bitácora.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "estado": {"type": "string"},
                    "fecha_inicio_real": {"type": "string", "format": "date"},
                    "fecha_fin_real": {"type": "string", "format": "date"},
                    "nota": {"type": "string"},
                },
                "required": ["estado"],
            }
        },
        responses=TareaDetalleSerializer,
    )
    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado_action(self, request, pk=None):
        tarea = self.get_object()
        estado_nuevo = request.data.get("estado")
        if not estado_nuevo:
            raise ValidationError({"estado": ["Este campo es obligatorio."]})

        cambiar_estado_tarea(
            tarea,
            estado_nuevo,
            request.user,
            fecha_inicio_real=parse_date(request.data.get("fecha_inicio_real") or ""),
            fecha_fin_real=parse_date(request.data.get("fecha_fin_real") or ""),
            nota=request.data.get("nota"),
        )
        tarea.refresh_from_db()
        serializer = TareaDetalleSerializer(tarea, context=self.get_serializer_context())
        return Response(serializer.data)

    @extend_schema(
        summary="Árbol de tareas de un proyecto",
        description="Jerarquía completa anidada en una sola consulta (docs/api-contrato.md §5).",
        parameters=[OpenApiParameter("proyecto", str, required=True)],
        responses={200: {"type": "array", "items": {"type": "object"}}},
    )
    @action(detail=False, methods=["get"])
    def arbol(self, request):
        proyecto_id = request.query_params.get("proyecto")
        if not proyecto_id:
            raise ValidationError({"proyecto": ["Debe indicar ?proyecto=."]})

        tareas = list(
            self.filtrar_por_rol(Tarea.objects.filter(activo=True, proyecto_id=proyecto_id))
            .select_related("responsable")
            .order_by("orden", "codigo")
        )
        por_padre: dict = {}
        for tarea in tareas:
            por_padre.setdefault(tarea.tarea_padre_id, []).append(tarea)

        def construir(tarea):
            return {
                "id": str(tarea.id),
                "codigo": tarea.codigo,
                "nombre": tarea.nombre,
                "tipo": tarea.tipo,
                "estado": tarea.estado,
                "prioridad": tarea.prioridad,
                "responsable": str(tarea.responsable_id) if tarea.responsable_id else None,
                "responsable_nombre": tarea.responsable.nombre if tarea.responsable_id else None,
                "fecha_inicio_plan": tarea.fecha_inicio_plan.isoformat(),
                "fecha_fin_plan": tarea.fecha_fin_plan.isoformat(),
                "horas_estimadas": str(tarea.horas_estimadas),
                "horas_ejecutadas": str(tarea.horas_ejecutadas),
                "avance": str(tarea.avance),
                "orden": tarea.orden,
                "subtareas": [construir(hija) for hija in por_padre.get(tarea.id, [])],
            }

        return Response([construir(raiz) for raiz in por_padre.get(None, [])])

    @extend_schema(
        summary="Fechas sugeridas según dependencias FI",
        description="Sugerencia, no se impone (docs/plan/fase-07-tareas-programacion.md §7.1).",
        responses={200: {"type": "object"}},
    )
    @action(detail=True, methods=["get"], url_path="fechas-sugeridas")
    def fechas_sugeridas_action(self, request, pk=None):
        tarea = self.get_object()
        resultado = fechas_sugeridas(tarea)
        return Response(
            {
                "fecha_inicio_sugerida": (
                    resultado["fecha_inicio_sugerida"].isoformat()
                    if resultado["fecha_inicio_sugerida"]
                    else None
                ),
                "fecha_fin_sugerida": (
                    resultado["fecha_fin_sugerida"].isoformat()
                    if resultado["fecha_fin_sugerida"]
                    else None
                ),
            }
        )


class DependenciaTareaViewSet(MixinAlcancePorRol, ViewSetBase):
    serializer_lectura_class = DependenciaTareaSerializer
    serializer_escritura_class = DependenciaTareaSerializer
    permission_classes = [PermisoDependenciaTarea]
    filterset_class = FiltroDependenciaTarea
    ordering_fields = ["tarea_origen", "tarea_destino"]

    def get_queryset(self):
        queryset = DependenciaTarea.objects.select_related(
            "tarea_origen__proyecto", "tarea_destino__proyecto"
        )
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        return self.filtrar_por_rol(queryset)
