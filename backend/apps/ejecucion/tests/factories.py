import datetime

import factory

from apps.core.choices import EstadoAprobacion, Periodicidad
from apps.ejecucion.models import GastoEjecutado, RegistroEjecucion
from apps.proyectos.tests.factories import ProyectoFactory, RubroPresupuestoFactory
from apps.recursos.tests.factories import RecursoFactory


class RegistroEjecucionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RegistroEjecucion
        django_get_or_create = ["recurso", "proyecto", "tarea", "periodicidad", "periodo_inicio"]

    proyecto = factory.SubFactory(ProyectoFactory)
    tarea = None
    recurso = factory.SubFactory(RecursoFactory)
    periodicidad = Periodicidad.DIARIA
    periodo_inicio = datetime.date(2026, 1, 5)
    periodo_fin = datetime.date(2026, 1, 5)
    horas = 8
    valor_hora_aplicado = 70000
    descripcion = "Trabajo de desarrollo"
    estado_aprobacion = EstadoAprobacion.APROBADO


class GastoEjecutadoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GastoEjecutado
        django_get_or_create = ["proyecto", "rubro", "fecha", "numero_documento"]

    proyecto = factory.SubFactory(ProyectoFactory)
    rubro = factory.SubFactory(RubroPresupuestoFactory)
    fecha = datetime.date(2026, 1, 15)
    monto = 1_000_000
    proveedor = "Proveedor Demo S.A.S."
    numero_documento = factory.Sequence(lambda n: f"FAC-{n:05d}")
    estado_aprobacion = EstadoAprobacion.APROBADO
