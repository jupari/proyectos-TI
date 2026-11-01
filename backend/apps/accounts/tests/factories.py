import factory
from django.contrib.auth.models import Group

from apps.accounts.models import RolMeta, Usuario

ROLES_SISTEMA = [
    ("ADMIN", "Administrador", 1),
    ("PMO", "PMO / Dirección", 2),
    ("LIDER", "Líder de proyecto", 3),
    ("RECURSO", "Recurso / Ejecutor", 4),
    ("CONSULTA", "Consulta", 5),
]


class UsuarioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Usuario
        django_get_or_create = ["email"]
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"usuario{n}@seguimiento.local")
    nombres = factory.Faker("first_name", locale="es_CO")
    apellidos = factory.Faker("last_name", locale="es_CO")
    cargo = "Colaborador"
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if create:
            self.set_password(extracted or "Seguimiento2026!")
            self.save()


def sembrar_roles():
    """Crea (idempotente) los cinco roles del sistema y sus grupos."""
    roles = {}
    for codigo, descripcion, orden in ROLES_SISTEMA:
        grupo, _ = Group.objects.get_or_create(name=descripcion)
        rol, _ = RolMeta.objects.get_or_create(
            codigo=codigo,
            defaults={
                "grupo": grupo,
                "descripcion": descripcion,
                "es_sistema": True,
                "orden": orden,
            },
        )
        roles[codigo] = rol
    return roles
