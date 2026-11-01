from rest_framework import serializers


class RespuestaSaludSerializer(serializers.Serializer):
    estado = serializers.CharField()
    version = serializers.CharField()
    base_datos = serializers.CharField()
    hora = serializers.DateTimeField()


class SerializerAuditoria(serializers.Serializer):
    """Mixin que expone el nombre de quien creó/actualizó el registro."""

    creado_por_nombre = serializers.SerializerMethodField()
    actualizado_por_nombre = serializers.SerializerMethodField()

    def get_creado_por_nombre(self, obj):
        return obj.creado_por.nombre_completo if obj.creado_por_id else None

    def get_actualizado_por_nombre(self, obj):
        return obj.actualizado_por.nombre_completo if obj.actualizado_por_id else None


class SerializerBase(SerializerAuditoria, serializers.ModelSerializer):
    """ModelSerializer base de todas las apps de negocio.

    `creado_en`/`actualizado_en` y los campos de auditoría son siempre de solo
    lectura. Cada serializer concreto además marca sus propios campos
    calculados (los `C` de docs/modelo-datos.md) como read_only en su Meta.
    """

    def get_fields(self):
        campos = super().get_fields()
        for nombre in ("creado_en", "actualizado_en"):
            if nombre in campos:
                campos[nombre].read_only = True
        return campos
