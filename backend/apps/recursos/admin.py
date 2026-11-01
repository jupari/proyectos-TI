from django.contrib import admin

from .models import AsignacionRecurso, Recurso, TarifaRecurso


class TarifaRecursoInline(admin.TabularInline):
    model = TarifaRecurso
    extra = 0
    fields = ["valor_hora", "moneda", "vigente_desde", "vigente_hasta"]


@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "perfil", "usuario", "capacidad_horas_mes", "activo"]
    list_filter = ["tipo", "activo"]
    search_fields = ["nombre", "email"]
    autocomplete_fields = ["usuario", "perfil"]
    readonly_fields = ["creado_en", "actualizado_en"]
    inlines = [TarifaRecursoInline]


@admin.register(TarifaRecurso)
class TarifaRecursoAdmin(admin.ModelAdmin):
    list_display = ["recurso", "valor_hora", "moneda", "vigente_desde", "vigente_hasta"]
    list_filter = ["moneda"]
    search_fields = ["recurso__nombre"]
    autocomplete_fields = ["recurso"]
    readonly_fields = ["creado_en", "actualizado_en"]


@admin.register(AsignacionRecurso)
class AsignacionRecursoAdmin(admin.ModelAdmin):
    list_display = [
        "proyecto",
        "recurso",
        "fase",
        "fecha_desde",
        "fecha_hasta",
        "horas_planeadas",
        "costo_planeado",
    ]
    list_filter = ["proyecto"]
    search_fields = ["proyecto__codigo", "proyecto__nombre", "recurso__nombre"]
    autocomplete_fields = ["proyecto", "recurso", "fase"]
    readonly_fields = ["costo_planeado", "creado_en", "actualizado_en"]
