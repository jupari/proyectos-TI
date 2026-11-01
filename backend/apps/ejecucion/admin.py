from django.contrib import admin

from .models import GastoEjecutado, RegistroEjecucion


@admin.register(RegistroEjecucion)
class RegistroEjecucionAdmin(admin.ModelAdmin):
    list_display = [
        "proyecto",
        "recurso",
        "tarea",
        "periodicidad",
        "periodo_inicio",
        "horas",
        "costo",
        "estado_aprobacion",
    ]
    list_filter = ["periodicidad", "estado_aprobacion"]
    search_fields = ["proyecto__codigo", "proyecto__nombre", "recurso__nombre"]
    date_hierarchy = "periodo_inicio"
    autocomplete_fields = ["proyecto", "tarea", "recurso", "aprobado_por", "registrado_por"]
    readonly_fields = ["valor_hora_aplicado", "costo", "creado_en", "actualizado_en"]


@admin.register(GastoEjecutado)
class GastoEjecutadoAdmin(admin.ModelAdmin):
    list_display = ["proyecto", "rubro", "fecha", "monto", "proveedor", "estado_aprobacion"]
    list_filter = ["estado_aprobacion"]
    search_fields = ["proyecto__codigo", "proyecto__nombre", "proveedor", "numero_documento"]
    date_hierarchy = "fecha"
    autocomplete_fields = ["proyecto", "rubro", "aprobado_por"]
    readonly_fields = ["creado_en", "actualizado_en"]
