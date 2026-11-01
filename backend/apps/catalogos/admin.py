from django.contrib import admin

from .models import Area, PerfilRecurso, Portafolio


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "responsable", "activo"]
    list_filter = ["activo"]
    search_fields = ["codigo", "nombre"]
    autocomplete_fields = ["responsable"]
    readonly_fields = ["creado_en", "actualizado_en"]


@admin.register(Portafolio)
class PortafolioAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "responsable", "activo"]
    list_filter = ["activo"]
    search_fields = ["codigo", "nombre"]
    autocomplete_fields = ["responsable"]
    readonly_fields = ["creado_en", "actualizado_en"]


@admin.register(PerfilRecurso)
class PerfilRecursoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "tarifa_hora_referencia", "moneda", "activo"]
    list_filter = ["moneda", "activo"]
    search_fields = ["codigo", "nombre"]
    readonly_fields = ["creado_en", "actualizado_en"]
