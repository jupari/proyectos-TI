import factory

from apps.catalogos.models import Area, PerfilRecurso, Portafolio


class AreaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Area
        django_get_or_create = ["codigo"]

    codigo = factory.Sequence(lambda n: f"AREA-{n:02d}")
    nombre = factory.Faker("word", locale="es_CO")


class PortafolioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Portafolio
        django_get_or_create = ["codigo"]

    codigo = factory.Sequence(lambda n: f"PORT-{n:02d}")
    nombre = factory.Faker("word", locale="es_CO")
    descripcion = factory.Faker("sentence", locale="es_CO")


class PerfilRecursoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PerfilRecurso
        django_get_or_create = ["codigo"]

    codigo = factory.Sequence(lambda n: f"PERFIL-{n:02d}")
    nombre = "Perfil genérico"
    tarifa_hora_referencia = 80000
    moneda = "COP"
