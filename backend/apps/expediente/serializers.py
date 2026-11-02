from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.exceptions import ErrorArchivo
from apps.core.validators import validar_extension_archivo, validar_tamano_archivo

from .models import DocumentoExpediente, EntradaBitacora
from .services import guardar_documento


def _validar_tamano(archivo):
    """La extensión inválida queda en el `FileField` normal (→ 400 de
    DRF); el tamaño se valida aparte para poder responder 413
    (`ErrorArchivo`), que es lo que pide docs/plan/fase-09 §9.2.1 y no lo
    que haría DRF si copiara los dos validadores del modelo sin distinguir."""
    try:
        validar_tamano_archivo(archivo)
    except DjangoValidationError as exc:
        raise ErrorArchivo(exc.messages[0]) from exc
    return archivo


class DocumentoExpedienteSerializer(serializers.ModelSerializer):
    archivo = serializers.FileField(validators=[validar_extension_archivo])
    proyecto_codigo = serializers.CharField(source="proyecto.codigo", read_only=True)
    creado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = DocumentoExpediente
        fields = [
            "id",
            "proyecto",
            "proyecto_codigo",
            "seguimiento",
            "tarea",
            "categoria",
            "nombre",
            "archivo",
            "nombre_original",
            "mime",
            "tamano_bytes",
            "hash_sha256",
            "version",
            "documento_padre",
            "es_version_vigente",
            "descripcion",
            "creado_por",
            "creado_por_nombre",
            "creado_en",
            "activo",
        ]
        read_only_fields = [
            "id",
            "nombre_original",
            "mime",
            "tamano_bytes",
            "hash_sha256",
            "version",
            "documento_padre",
            "es_version_vigente",
            "creado_por",
            "creado_en",
            # "activo" también read-only: DRF trata un `BooleanField` ausente
            # de un `multipart/form-data` como `False`, no como "usa el
            # default del modelo" (a diferencia del JSON). Como este
            # endpoint es el único de toda la API que recibe multipart (por
            # el archivo), era el único expuesto a crear documentos
            # inactivos por accidente en cada alta.
            "activo",
        ]

    def get_creado_por_nombre(self, obj) -> str | None:
        return obj.creado_por.nombre_completo if obj.creado_por else None

    def validate_archivo(self, archivo):
        return _validar_tamano(archivo)

    def create(self, validated_data):
        request = self.context.get("request")
        usuario = getattr(request, "user", None) if request else None
        return guardar_documento(validated_data, usuario)


class NuevaVersionSerializer(serializers.Serializer):
    """Serializer sin modelo para `POST .../{id}/nueva-version/`: solo
    recibe el archivo, el resto de metadatos los hereda la versión anterior
    (`apps.expediente.services.nueva_version`)."""

    archivo = serializers.FileField(validators=[validar_extension_archivo])

    def validate_archivo(self, archivo):
        return _validar_tamano(archivo)


class EntradaBitacoraSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = EntradaBitacora
        fields = [
            "id",
            "proyecto",
            "tipo_evento",
            "entidad",
            "entidad_id",
            "descripcion",
            "datos_antes",
            "datos_despues",
            "usuario",
            "usuario_nombre",
            "ocurrido_en",
        ]

    def get_usuario_nombre(self, obj) -> str | None:
        return obj.usuario.nombre_completo if obj.usuario else None
