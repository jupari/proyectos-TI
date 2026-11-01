import datetime

import factory

from apps.core.choices import TipoRecurso
from apps.proyectos.tests.factories import ProyectoFactory
from apps.recursos.models import AsignacionRecurso, Recurso, TarifaRecurso


class RecursoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Recurso
        django_get_or_create = ["nombre"]

    tipo = TipoRecurso.INTERNO
    nombre = factory.Faker("name", locale="es_CO")
    email = factory.LazyAttribute(lambda o: f"{o.nombre.split()[0].lower()}@seguimiento.local")
    capacidad_horas_mes = 160
    fecha_ingreso = datetime.date(2024, 1, 1)


class TarifaRecursoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TarifaRecurso
        django_get_or_create = ["recurso", "vigente_desde"]

    recurso = factory.SubFactory(RecursoFactory)
    valor_hora = 70000
    moneda = "COP"
    vigente_desde = datetime.date(2024, 1, 1)


class AsignacionRecursoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AsignacionRecurso
        django_get_or_create = ["proyecto", "recurso", "fase", "fecha_desde"]

    proyecto = factory.SubFactory(ProyectoFactory)
    recurso = factory.SubFactory(RecursoFactory)
    fase = None
    rol_en_proyecto = "Analista funcional"
    fecha_desde = datetime.date(2026, 1, 1)
    fecha_hasta = datetime.date(2026, 6, 30)
    porcentaje_dedicacion = 50
    horas_planeadas = 400
    valor_hora_plan = 70000
