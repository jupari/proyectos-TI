import uuid

import factory

from apps.core.choices import CategoriaDocumento, TipoEvento
from apps.expediente.models import DocumentoExpediente, EntradaBitacora
from apps.proyectos.tests.factories import ProyectoFactory


class DocumentoExpedienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentoExpediente
        django_get_or_create = ["proyecto", "nombre", "version"]

    proyecto = factory.SubFactory(ProyectoFactory)
    categoria = CategoriaDocumento.INFORME
    nombre = factory.Faker("word", locale="es_CO")
    version = 1
    archivo = factory.django.FileField(data=b"contenido de demostracion", filename="demo.txt")
    nombre_original = "demo.txt"
    mime = "text/plain"
    tamano_bytes = 25
    hash_sha256 = factory.Sequence(lambda n: f"{n:064d}")


class EntradaBitacoraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntradaBitacora
        django_get_or_create = ["proyecto", "descripcion"]

    proyecto = factory.SubFactory(ProyectoFactory)
    tipo_evento = TipoEvento.CREACION
    entidad = "Proyecto"
    entidad_id = factory.LazyFunction(uuid.uuid4)
    descripcion = "Creación del proyecto de demostración."
