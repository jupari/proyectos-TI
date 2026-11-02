from rest_framework import serializers

from .models import Area, PerfilRecurso, Portafolio


class AreaSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Area
        fields = ["id", "codigo", "nombre", "responsable", "responsable_nombre", "activo"]

    def get_responsable_nombre(self, obj) -> str | None:
        return obj.responsable.nombre_completo if obj.responsable else None


class PortafolioSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Portafolio
        fields = [
            "id",
            "codigo",
            "nombre",
            "descripcion",
            "responsable",
            "responsable_nombre",
            "activo",
        ]

    def get_responsable_nombre(self, obj) -> str | None:
        return obj.responsable.nombre_completo if obj.responsable else None


class PerfilRecursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilRecurso
        fields = ["id", "codigo", "nombre", "tarifa_hora_referencia", "moneda", "activo"]
