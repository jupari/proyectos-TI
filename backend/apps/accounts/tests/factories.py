import factory

from apps.accounts.models import Usuario


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
