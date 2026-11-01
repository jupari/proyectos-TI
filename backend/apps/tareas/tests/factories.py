import datetime

import factory

from apps.core.choices import EstadoTarea, Prioridad, TipoDependencia, TipoTarea
from apps.proyectos.tests.factories import ProyectoFactory
from apps.tareas.models import DependenciaTarea, Tarea


class TareaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tarea
        django_get_or_create = ["proyecto", "codigo"]

    proyecto = factory.SubFactory(ProyectoFactory)
    codigo = factory.LazyAttributeSequence(lambda o, n: f"{o.proyecto.codigo}-T{n:03d}")
    nombre = factory.Faker("sentence", nb_words=4, locale="es_CO")
    tipo = TipoTarea.TAREA
    estado = EstadoTarea.PENDIENTE
    prioridad = Prioridad.MEDIA
    fecha_inicio_plan = datetime.date(2026, 1, 1)
    fecha_fin_plan = datetime.date(2026, 1, 31)
    horas_estimadas = 40


class DependenciaTareaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DependenciaTarea
        django_get_or_create = ["tarea_origen", "tarea_destino"]

    tarea_origen = factory.SubFactory(TareaFactory)
    tarea_destino = factory.SubFactory(TareaFactory)
    tipo = TipoDependencia.FI
    dias_desfase = 0
