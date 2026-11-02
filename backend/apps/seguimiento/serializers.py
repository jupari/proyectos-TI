from django.utils import timezone
from rest_framework import serializers

from apps.core.periodos import normalizar_periodo

from .models import CompromisoSeguimiento, Seguimiento


class SeguimientoSerializer(serializers.ModelSerializer):
    """`periodo_fin` se recalcula siempre con `normalizar_periodo`, nunca se
    confía en lo que envía el cliente. `semaforo_calculado` y los cuatro
    campos `**C**` quedan en su valor por defecto (0) mientras el
    seguimiento está en `BORRADOR`: solo se congelan al publicar
    (`apps.seguimiento.services.publicar`), que es quien de verdad los
    calcula; antes de eso la UI muestra la vista previa de `precargar`, no
    estos campos."""

    proyecto_codigo = serializers.CharField(source="proyecto.codigo", read_only=True)
    publicado_por_nombre = serializers.SerializerMethodField()
    # Si no se envía, `create()` la calcula como min(periodo_fin, hoy).
    fecha_corte = serializers.DateField(required=False)

    class Meta:
        model = Seguimiento
        fields = [
            "id",
            "proyecto",
            "proyecto_codigo",
            "periodicidad",
            "periodo_inicio",
            "periodo_fin",
            "fecha_corte",
            "avance_reportado",
            "semaforo",
            "semaforo_calculado",
            "justificacion_semaforo",
            "logros",
            "dificultades",
            "riesgos",
            "acciones_siguientes",
            "horas_periodo",
            "costo_periodo",
            "horas_acumuladas",
            "costo_acumulado",
            "estado",
            "publicado_en",
            "publicado_por",
            "publicado_por_nombre",
            "activo",
        ]
        read_only_fields = [
            "id",
            "periodo_fin",
            "semaforo_calculado",
            "horas_periodo",
            "costo_periodo",
            "horas_acumuladas",
            "costo_acumulado",
            "estado",
            "publicado_en",
            "publicado_por",
        ]

    def get_publicado_por_nombre(self, obj) -> str | None:
        return obj.publicado_por.nombre_completo if obj.publicado_por else None

    def create(self, validated_data):
        validated_data["periodo_inicio"], validated_data["periodo_fin"] = normalizar_periodo(
            validated_data["periodicidad"], validated_data["periodo_inicio"]
        )
        if not validated_data.get("fecha_corte"):
            validated_data["fecha_corte"] = min(validated_data["periodo_fin"], timezone.localdate())
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "periodicidad" in validated_data or "periodo_inicio" in validated_data:
            periodicidad = validated_data.get("periodicidad", instance.periodicidad)
            periodo_inicio = validated_data.get("periodo_inicio", instance.periodo_inicio)
            validated_data["periodo_inicio"], validated_data["periodo_fin"] = normalizar_periodo(
                periodicidad, periodo_inicio
            )
        return super().update(instance, validated_data)


class CompromisoSeguimientoSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.CharField(source="responsable.nombre_completo", read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = CompromisoSeguimiento
        fields = [
            "id",
            "seguimiento",
            "descripcion",
            "responsable",
            "responsable_nombre",
            "fecha_compromiso",
            "estado",
            "fecha_cumplimiento",
            "esta_vencido",
            "activo",
        ]
