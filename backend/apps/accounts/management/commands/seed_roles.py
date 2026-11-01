from django.apps import apps as django_apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.accounts.models import RolMeta
from apps.accounts.permisos_matriz import LETRA_A_ACCION, MATRIZ_PERMISOS, MODELOS_POR_RECURSO

ROLES_SISTEMA = [
    ("ADMIN", "Administrador", 1),
    ("PMO", "PMO / Dirección", 2),
    ("LIDER", "Líder de proyecto", 3),
    ("RECURSO", "Recurso / Ejecutor", 4),
    ("CONSULTA", "Consulta", 5),
]


class Command(BaseCommand):
    help = "Siembra los cinco roles del sistema (PLAN.md §5) y sus permisos de Django."

    def handle(self, *args, **options):
        grupos_por_codigo = self._sembrar_grupos_y_roles()
        self._sembrar_permisos(grupos_por_codigo)
        self.stdout.write(self.style.SUCCESS("Roles y permisos sembrados."))

    def _sembrar_grupos_y_roles(self):
        grupos = {}
        for codigo, descripcion, orden in ROLES_SISTEMA:
            grupo, _ = Group.objects.get_or_create(name=descripcion)
            RolMeta.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "grupo": grupo,
                    "descripcion": descripcion,
                    "es_sistema": True,
                    "orden": orden,
                },
            )
            grupos[codigo] = grupo
        return grupos

    def _sembrar_permisos(self, grupos_por_codigo):
        for recurso, modelos in MODELOS_POR_RECURSO.items():
            letras_por_rol = MATRIZ_PERMISOS[recurso]
            for codigo_rol, letras in letras_por_rol.items():
                grupo = grupos_por_codigo[codigo_rol]
                acciones = [LETRA_A_ACCION[letra] for letra in letras if letra in LETRA_A_ACCION]
                if not acciones:
                    continue
                for ruta_modelo in modelos:
                    self._asignar_permisos_modelo(grupo, ruta_modelo, acciones)

    def _asignar_permisos_modelo(self, grupo, ruta_modelo, acciones):
        app_label, nombre_modelo = ruta_modelo.split(".")
        modelo = django_apps.get_model(app_label, nombre_modelo)
        content_type = ContentType.objects.get_for_model(modelo)
        for accion in acciones:
            permiso, _ = Permission.objects.get_or_create(
                codename=f"{accion}_{modelo._meta.model_name}",
                content_type=content_type,
                defaults={"name": f"Can {accion} {modelo._meta.verbose_name}"},
            )
            grupo.permissions.add(permiso)
