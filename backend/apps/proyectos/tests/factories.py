import datetime

import factory

from apps.accounts.tests.factories import UsuarioFactory
from apps.catalogos.tests.factories import AreaFactory
from apps.core.choices import EstadoFase, EstadoHito, EstadoProyecto, Prioridad
from apps.proyectos.models import FaseProyecto, Hito, Proyecto, RubroPresupuesto


class ProyectoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Proyecto
        django_get_or_create = ["codigo"]

    codigo = factory.Sequence(lambda n: f"PRY-2026-{n:03d}")
    nombre = factory.Faker("catch_phrase", locale="es_CO")
    descripcion = factory.Faker("paragraph", locale="es_CO")
    objetivo = factory.Faker("sentence", locale="es_CO")
    area_solicitante = factory.SubFactory(AreaFactory)
    gerente = factory.SubFactory(UsuarioFactory)
    estado = EstadoProyecto.PLANEACION
    prioridad = Prioridad.MEDIA
    fecha_inicio_plan = datetime.date(2026, 1, 1)
    fecha_fin_plan = datetime.date(2026, 12, 31)
    moneda = "COP"
    presupuesto_horas = 1000
    presupuesto_dinero = 100_000_000


class FaseProyectoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FaseProyecto
        django_get_or_create = ["proyecto", "orden"]

    proyecto = factory.SubFactory(ProyectoFactory)
    nombre = factory.Faker("word", locale="es_CO")
    orden = factory.Sequence(lambda n: n)
    peso = 25
    fecha_inicio_plan = datetime.date(2026, 1, 1)
    fecha_fin_plan = datetime.date(2026, 3, 31)
    estado = EstadoFase.PENDIENTE


class HitoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Hito
        django_get_or_create = ["proyecto", "nombre"]

    proyecto = factory.SubFactory(ProyectoFactory)
    nombre = factory.Faker("word", locale="es_CO")
    descripcion = factory.Faker("sentence", locale="es_CO")
    fecha_plan = datetime.date(2026, 6, 30)
    estado = EstadoHito.PENDIENTE
    criterio_cumplimiento = "Entregable aceptado por el cliente"
    es_entregable = True


class RubroPresupuestoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RubroPresupuesto
        django_get_or_create = ["proyecto", "categoria", "descripcion"]

    proyecto = factory.SubFactory(ProyectoFactory)
    categoria = "LICENCIAS"
    descripcion = factory.Faker("word", locale="es_CO")
    monto_planeado = 5_000_000
