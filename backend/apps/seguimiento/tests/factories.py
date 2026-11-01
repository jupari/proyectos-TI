import datetime

import factory

from apps.accounts.tests.factories import UsuarioFactory
from apps.core.choices import EstadoCompromiso, EstadoSeguimiento, Periodicidad, Semaforo
from apps.proyectos.tests.factories import ProyectoFactory
from apps.seguimiento.models import CompromisoSeguimiento, Seguimiento


class SeguimientoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Seguimiento
        django_get_or_create = ["proyecto", "periodicidad", "periodo_inicio"]

    proyecto = factory.SubFactory(ProyectoFactory)
    periodicidad = Periodicidad.MENSUAL
    periodo_inicio = datetime.date(2026, 1, 1)
    periodo_fin = datetime.date(2026, 1, 31)
    fecha_corte = datetime.date(2026, 1, 31)
    avance_reportado = 20
    semaforo = Semaforo.VERDE
    logros = "Avance según lo planeado."
    estado = EstadoSeguimiento.BORRADOR


class CompromisoSeguimientoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompromisoSeguimiento
        django_get_or_create = ["seguimiento", "descripcion"]

    seguimiento = factory.SubFactory(SeguimientoFactory)
    descripcion = factory.Faker("sentence", locale="es_CO")
    responsable = factory.SubFactory(UsuarioFactory)
    fecha_compromiso = datetime.date(2026, 2, 15)
    estado = EstadoCompromiso.ABIERTO
