from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.core.choices import EstadoProyecto
from apps.tablero.services import resumen_ejecucion as calcular_resumen_ejecucion

from .models import EntregableHito, FaseProyecto, Hito, Proyecto, RubroPresupuesto
from .services import generar_codigo_proyecto, validar_presupuesto

# `generar_codigo_proyecto` bloquea la última fila con ese prefijo —si existe
# alguna—, pero no protege contra una fila *nueva* insertada por otra
# transacción mientras la primera esperaba el candado (el `SELECT ... FOR
# UPDATE ... ORDER BY ... LIMIT 1` de Postgres no vuelve a evaluar el filtro
# tras desbloquearse; solo revalida la fila que ya había elegido). Bajo
# creación concurrente eso puede hacer que dos transacciones calculen el
# mismo código; la restricción `UniqueConstraint` de `codigo` lo detecta al
# insertar y aquí se reintenta con un código nuevo en vez de devolver un 500
# (fase 11 §11.1.3: confirmado con una prueba de concurrencia real).
INTENTOS_CODIGO_PROYECTO = 5


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

    # `validar_pesos_fases` (suma de `peso` == 100) NO se valida acá: una
    # regla que exige "==" en cada guardado individual hace imposible
    # redistribuir el peso entre dos fases ya existentes (cualquier paso
    # intermedio de una edición fila por fila deja la suma en más o menos
    # de 100). `FaseProyectoViewSet.perform_create`/`perform_update` sí la
    # aplica (mismo comportamiento de antes para quien use ese endpoint
    # fila por fila); `ProyectoViewSet.guardar_fases_lote` la aplica una
    # sola vez al final de guardar todas las fases juntas (fase-05 adenda).


class EntregableHitoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntregableHito
        fields = [
            "id",
            "proyecto",
            "hito",
            "nombre",
            "descripcion",
            "estado",
            "fecha_entrega",
            "activo",
        ]

    def validate(self, attrs):
        hito = attrs.get("hito", getattr(self.instance, "hito", None))
        proyecto = attrs.get("proyecto", getattr(self.instance, "proyecto", None))
        if hito is not None and proyecto is not None and hito.proyecto_id != proyecto.id:
            raise serializers.ValidationError(
                {"hito": ["El hito no pertenece a este proyecto."]}
            )
        return attrs


class HitoSerializer(serializers.ModelSerializer):
    entregables = serializers.SerializerMethodField()

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
            "entregables",
            "activo",
        ]

    def get_entregables(self, obj) -> list[dict]:
        # Se filtra en Python (no con `.filter`) para aprovechar el prefetch.
        activos = [e for e in obj.entregables.all() if e.activo]
        return EntregableHitoSerializer(activos, many=True).data


class RubroPresupuestoSerializer(serializers.ModelSerializer):
    """A diferencia de `FaseProyectoSerializer`, `validar_presupuesto`
    (`presupuesto_dinero >= suma de rubros`) sí se valida en cada guardado:
    no tiene el problema de "==" de los pesos de fase, porque es un `>=`
    — agregar o editar un rubro de a uno nunca deja un estado intermedio
    inválido que haga falta corregir con otro rubro a la vez."""

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

    @transaction.atomic
    def create(self, validated_data):
        instancia = super().create(validated_data)
        validar_presupuesto(instancia.proyecto)
        return instancia

    @transaction.atomic
    def update(self, instance, validated_data):
        instancia = super().update(instance, validated_data)
        validar_presupuesto(instancia.proyecto)
        return instancia


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
            "en_produccion",
            "en_soporte",
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
            "en_produccion",
            "en_soporte",
        ]
        read_only_fields = ["id", "codigo"]

    def validate(self, attrs):
        estado = self.instance.estado if self.instance else None
        if (attrs.get("en_produccion") or attrs.get("en_soporte")) and (
            estado != EstadoProyecto.PRODUCCION_SOPORTE
        ):
            raise serializers.ValidationError(
                {
                    "en_produccion": [
                        "Solo se puede indicar cuando el proyecto está en «Producción y soporte»."
                    ]
                }
            )
        _validar_fin_despues_de_inicio(
            attrs, self.instance, "fecha_inicio_plan", "fecha_fin_plan"
        )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        for intento in range(INTENTOS_CODIGO_PROYECTO):
            try:
                with transaction.atomic():
                    validated_data["codigo"] = generar_codigo_proyecto()
                    instancia = super().create(validated_data)
                break
            except IntegrityError:
                if intento == INTENTOS_CODIGO_PROYECTO - 1:
                    raise
        validar_presupuesto(instancia)
        return instancia

    @transaction.atomic
    def update(self, instance, validated_data):
        instancia = super().update(instance, validated_data)
        validar_presupuesto(instancia)
        return instancia
