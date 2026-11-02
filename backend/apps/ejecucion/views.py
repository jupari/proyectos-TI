from django.db.models import Q, Sum
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from apps.core.choices import EstadoAprobacion
from apps.core.exceptions import ErrorConflicto
from apps.core.mixins import MixinAlcancePorRol
from apps.core.roles import codigos_roles_de, resolver_proyecto_de_instancia
from apps.core.views import ViewSetBase

from .filters import FiltroGastoEjecutado, FiltroRegistroEjecucion
from .models import GastoEjecutado, RegistroEjecucion
from .serializers import GastoEjecutadoSerializer, RegistroEjecucionSerializer
from .services import aprobar as aprobar_registro
from .services import aprobar_gasto, carga_lote, enviar_gasto, reabrir_gasto, rechazar_gasto
from .services import enviar as enviar_registro
from .services import reabrir as reabrir_registro
from .services import rechazar as rechazar_registro

ESTADOS_EDITABLES = (EstadoAprobacion.BORRADOR, EstadoAprobacion.RECHAZADO)


class PermisoRegistroEjecucion(BasePermission):
    """ADMIN: todo. PMO: todo salvo borrar. LIDER: todo en sus proyectos
    salvo borrar y reabrir. RECURSO: solo sobre sus propios registros, sin
    aprobar/rechazar/reabrir ni borrar. `aprobar`/`rechazar` exigen además
    PMO o LIDER **del proyecto**; `reabrir` exige PMO (ADMIN ya cubierto
    arriba). "Nadie aprueba su propio registro" se valida en
    `apps.ejecucion.services` porque depende de `registrado_por`, un dato
    del objeto, no solo del rol."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        if "ADMIN" in codigos:
            return True
        if request.method == "DELETE":
            return False

        action_actual = getattr(view, "action", None)
        if action_actual == "reabrir":
            return "PMO" in codigos
        if action_actual in ("aprobar", "rechazar"):
            return bool(codigos & {"PMO", "LIDER"})
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)

        if action_actual == "create":
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
                recurso_id = request.data.get("recurso")
                recurso_propio = getattr(request.user, "recurso", None)
                if not recurso_id or recurso_propio is None:
                    return True  # datos incompletos: el serializer lo rechaza
                return str(recurso_propio.id) == str(recurso_id)
            return False

        # update / partial_update / enviar / lote
        return bool(codigos & {"PMO", "LIDER", "RECURSO"})

    def has_object_permission(self, request, view, obj):
        codigos = codigos_roles_de(request.user)
        if "ADMIN" in codigos:
            return True
        if request.method == "DELETE":
            return False

        action_actual = getattr(view, "action", None)
        usuario = request.user

        if action_actual in ("aprobar", "rechazar"):
            if "PMO" in codigos:
                return True
            if "LIDER" in codigos:
                proyecto = resolver_proyecto_de_instancia(obj)
                return proyecto is not None and (
                    proyecto.gerente_id == usuario.id or proyecto.lider_tecnico_id == usuario.id
                )
            return False
        if action_actual == "reabrir":
            return "PMO" in codigos
        if request.method in SAFE_METHODS:
            return True

        if "PMO" in codigos:
            return True
        if "LIDER" in codigos:
            proyecto = resolver_proyecto_de_instancia(obj)
            return proyecto is not None and (
                proyecto.gerente_id == usuario.id or proyecto.lider_tecnico_id == usuario.id
            )
        if "RECURSO" in codigos:
            recurso = getattr(usuario, "recurso", None)
            return recurso is not None and obj.recurso_id == recurso.id
        return False


class PermisoGastoEjecutado(BasePermission):
    """ADMIN: todo. PMO: todo salvo borrar. LIDER: solo listar y crear en
    sus proyectos (docs/api-contrato.md §8: "L C *propios*", sin editar ni
    aprobar). RECURSO y CONSULTA-sin-autenticar: sin acceso; CONSULTA solo
    lectura."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        if "ADMIN" in codigos:
            return True
        if request.method == "DELETE":
            return False

        action_actual = getattr(view, "action", None)
        if action_actual in ("reabrir", "aprobar", "rechazar"):
            return "PMO" in codigos
        if request.method in SAFE_METHODS:
            return bool(codigos & {"PMO", "LIDER", "CONSULTA"})

        if action_actual == "create":
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

        # update / partial_update / enviar: solo PMO (y ADMIN, ya cubierto)
        return "PMO" in codigos

    def has_object_permission(self, request, view, obj):
        codigos = codigos_roles_de(request.user)
        if "ADMIN" in codigos:
            return True
        if request.method == "DELETE":
            return False
        if request.method in SAFE_METHODS:
            return bool(codigos & {"PMO", "LIDER", "CONSULTA"})
        return "PMO" in codigos


class RegistroEjecucionViewSet(MixinAlcancePorRol, ViewSetBase):
    serializer_lectura_class = RegistroEjecucionSerializer
    serializer_escritura_class = RegistroEjecucionSerializer
    permission_classes = [PermisoRegistroEjecucion]
    filterset_class = FiltroRegistroEjecucion
    ordering_fields = ["periodo_inicio", "horas", "estado_aprobacion"]

    def get_queryset(self):
        queryset = RegistroEjecucion.objects.select_related(
            "proyecto", "tarea", "recurso", "aprobado_por", "registrado_por"
        )
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        return self.filtrar_por_rol(queryset)

    def _responder_con_advertencias(self, serializer, status_code):
        datos = dict(serializer.data)
        datos["advertencias"] = getattr(serializer, "advertencias", [])
        return Response(datos, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        respuesta = self._responder_con_advertencias(serializer, status.HTTP_201_CREATED)
        respuesta["Location"] = headers.get("Location")
        return respuesta

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.estado_aprobacion not in ESTADOS_EDITABLES:
            raise ErrorConflicto(
                "El registro no está en borrador ni rechazado. Reabra el registro para "
                "modificarlo."
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self._responder_con_advertencias(serializer, status.HTTP_200_OK)

    @extend_schema(summary="Envía el registro a aprobación (BORRADOR/RECHAZADO → ENVIADO)")
    @action(detail=True, methods=["post"])
    def enviar(self, request, pk=None):
        registro = self.get_object()
        enviar_registro(registro, request.user)
        return Response(self.get_serializer(registro).data)

    @extend_schema(summary="Aprueba el registro (ENVIADO → APROBADO)")
    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        registro = self.get_object()
        aprobar_registro(registro, request.user)
        return Response(self.get_serializer(registro).data)

    @extend_schema(
        summary="Rechaza el registro (ENVIADO → RECHAZADO)",
        request={
            "application/json": {
                "type": "object",
                "properties": {"motivo_rechazo": {"type": "string"}},
                "required": ["motivo_rechazo"],
            }
        },
    )
    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        registro = self.get_object()
        rechazar_registro(registro, request.data.get("motivo_rechazo", ""), request.user)
        return Response(self.get_serializer(registro).data)

    @extend_schema(summary="Reabre el registro para corrección (APROBADO → ENVIADO)")
    @action(detail=True, methods=["post"])
    def reabrir(self, request, pk=None):
        registro = self.get_object()
        reabrir_registro(registro, request.user)
        return Response(self.get_serializer(registro).data)

    @extend_schema(
        summary="Carga varios registros de una vez",
        description="No es atómico por registro: los válidos se guardan aunque otros fallen "
        "(docs/api-contrato.md §6).",
        request={
            "application/json": {
                "type": "object",
                "properties": {"registros": {"type": "array", "items": {"type": "object"}}},
            }
        },
        responses={200: {"type": "object"}},
    )
    @action(detail=False, methods=["post"])
    def lote(self, request):
        lista_datos = request.data.get("registros")
        if not isinstance(lista_datos, list):
            raise ValidationError({"registros": ["Debe ser una lista de registros."]})
        creados, errores = carga_lote(lista_datos, self.get_serializer_context())
        return Response({"creados": len(creados), "errores": errores})

    @extend_schema(
        summary="Resumen agregado de registros aprobados",
        parameters=[
            OpenApiParameter("proyecto", str, required=True),
            OpenApiParameter(
                "agrupar_por", str, required=False, description="recurso | tarea | mes"
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "object"}}},
    )
    @action(detail=False, methods=["get"])
    def resumen(self, request):
        proyecto_id = request.query_params.get("proyecto")
        agrupar_por = request.query_params.get("agrupar_por", "recurso")
        if not proyecto_id:
            raise ValidationError({"proyecto": ["Debe indicar ?proyecto=."]})
        if agrupar_por not in ("recurso", "tarea", "mes"):
            raise ValidationError({"agrupar_por": ["Debe ser recurso, tarea o mes."]})

        base = self.filtrar_por_rol(
            RegistroEjecucion.objects.filter(
                activo=True, proyecto_id=proyecto_id, estado_aprobacion=EstadoAprobacion.APROBADO
            )
        )

        if agrupar_por == "recurso":
            filas = base.values("recurso", "recurso__nombre").annotate(
                horas=Sum("horas"), costo=Sum("costo")
            ).order_by("recurso__nombre")
            resultado = [
                {
                    "recurso": str(f["recurso"]),
                    "recurso_nombre": f["recurso__nombre"],
                    "horas": f["horas"],
                    "costo": f["costo"],
                }
                for f in filas
            ]
        elif agrupar_por == "tarea":
            filas = base.values("tarea", "tarea__codigo").annotate(
                horas=Sum("horas"), costo=Sum("costo")
            ).order_by("tarea__codigo")
            resultado = [
                {
                    "tarea": str(f["tarea"]) if f["tarea"] else None,
                    "tarea_codigo": f["tarea__codigo"],
                    "horas": f["horas"],
                    "costo": f["costo"],
                }
                for f in filas
            ]
        else:
            filas = (
                base.values("periodo_inicio__year", "periodo_inicio__month")
                .annotate(horas=Sum("horas"), costo=Sum("costo"))
                .order_by("periodo_inicio__year", "periodo_inicio__month")
            )
            resultado = [
                {
                    "anio": f["periodo_inicio__year"],
                    "mes": f["periodo_inicio__month"],
                    "horas": f["horas"],
                    "costo": f["costo"],
                }
                for f in filas
            ]
        return Response(resultado)


class GastoEjecutadoViewSet(MixinAlcancePorRol, ViewSetBase):
    serializer_lectura_class = GastoEjecutadoSerializer
    serializer_escritura_class = GastoEjecutadoSerializer
    permission_classes = [PermisoGastoEjecutado]
    filterset_class = FiltroGastoEjecutado
    ordering_fields = ["fecha", "monto"]

    def get_queryset(self):
        queryset = GastoEjecutado.objects.select_related("proyecto", "rubro", "aprobado_por")
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        return self.filtrar_por_rol(queryset)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.estado_aprobacion not in ESTADOS_EDITABLES:
            raise ErrorConflicto(
                "El gasto no está en borrador ni rechazado. Reabra el gasto para modificarlo."
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @extend_schema(summary="Envía el gasto a aprobación (BORRADOR/RECHAZADO → ENVIADO)")
    @action(detail=True, methods=["post"])
    def enviar(self, request, pk=None):
        gasto = self.get_object()
        enviar_gasto(gasto, request.user)
        return Response(self.get_serializer(gasto).data)

    @extend_schema(summary="Aprueba el gasto (ENVIADO → APROBADO)")
    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        gasto = self.get_object()
        aprobar_gasto(gasto, request.user)
        return Response(self.get_serializer(gasto).data)

    @extend_schema(
        summary="Rechaza el gasto (ENVIADO → RECHAZADO)",
        request={
            "application/json": {
                "type": "object",
                "properties": {"motivo_rechazo": {"type": "string"}},
                "required": ["motivo_rechazo"],
            }
        },
    )
    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        gasto = self.get_object()
        rechazar_gasto(gasto, request.data.get("motivo_rechazo", ""), request.user)
        return Response(self.get_serializer(gasto).data)

    @extend_schema(summary="Reabre el gasto para corrección (APROBADO → ENVIADO)")
    @action(detail=True, methods=["post"])
    def reabrir(self, request, pk=None):
        gasto = self.get_object()
        reabrir_gasto(gasto, request.user)
        return Response(self.get_serializer(gasto).data)
