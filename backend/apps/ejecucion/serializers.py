from rest_framework import serializers

from .models import GastoEjecutado, RegistroEjecucion
from .services import (
    preparar_registro,
    validar_rango_proyecto,
    validar_rubro,
    validar_solapamiento,
    validar_tarea,
    validar_topes,
)


class RegistroEjecucionSerializer(serializers.ModelSerializer):
    """`registrado_por` siempre lo fija `create()` con el usuario de la
    petición (nunca el cliente); `periodo_fin`, `valor_hora_aplicado` y
    `costo` los resuelve `preparar_registro` (servicio), no el cliente."""

    proyecto_codigo = serializers.CharField(source="proyecto.codigo", read_only=True)
    proyecto_nombre = serializers.CharField(source="proyecto.nombre", read_only=True)
    tarea_codigo = serializers.CharField(source="tarea.codigo", read_only=True, default=None)
    recurso_nombre = serializers.CharField(source="recurso.nombre", read_only=True)
    registrado_por_nombre = serializers.SerializerMethodField()
    aprobado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = RegistroEjecucion
        fields = [
            "id",
            "proyecto",
            "proyecto_codigo",
            "proyecto_nombre",
            "tarea",
            "tarea_codigo",
            "recurso",
            "recurso_nombre",
            "periodicidad",
            "periodo_inicio",
            "periodo_fin",
            "horas",
            "valor_hora_aplicado",
            "costo",
            "descripcion",
            "estado_aprobacion",
            "motivo_rechazo",
            "aprobado_por",
            "aprobado_por_nombre",
            "aprobado_en",
            "registrado_por",
            "registrado_por_nombre",
            "origen",
            "activo",
        ]
        read_only_fields = [
            "id",
            "periodo_fin",
            "valor_hora_aplicado",
            "costo",
            "estado_aprobacion",
            "motivo_rechazo",
            "aprobado_por",
            "aprobado_en",
            "registrado_por",
            "origen",
        ]

    def get_registrado_por_nombre(self, obj) -> str | None:
        return obj.registrado_por.nombre_completo if obj.registrado_por else None

    def get_aprobado_por_nombre(self, obj) -> str | None:
        return obj.aprobado_por.nombre_completo if obj.aprobado_por else None

    def create(self, validated_data):
        request = self.context.get("request")
        usuario = getattr(request, "user", None) if request else None

        instancia = RegistroEjecucion(**validated_data, registrado_por=usuario)
        preparar_registro(instancia)
        validar_rango_proyecto(instancia)
        validar_tarea(instancia)
        validar_solapamiento(instancia)
        self.advertencias = validar_topes(instancia)
        instancia.save()
        return instancia

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        preparar_registro(instance)
        validar_rango_proyecto(instance)
        validar_tarea(instance)
        validar_solapamiento(instance)
        self.advertencias = validar_topes(instance)
        instance.save()
        return instance


class GastoEjecutadoSerializer(serializers.ModelSerializer):
    proyecto_codigo = serializers.CharField(source="proyecto.codigo", read_only=True)
    rubro_descripcion = serializers.CharField(source="rubro.descripcion", read_only=True)
    aprobado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = GastoEjecutado
        fields = [
            "id",
            "proyecto",
            "proyecto_codigo",
            "rubro",
            "rubro_descripcion",
            "fecha",
            "monto",
            "proveedor",
            "numero_documento",
            "descripcion",
            "estado_aprobacion",
            "aprobado_por",
            "aprobado_por_nombre",
            "aprobado_en",
            "activo",
        ]
        read_only_fields = ["id", "estado_aprobacion", "aprobado_por", "aprobado_en"]

    def get_aprobado_por_nombre(self, obj) -> str | None:
        return obj.aprobado_por.nombre_completo if obj.aprobado_por else None

    def create(self, validated_data):
        instancia = GastoEjecutado(**validated_data)
        validar_rubro(instancia)
        instancia.save()
        return instancia

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        validar_rubro(instance)
        instance.save()
        return instance
