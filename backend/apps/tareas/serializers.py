import datetime

from django.db import transaction
from rest_framework import serializers

from apps.core.roles import codigos_roles_de

from .models import DependenciaTarea, Tarea
from .services import (
    ESTADOS_TERMINALES_TAREA,
    detectar_ciclo,
    generar_codigo_tarea,
    marcar_creacion_durante_ejecucion,
    recalcular_avance,
    validar_jerarquia,
)


def _validar_fin_despues_de_inicio(attrs, instance, campo_inicio, campo_fin):
    inicio = attrs.get(campo_inicio, getattr(instance, campo_inicio, None))
    fin = attrs.get(campo_fin, getattr(instance, campo_fin, None))
    if inicio and fin and fin < inicio:
        raise serializers.ValidationError(
            {campo_fin: ["Debe ser igual o posterior a la fecha de inicio."]}
        )


class TareaSubtareaSerializer(serializers.ModelSerializer):
    """Un nivel de subtareas, para anidar en `TareaDetalleSerializer` sin
    recursión (docs/plan/fase-07-tareas-programacion.md §7.2.3)."""

    responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Tarea
        fields = [
            "id",
            "codigo",
            "nombre",
            "estado",
            "prioridad",
            "responsable",
            "responsable_nombre",
            "horas_estimadas",
            "horas_ejecutadas",
            "avance",
            "fecha_inicio_plan",
            "fecha_fin_plan",
        ]

    def get_responsable_nombre(self, obj) -> str | None:
        return obj.responsable.nombre if obj.responsable else None


class DependenciaTareaSerializer(serializers.ModelSerializer):
    tarea_origen_codigo = serializers.CharField(source="tarea_origen.codigo", read_only=True)
    tarea_destino_codigo = serializers.CharField(source="tarea_destino.codigo", read_only=True)

    class Meta:
        model = DependenciaTarea
        fields = [
            "id",
            "tarea_origen",
            "tarea_origen_codigo",
            "tarea_destino",
            "tarea_destino_codigo",
            "tipo",
            "dias_desfase",
            "activo",
        ]

    def validate(self, attrs):
        origen = attrs.get("tarea_origen", getattr(self.instance, "tarea_origen", None))
        destino = attrs.get("tarea_destino", getattr(self.instance, "tarea_destino", None))
        if origen and destino and origen.proyecto_id != destino.proyecto_id:
            raise serializers.ValidationError(
                {"tarea_destino": ["Las dos tareas deben ser del mismo proyecto."]}
            )
        return attrs

    def create(self, validated_data):
        detectar_ciclo(validated_data["tarea_origen"], validated_data["tarea_destino"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        origen = validated_data.get("tarea_origen", instance.tarea_origen)
        destino = validated_data.get("tarea_destino", instance.tarea_destino)
        if origen.pk != instance.tarea_origen_id or destino.pk != instance.tarea_destino_id:
            detectar_ciclo(origen, destino)
        return super().update(instance, validated_data)


class TareaListaSerializer(serializers.ModelSerializer):
    proyecto_codigo = serializers.CharField(source="proyecto.codigo", read_only=True)
    fase_nombre = serializers.SerializerMethodField()
    sprint_nombre = serializers.SerializerMethodField()
    responsable_nombre = serializers.SerializerMethodField()
    dias_atraso = serializers.SerializerMethodField()
    tiene_subtareas = serializers.SerializerMethodField()
    numero_dependencias = serializers.SerializerMethodField()

    class Meta:
        model = Tarea
        fields = [
            "id",
            "proyecto",
            "proyecto_codigo",
            "fase",
            "fase_nombre",
            "tarea_padre",
            "codigo",
            "nombre",
            "tipo",
            "estado",
            "prioridad",
            "responsable",
            "responsable_nombre",
            "fecha_inicio_plan",
            "fecha_fin_plan",
            "fecha_inicio_real",
            "fecha_fin_real",
            "horas_estimadas",
            "horas_ejecutadas",
            "avance",
            "orden",
            "creada_durante_ejecucion",
            "motivo_creacion",
            "clave_jira",
            "sprint",
            "sprint_nombre",
            "epica_clave",
            "epica_nombre",
            "dias_atraso",
            "tiene_subtareas",
            "numero_dependencias",
            "activo",
        ]

    def get_fase_nombre(self, obj) -> str | None:
        return obj.fase.nombre if obj.fase else None

    def get_sprint_nombre(self, obj) -> str | None:
        return obj.sprint.nombre if obj.sprint else None

    def get_responsable_nombre(self, obj) -> str | None:
        return obj.responsable.nombre if obj.responsable else None

    def get_dias_atraso(self, obj) -> int | None:
        if obj.estado in ESTADOS_TERMINALES_TAREA:
            return None
        hoy = datetime.date.today()
        if obj.fecha_fin_plan >= hoy:
            return None
        return (hoy - obj.fecha_fin_plan).days

    def get_tiene_subtareas(self, obj) -> bool:
        return obj.subtareas.filter(activo=True).exists()

    def get_numero_dependencias(self, obj) -> int:
        return (
            obj.dependencias_salientes.filter(activo=True).count()
            + obj.dependencias_entrantes.filter(activo=True).count()
        )


class TareaDetalleSerializer(TareaListaSerializer):
    subtareas = serializers.SerializerMethodField()
    dependencias_entrantes = DependenciaTareaSerializer(many=True, read_only=True)
    dependencias_salientes = DependenciaTareaSerializer(many=True, read_only=True)

    class Meta(TareaListaSerializer.Meta):
        fields = [
            *TareaListaSerializer.Meta.fields,
            "descripcion",
            "subtareas",
            "dependencias_entrantes",
            "dependencias_salientes",
        ]

    def get_subtareas(self, obj) -> list:
        return TareaSubtareaSerializer(obj.subtareas.filter(activo=True), many=True).data


class TareaEscrituraSerializer(serializers.ModelSerializer):
    """`codigo` lo genera el servidor (como en `ProyectoEscrituraSerializer`):
    se incluye de solo lectura para que aparezca en la respuesta, y además se
    rechaza explícitamente si alguien intenta enviarlo, igual que
    `horas_ejecutadas` (siempre calculada) y `avance` cuando la tarea tiene
    subtareas (ahí también es calculado, por `recalcular_avance`)."""

    class Meta:
        model = Tarea
        fields = [
            "id",
            "proyecto",
            "fase",
            "tarea_padre",
            "codigo",
            "nombre",
            "descripcion",
            "tipo",
            "prioridad",
            "responsable",
            "fecha_inicio_plan",
            "fecha_fin_plan",
            "fecha_inicio_real",
            "fecha_fin_real",
            "horas_estimadas",
            "horas_ejecutadas",
            "avance",
            "orden",
            "creada_durante_ejecucion",
            "motivo_creacion",
            "clave_jira",
        ]
        read_only_fields = ["id", "codigo", "horas_ejecutadas", "creada_durante_ejecucion"]

    def validate(self, attrs):
        datos_enviados = self.initial_data if hasattr(self, "initial_data") else {}
        if "codigo" in datos_enviados:
            raise serializers.ValidationError(
                {"codigo": ["No se puede escribir directamente; lo genera el servidor."]}
            )
        if "horas_ejecutadas" in datos_enviados:
            raise serializers.ValidationError(
                {"horas_ejecutadas": ["Es un valor calculado; no se puede escribir."]}
            )

        instance = self.instance
        tiene_subtareas = instance.subtareas.filter(activo=True).exists() if instance else False
        if tiene_subtareas and "avance" in datos_enviados:
            raise serializers.ValidationError(
                {"avance": ["Esta tarea tiene subtareas; su avance se calcula, no se escribe."]}
            )

        _validar_fin_despues_de_inicio(attrs, instance, "fecha_inicio_plan", "fecha_fin_plan")

        request = self.context.get("request")
        usuario = getattr(request, "user", None) if request else None
        if usuario is not None:
            codigos = codigos_roles_de(usuario)
            if codigos.isdisjoint({"ADMIN", "PMO", "LIDER"}):
                recurso = getattr(usuario, "recurso", None)
                responsable_nuevo = attrs.get(
                    "responsable", getattr(instance, "responsable", None)
                )
                recurso_valido = recurso is not None and responsable_nuevo is not None
                if not recurso_valido or responsable_nuevo.id != recurso.id:
                    raise serializers.ValidationError(
                        {
                            "responsable": [
                                "Solo puede crear o editar tareas donde usted es el responsable."
                            ]
                        }
                    )

        padre = attrs.get("tarea_padre", getattr(instance, "tarea_padre", None))
        if padre is not None:
            tarea_para_validar = instance or Tarea(
                proyecto=attrs.get("proyecto"), pk=None
            )
            validar_jerarquia(tarea_para_validar, padre)

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        instancia = Tarea(**validated_data)
        marcar_creacion_durante_ejecucion(instancia)
        instancia.codigo = generar_codigo_tarea(instancia.proyecto)
        instancia.save()
        if instancia.tarea_padre_id:
            recalcular_avance(instancia.tarea_padre)
        return instancia

    @transaction.atomic
    def update(self, instance, validated_data):
        padre_anterior_id = instance.tarea_padre_id
        instancia = super().update(instance, validated_data)
        if instancia.tarea_padre_id:
            recalcular_avance(instancia.tarea_padre)
        if padre_anterior_id and padre_anterior_id != instancia.tarea_padre_id:
            from .models import Tarea as TareaModelo

            padre_anterior = TareaModelo.objects.filter(pk=padre_anterior_id).first()
            if padre_anterior:
                recalcular_avance(padre_anterior)
        return instancia
