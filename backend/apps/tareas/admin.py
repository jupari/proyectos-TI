from django.contrib import admin

from .models import DependenciaTarea, Tarea


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = [
        "codigo",
        "nombre",
        "proyecto",
        "estado",
        "prioridad",
        "responsable",
        "avance",
        "activo",
    ]
    list_filter = ["estado", "prioridad", "tipo", "creada_durante_ejecucion", "activo"]
    search_fields = ["codigo", "nombre", "proyecto__codigo", "proyecto__nombre"]
    date_hierarchy = "fecha_inicio_plan"
    autocomplete_fields = ["proyecto", "fase", "tarea_padre", "responsable"]
    readonly_fields = ["horas_ejecutadas", "creado_en", "actualizado_en"]


@admin.register(DependenciaTarea)
class DependenciaTareaAdmin(admin.ModelAdmin):
    list_display = ["tarea_origen", "tarea_destino", "tipo", "dias_desfase"]
    list_filter = ["tipo"]
    search_fields = ["tarea_origen__codigo", "tarea_destino__codigo"]
    autocomplete_fields = ["tarea_origen", "tarea_destino"]
    readonly_fields = ["creado_en", "actualizado_en"]
