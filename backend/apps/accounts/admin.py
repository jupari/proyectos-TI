from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import RolMeta, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ["nombres", "apellidos"]
    list_display = [
        "email",
        "nombres",
        "apellidos",
        "proveedor_auth",
        "is_staff",
        "is_active",
        "activo",
    ]
    list_filter = ["proveedor_auth", "is_staff", "is_active", "activo", "groups"]
    search_fields = ["email", "nombres", "apellidos"]
    readonly_fields = ["ultimo_acceso_en", "creado_en", "actualizado_en"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Datos personales",
            {"fields": ("nombres", "apellidos", "cargo", "telefono", "avatar_url")},
        ),
        (
            "Autenticación",
            {"fields": ("proveedor_auth", "google_sub", "debe_cambiar_clave")},
        ),
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas", {"fields": ("ultimo_acceso_en", "creado_en", "actualizado_en")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nombres", "apellidos", "password1", "password2"),
            },
        ),
    )


@admin.register(RolMeta)
class RolMetaAdmin(admin.ModelAdmin):
    list_display = ["codigo", "descripcion", "orden", "es_sistema", "activo"]
    list_filter = ["es_sistema", "activo"]
    search_fields = ["codigo", "descripcion"]
    autocomplete_fields = ["grupo"]
    readonly_fields = ["creado_en", "actualizado_en"]
