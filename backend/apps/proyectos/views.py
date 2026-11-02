from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.choices import EstadoAprobacion
from apps.core.exceptions import ErrorConflicto
from apps.core.mixins import MixinAlcancePorRol
from apps.core.permissions import EsLiderDelProyectoOLectura
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


class PermisoProyecto(EsLiderDelProyectoOLectura):
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

    @extend_schema(
        summary="Recursos planeados del proyecto",
        description="Asignaciones activas del proyecto: horas, costo, periodo y fase por "
        "recurso (docs/plan/fase-06-recursos-asignacion.md §6.2).",
        responses={200: {"type": "array", "items": {"type": "object"}}},
    )
    @action(detail=True, methods=["get"], url_path="recursos-planeados")
    def recursos_planeados(self, request, pk=None):
        from apps.recursos.serializers import AsignacionRecursoSerializer

        proyecto = self.get_object()
        serializer = AsignacionRecursoSerializer(
            proyecto.asignaciones.filter(activo=True).select_related("recurso", "fase"),
            many=True,
        )
        return Response(serializer.data)

    @extend_schema(
        summary="Cronograma del proyecto",
        description="Filas listas para el diagrama de Gantt de solo lectura del frontend: "
        "una por tarea, ordenadas por fase y fecha de inicio plan, con sus dependencias "
        "entrantes (docs/plan/fase-07-tareas-programacion.md §7.2.6). Dos consultas en total, "
        "sin N+1 por tarea.",
        responses={200: {"type": "array", "items": {"type": "object"}}},
    )
    @action(detail=True, methods=["get"])
    def cronograma(self, request, pk=None):
        from apps.tareas.models import DependenciaTarea, Tarea

        proyecto = self.get_object()
        tareas = list(
            Tarea.objects.filter(proyecto=proyecto, activo=True).select_related(
                "fase", "responsable"
            )
        )

        dependencias_por_tarea: dict = {}
        ids_tareas = [tarea.id for tarea in tareas]
        dependencias = DependenciaTarea.objects.filter(
            activo=True, tarea_destino_id__in=ids_tareas
        ).values("tarea_destino_id", "tarea_origen_id", "tipo", "dias_desfase")
        for dependencia in dependencias:
            dependencias_por_tarea.setdefault(dependencia["tarea_destino_id"], []).append(
                {
                    "tarea_id": str(dependencia["tarea_origen_id"]),
                    "tipo": dependencia["tipo"],
                    "dias_desfase": dependencia["dias_desfase"],
                }
            )

        mapa_tareas = {tarea.id: tarea for tarea in tareas}
        niveles: dict = {}

        def nivel_de(tarea):
            if tarea.id in niveles:
                return niveles[tarea.id]
            if tarea.tarea_padre_id is None or tarea.tarea_padre_id not in mapa_tareas:
                niveles[tarea.id] = 1
            else:
                niveles[tarea.id] = 1 + nivel_de(mapa_tareas[tarea.tarea_padre_id])
            return niveles[tarea.id]

        filas_ordenadas = sorted(
            tareas, key=lambda t: (t.fase.orden if t.fase_id else 10_000, t.fecha_inicio_plan)
        )

        return Response(
            [
                {
                    "tarea_id": str(tarea.id),
                    "codigo": tarea.codigo,
                    "nombre": tarea.nombre,
                    "nivel": nivel_de(tarea),
                    "fase": tarea.fase.nombre if tarea.fase_id else None,
                    "inicio_plan": tarea.fecha_inicio_plan.isoformat(),
                    "fin_plan": tarea.fecha_fin_plan.isoformat(),
                    "inicio_real": (
                        tarea.fecha_inicio_real.isoformat() if tarea.fecha_inicio_real else None
                    ),
                    "fin_real": tarea.fecha_fin_real.isoformat() if tarea.fecha_fin_real else None,
                    "avance": str(tarea.avance),
                    "estado": tarea.estado,
                    "responsable": tarea.responsable.nombre if tarea.responsable_id else None,
                    "dependencias": dependencias_por_tarea.get(tarea.id, []),
                }
                for tarea in filas_ordenadas
            ]
        )

    @extend_schema(
        summary="Plan vs. ejecutado por recurso y por mes",
        description="docs/plan/fase-08-ejecucion-ingesta.md §8.2.4.",
        responses={200: {"type": "object"}},
    )
    @action(detail=True, methods=["get"])
    def ejecucion(self, request, pk=None):
        from apps.ejecucion.services import comparativo_por_mes, comparativo_por_recurso

        proyecto = self.get_object()
        return Response(
            {
                "por_recurso": comparativo_por_recurso(proyecto),
                "por_mes": comparativo_por_mes(proyecto),
            }
        )


class FaseProyectoViewSet(ViewSetBase):
    queryset = FaseProyecto.objects.select_related("proyecto")
    serializer_lectura_class = FaseProyectoSerializer
    serializer_escritura_class = FaseProyectoSerializer
    permission_classes = [EsLiderDelProyectoOLectura]
    filterset_fields = ["proyecto", "estado"]
    ordering_fields = ["orden", "fecha_inicio_plan"]


class HitoViewSet(ViewSetBase):
    queryset = Hito.objects.select_related("proyecto")
    serializer_lectura_class = HitoSerializer
    serializer_escritura_class = HitoSerializer
    permission_classes = [EsLiderDelProyectoOLectura]
    filterset_fields = ["proyecto", "estado", "es_entregable"]
    ordering_fields = ["fecha_plan"]


class RubroPresupuestoViewSet(ViewSetBase):
    queryset = RubroPresupuesto.objects.select_related("proyecto")
    serializer_lectura_class = RubroPresupuestoSerializer
    serializer_escritura_class = RubroPresupuestoSerializer
    permission_classes = [EsLiderDelProyectoOLectura]
    filterset_fields = ["proyecto", "categoria"]
    ordering_fields = ["categoria"]
