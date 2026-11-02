from django.db.models import Q
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from apps.core.mixins import MixinAlcancePorRol
from apps.core.roles import codigos_roles_de, resolver_proyecto_de_instancia
from apps.core.views import ViewSetBase, ViewSetSoloLectura

from .filters import FiltroBitacora, FiltroDocumentoExpediente
from .models import DocumentoExpediente, EntradaBitacora
from .serializers import (
    DocumentoExpedienteSerializer,
    EntradaBitacoraSerializer,
    NuevaVersionSerializer,
)
from .services import nueva_version as crear_nueva_version


class PermisoDocumentoExpediente(BasePermission):
    """ADMIN: L C E B. PMO: L C E (sin borrar: la matriz de
    docs/api-contrato.md §8 no le da "B"). LIDER: L C E *propios*. RECURSO:
    L C *propios*, y además puede borrar **solo lo que él mismo subió**
    (docs/plan/fase-09-seguimiento-expediente.md §9.3.5 lo pide explícito,
    aunque la matriz general no le da "B" a RECURSO; se documenta la
    discrepancia en la Evidencia de la fase)."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        action_actual = getattr(view, "action", None)
        usuario = request.user

        if "ADMIN" in codigos:
            return True
        if request.method == "DELETE":
            return bool(codigos & {"LIDER", "RECURSO"})
        if request.method in SAFE_METHODS:
            return bool(usuario and usuario.is_authenticated)

        if action_actual in ("create", "nueva_version"):
            if "PMO" in codigos:
                return True
            if "LIDER" in codigos:
                proyecto_id = request.data.get("proyecto")
                if not proyecto_id:
                    return True
                from apps.proyectos.models import Proyecto

                return Proyecto.objects.filter(
                    Q(pk=proyecto_id) & (Q(gerente=usuario) | Q(lider_tecnico=usuario))
                ).exists()
            if "RECURSO" in codigos:
                proyecto_id = request.data.get("proyecto")
                recurso = getattr(usuario, "recurso", None)
                if not proyecto_id or recurso is None:
                    return True
                from apps.recursos.models import AsignacionRecurso

                return AsignacionRecurso.objects.filter(
                    proyecto_id=proyecto_id, recurso=recurso, activo=True
                ).exists()
            return False

        # update / partial_update: solo PMO o LIDER (RECURSO no tiene "E")
        return bool(codigos & {"PMO", "LIDER"})

    def has_object_permission(self, request, view, obj):
        codigos = codigos_roles_de(request.user)
        usuario = request.user
        if "ADMIN" in codigos:
            return True

        if request.method == "DELETE":
            if "LIDER" in codigos:
                proyecto = resolver_proyecto_de_instancia(obj)
                return proyecto is not None and (
                    proyecto.gerente_id == usuario.id or proyecto.lider_tecnico_id == usuario.id
                )
            if "RECURSO" in codigos:
                return obj.creado_por_id == usuario.id
            return False

        if request.method in SAFE_METHODS:
            return True

        if "PMO" in codigos:
            return True
        if "LIDER" in codigos:
            proyecto = resolver_proyecto_de_instancia(obj)
            return proyecto is not None and (
                proyecto.gerente_id == usuario.id or proyecto.lider_tecnico_id == usuario.id
            )
        return False


class PermisoBitacora(BasePermission):
    """`docs/api-contrato.md` §8: `L` para ADMIN/PMO, `L *propios*` para
    LIDER, y **sin acceso** para RECURSO y CONSULTA (a diferencia del resto
    de recursos, aquí CONSULTA no entra en `ROLES_ALCANCE_TOTAL`)."""

    def has_permission(self, request, view):
        return bool(codigos_roles_de(request.user) & {"ADMIN", "PMO", "LIDER"})


class DocumentoExpedienteViewSet(MixinAlcancePorRol, ViewSetBase):
    serializer_lectura_class = DocumentoExpedienteSerializer
    serializer_escritura_class = DocumentoExpedienteSerializer
    permission_classes = [PermisoDocumentoExpediente]
    filterset_class = FiltroDocumentoExpediente
    ordering_fields = ["creado_en", "categoria"]

    def get_queryset(self):
        queryset = DocumentoExpediente.objects.select_related("proyecto", "creado_por")
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        return self.filtrar_por_rol(queryset)

    @extend_schema(
        summary="Sube una nueva versión del documento",
        request=NuevaVersionSerializer,
        responses=DocumentoExpedienteSerializer,
    )
    @action(detail=True, methods=["post"], url_path="nueva-version")
    def nueva_version(self, request, pk=None):
        documento = self.get_object()
        serializer = NuevaVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nueva = crear_nueva_version(documento, serializer.validated_data["archivo"], request.user)
        return Response(
            DocumentoExpedienteSerializer(nueva, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Descarga el archivo del documento")
    @action(detail=True, methods=["get"])
    def descargar(self, request, pk=None):
        documento = self.get_object()
        respuesta = FileResponse(
            documento.archivo.open("rb"),
            content_type=documento.mime or "application/octet-stream",
        )
        respuesta["Content-Disposition"] = f'attachment; filename="{documento.nombre_original}"'
        return respuesta


class BitacoraViewSet(MixinAlcancePorRol, ViewSetSoloLectura):
    serializer_lectura_class = EntradaBitacoraSerializer
    permission_classes = [PermisoBitacora]
    filterset_class = FiltroBitacora
    ordering_fields = ["ocurrido_en"]

    def get_queryset(self):
        queryset = EntradaBitacora.objects.select_related("proyecto", "usuario")
        if self.request.query_params.get("activo") != "false":
            queryset = queryset.filter(activo=True)
        return self.filtrar_por_rol(queryset)
