import datetime

from rest_framework import serializers

from apps.core.choices import TipoEvento
from apps.core.exceptions import ErrorReglaNegocio
from apps.core.services import registrar_evento

from .models import AsignacionRecurso, Recurso, TarifaRecurso
from .services import validar_asignacion, validar_vigencias, valor_hora_vigente


class RecursoSerializer(serializers.ModelSerializer):
    perfil_nombre = serializers.SerializerMethodField()
    tarifa_vigente = serializers.SerializerMethodField()
    proyectos_activos = serializers.SerializerMethodField()

    class Meta:
        model = Recurso
        fields = [
            "id",
            "tipo",
            "nombre",
            "usuario",
            "perfil",
            "perfil_nombre",
            "email",
            "capacidad_horas_mes",
            "fecha_ingreso",
            "fecha_retiro",
            "tarifa_vigente",
            "proyectos_activos",
            "activo",
        ]

    def get_perfil_nombre(self, obj) -> str | None:
        return obj.perfil.nombre if obj.perfil else None

    def get_tarifa_vigente(self, obj) -> str | None:
        try:
            return str(valor_hora_vigente(obj, datetime.date.today()))
        except ErrorReglaNegocio:
            return None

    def get_proyectos_activos(self, obj) -> int:
        return (
            obj.asignaciones.filter(activo=True, proyecto__activo=True)
            .values("proyecto")
            .distinct()
            .count()
        )


class TarifaRecursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarifaRecurso
        fields = [
            "id",
            "recurso",
            "valor_hora",
            "moneda",
            "vigente_desde",
            "vigente_hasta",
            "activo",
        ]

    def create(self, validated_data):
        tarifa = TarifaRecurso(**validated_data)
        self.avisos = validar_vigencias(tarifa.recurso, tarifa)
        tarifa.save()
        return tarifa

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        self.avisos = validar_vigencias(instance.recurso, instance)
        instance.save()
        return instance


class AsignacionRecursoSerializer(serializers.ModelSerializer):
    valor_hora_plan = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)

    class Meta:
        model = AsignacionRecurso
        fields = [
            "id",
            "proyecto",
            "recurso",
            "fase",
            "rol_en_proyecto",
            "fecha_desde",
            "fecha_hasta",
            "porcentaje_dedicacion",
            "horas_planeadas",
            "valor_hora_plan",
            "costo_planeado",
            "activo",
        ]
        read_only_fields = ["costo_planeado"]

    def validate(self, attrs):
        fecha_desde = attrs.get("fecha_desde", getattr(self.instance, "fecha_desde", None))
        fecha_hasta = attrs.get("fecha_hasta", getattr(self.instance, "fecha_hasta", None))
        if fecha_desde and fecha_hasta and fecha_hasta < fecha_desde:
            raise serializers.ValidationError(
                {"fecha_hasta": ["Debe ser igual o posterior a la fecha desde."]}
            )
        return attrs

    def create(self, validated_data):
        tarifa_manual = "valor_hora_plan" in validated_data
        if not tarifa_manual:
            validated_data["valor_hora_plan"] = valor_hora_vigente(
                validated_data["recurso"], validated_data["fecha_desde"]
            )

        instancia = AsignacionRecurso(**validated_data)
        self.advertencias = validar_asignacion(instancia)
        instancia.save()

        if tarifa_manual:
            usuario = self.context["request"].user if "request" in self.context else None
            registrar_evento(
                tipo_evento=TipoEvento.ASIGNACION,
                entidad="AsignacionRecurso",
                entidad_id=instancia.id,
                descripcion=(
                    f"Asignación de {instancia.recurso.nombre} a {instancia.proyecto.codigo} "
                    f"con tarifa manual de {instancia.valor_hora_plan}."
                ),
                proyecto=instancia.proyecto,
                usuario=usuario,
            )
        return instancia

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        self.advertencias = validar_asignacion(instance)
        instance.save()
        return instance
