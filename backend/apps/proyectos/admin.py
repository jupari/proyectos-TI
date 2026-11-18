from django.contrib import admin

from apps.recursos.models import AsignacionRecurso

from .models import EntregableHito, FaseProyecto, Hito, Proyecto, RubroPresupuesto


class FaseProyectoInline(admin.TabularInline):
    model = FaseProyecto
    extra = 0
    fields = ["orden", "nombre", "peso", "fecha_inicio_plan", "fecha_fin_plan", "estado"]


class HitoInline(admin.TabularInline):
    model = Hito
    extra = 0
    fields = ["nombre", "fecha_plan", "fecha_real", "estado", "es_entregable"]


class RubroPresupuestoInline(admin.TabularInline):
    model = RubroPresupuesto
    extra = 0
    fields = ["categoria", "descripcion", "monto_planeado", "monto_ejecutado"]
    readonly_fields = ["monto_ejecutado"]


class AsignacionRecursoInline(admin.TabularInline):
    model = AsignacionRecurso
    extra = 0
    fields = [
        "recurso",
        "fase",
        "rol_en_proyecto",
        "fecha_desde",
        "fecha_hasta",
        "horas_planeadas",
        "valor_hora_plan",
        "costo_planeado",
    ]
    readonly_fields = ["costo_planeado"]
    autocomplete_fields = ["recurso", "fase"]


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = [
        "codigo",
        "nombre",
        "estado",
        "prioridad",
        "semaforo",
        "gerente",
        "fecha_inicio_plan",
        "fecha_fin_plan",
        "activo",
    ]
    list_filter = ["estado", "prioridad", "semaforo", "portafolio", "area_solicitante", "activo"]
    search_fields = ["codigo", "nombre"]
    date_hierarchy = "fecha_inicio_plan"
    autocomplete_fields = ["portafolio", "area_solicitante", "gerente", "lider_tecnico"]
    readonly_fields = ["semaforo", "creado_en", "actualizado_en"]
    inlines = [FaseProyectoInline, HitoInline, RubroPresupuestoInline, AsignacionRecursoInline]


@admin.register(FaseProyecto)
class FaseProyectoAdmin(admin.ModelAdmin):
    list_display = ["proyecto", "orden", "nombre", "peso", "estado"]
    list_filter = ["estado"]
    search_fields = ["nombre", "proyecto__codigo", "proyecto__nombre"]
    autocomplete_fields = ["proyecto"]
    readonly_fields = ["creado_en", "actualizado_en"]


@admin.register(Hito)
class HitoAdmin(admin.ModelAdmin):
    list_display = ["proyecto", "nombre", "fecha_plan", "estado", "es_entregable"]
    list_filter = ["estado", "es_entregable"]
    search_fields = ["nombre", "proyecto__codigo", "proyecto__nombre"]
    date_hierarchy = "fecha_plan"
    autocomplete_fields = ["proyecto"]
    readonly_fields = ["creado_en", "actualizado_en"]


@admin.register(RubroPresupuesto)
class RubroPresupuestoAdmin(admin.ModelAdmin):
    list_display = ["proyecto", "categoria", "descripcion", "monto_planeado", "monto_ejecutado"]
    list_filter = ["categoria"]
    search_fields = ["descripcion", "proyecto__codigo", "proyecto__nombre"]
    autocomplete_fields = ["proyecto"]
    readonly_fields = ["monto_ejecutado", "creado_en", "actualizado_en"]


@admin.register(EntregableHito)
class EntregableHitoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "hito", "proyecto", "estado", "fecha_entrega"]
    list_filter = ["estado"]
    search_fields = ["nombre", "hito__nombre"]
