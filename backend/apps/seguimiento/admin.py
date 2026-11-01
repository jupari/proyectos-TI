from django.contrib import admin

from .models import CompromisoSeguimiento, Seguimiento


class CompromisoSeguimientoInline(admin.TabularInline):
    model = CompromisoSeguimiento
    extra = 0
    fields = ["descripcion", "responsable", "fecha_compromiso", "estado", "fecha_cumplimiento"]
    autocomplete_fields = ["responsable"]


@admin.register(Seguimiento)
class SeguimientoAdmin(admin.ModelAdmin):
    list_display = [
        "proyecto",
        "periodicidad",
        "periodo_inicio",
        "periodo_fin",
        "semaforo",
        "estado",
        "avance_reportado",
    ]
    list_filter = ["periodicidad", "semaforo", "estado"]
    search_fields = ["proyecto__codigo", "proyecto__nombre"]
    date_hierarchy = "fecha_corte"
    autocomplete_fields = ["proyecto", "publicado_por"]
    readonly_fields = [
        "semaforo_calculado",
        "horas_periodo",
        "costo_periodo",
        "horas_acumuladas",
        "costo_acumulado",
        "creado_en",
        "actualizado_en",
    ]
    inlines = [CompromisoSeguimientoInline]


@admin.register(CompromisoSeguimiento)
class CompromisoSeguimientoAdmin(admin.ModelAdmin):
    list_display = ["seguimiento", "responsable", "fecha_compromiso", "estado"]
    list_filter = ["estado"]
    search_fields = ["descripcion", "seguimiento__proyecto__codigo"]
    autocomplete_fields = ["seguimiento", "responsable"]
    readonly_fields = ["creado_en", "actualizado_en"]
