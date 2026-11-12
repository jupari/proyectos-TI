from django.db import transaction
from rest_framework import serializers

from apps.tablero.services import resumen_ejecucion as calcular_resumen_ejecucion

from .models import FaseProyecto, Hito, Proyecto, RubroPresupuesto
from .services import generar_codigo_proyecto, validar_pesos_fases, validar_presupuesto


def _validar_fin_despues_de_inicio(attrs, instance, campo_inicio, campo_fin):
    inicio = attrs.get(campo_inicio, getattr(instance, campo_inicio, None))
    fin = attrs.get(campo_fin, getattr(instance, campo_fin, None))
    if inicio and fin and fin < inicio:
        raise serializers.ValidationError(
            {campo_fin: ["Debe ser igual o posterior a la fecha de inicio."]}
        )


class FaseProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaseProyecto
        fields = [
            "id",
            "proyecto",
            "nombre",
            "orden",
            "peso",
            "fecha_inicio_plan",
            "fecha_fin_plan",
            "fecha_inicio_real",
            "fecha_fin_real",
            "estado",
            "activo",
        ]

    def validate(self, attrs):
        _validar_fin_despues_de_inicio(
            attrs, self.instance, "fecha_inicio_plan", "fecha_fin_plan"
        )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        instancia = super().create(validated_data)
        validar_pesos_fases(instancia.proyecto)
        return instancia

    @transaction.atomic
    def update(self, instance, validated_data):
        instancia = super().update(instance, validated_data)
        validar_pesos_fases(instancia.proyecto)
        return instancia


class HitoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hito
        fields = [
            "id",
            "proyecto",
            "nombre",
            "descripcion",
            "fecha_plan",
            "fecha_real",
            "estado",
            "criterio_cumplimiento",
            "es_entregable",
            "activo",
        ]


class RubroPresupuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RubroPresupuesto
        fields = [
            "id",
            "proyecto",
            "categoria",
            "descripcion",
            "monto_planeado",
            "monto_ejecutado",
            "activo",
        ]
        read_only_fields = ["monto_ejecutado"]


class ProyectoListaSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source="area_solicitante.nombre", read_only=True)
    portafolio_nombre = serializers.SerializerMethodField()
    gerente_nombre = serializers.CharField(source="gerente.nombre_completo", read_only=True)
    resumen_ejecucion = serializers.SerializerMethodField()

    class Meta:
        model = Proyecto
        fields = [
            "id",
            "codigo",
            "nombre",
            "area_solicitante",
            "area_nombre",
            "portafolio",
            "portafolio_nombre",
            "gerente",
            "gerente_nombre",
            "lider_tecnico",
            "estado",
            "prioridad",
            "fecha_inicio_plan",
            "fecha_fin_plan",
            "fecha_inicio_real",
            "fecha_fin_real",
            "avance_reportado",
            "semaforo",
            "resumen_ejecucion",
            "activo",
        ]

    def get_portafolio_nombre(self, obj) -> str | None:
        return obj.portafolio.nombre if obj.portafolio else None

    def get_resumen_ejecucion(self, obj) -> dict:
        resumen = calcular_resumen_ejecucion(obj)
        return {
            "pct_horas": resumen["pct_horas"],
            "pct_dinero": resumen["pct_dinero"],
            "avance": resumen["avance"],
        }


class ProyectoDetalleSerializer(ProyectoListaSerializer):
    fases = FaseProyectoSerializer(many=True, read_only=True)
    hitos = HitoSerializer(many=True, read_only=True)
    rubros = RubroPresupuestoSerializer(many=True, read_only=True)

    class Meta(ProyectoListaSerializer.Meta):
        fields = [
            *ProyectoListaSerializer.Meta.fields,
            "descripcion",
            "objetivo",
            "moneda",
            "presupuesto_horas",
            "presupuesto_dinero",
            "observaciones",
            "clave_jira",
            "fases",
            "hitos",
            "rubros",
        ]

    def get_resumen_ejecucion(self, obj) -> dict:
        resumen = calcular_resumen_ejecucion(obj)
        resumen["fecha_corte"] = resumen["fecha_corte"].isoformat()
        return resumen


class ProyectoEscrituraSerializer(serializers.ModelSerializer):
    """Ignora `codigo` (lo genera el servidor) y no acepta `estado` (solo se
    cambia con `POST /proyectos/{id}/cambiar-estado/`)."""

    class Meta:
        model = Proyecto
        fields = [
            "id",
            "codigo",
            "nombre",
            "descripcion",
            "objetivo",
            "portafolio",
            "area_solicitante",
            "gerente",
            "lider_tecnico",
            "prioridad",
            "fecha_inicio_plan",
            "fecha_fin_plan",
            "fecha_inicio_real",
            "fecha_fin_real",
            "moneda",
            "presupuesto_horas",
            "presupuesto_dinero",
            "avance_reportado",
            "observaciones",
            "clave_jira",
        ]
        read_only_fields = ["id", "codigo"]

    def validate(self, attrs):
        _validar_fin_despues_de_inicio(
            attrs, self.instance, "fecha_inicio_plan", "fecha_fin_plan"
        )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data["codigo"] = generar_codigo_proyecto()
        instancia = super().create(validated_data)
        validar_presupuesto(instancia)
        return instancia

    @transaction.atomic
    def update(self, instance, validated_data):
        instancia = super().update(instance, validated_data)
        validar_presupuesto(instancia)
        return instancia
