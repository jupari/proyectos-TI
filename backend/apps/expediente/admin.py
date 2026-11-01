from django.contrib import admin

from .models import DocumentoExpediente, EntradaBitacora


@admin.register(DocumentoExpediente)
class DocumentoExpedienteAdmin(admin.ModelAdmin):
    list_display = [
        "proyecto",
        "nombre",
        "categoria",
        "version",
        "es_version_vigente",
        "tamano_bytes",
        "activo",
    ]
    list_filter = ["categoria", "es_version_vigente", "activo"]
    search_fields = ["nombre", "nombre_original", "proyecto__codigo", "proyecto__nombre"]
    autocomplete_fields = ["proyecto", "seguimiento", "tarea", "documento_padre"]
    readonly_fields = [
        "nombre_original",
        "mime",
        "tamano_bytes",
        "hash_sha256",
        "creado_en",
        "actualizado_en",
    ]


@admin.register(EntradaBitacora)
class EntradaBitacoraAdmin(admin.ModelAdmin):
    list_display = ["ocurrido_en", "proyecto", "tipo_evento", "entidad", "usuario"]
    list_filter = ["tipo_evento", "entidad"]
    search_fields = ["descripcion", "proyecto__codigo", "proyecto__nombre"]
    date_hierarchy = "ocurrido_en"
    autocomplete_fields = ["proyecto", "usuario"]
    readonly_fields = [field.name for field in EntradaBitacora._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
