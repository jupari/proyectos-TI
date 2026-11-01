import uuid

from django.conf import settings
from django.db import models

from apps.core.choices import CategoriaDocumento, TipoEvento
from apps.core.models import ModeloBase
from apps.core.validators import validar_extension_archivo, validar_tamano_archivo
from apps.proyectos.models import Proyecto
from apps.seguimiento.models import Seguimiento
from apps.tareas.models import Tarea


def ruta_archivo_expediente(instance, nombre_original):
    extension = nombre_original.rsplit(".", 1)[-1] if "." in nombre_original else ""
    return f"expediente/{instance.proyecto_id}/{uuid.uuid4()}.{extension}"


class DocumentoExpediente(ModeloBase):
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, related_name="documentos_expediente"
    )
    seguimiento = models.ForeignKey(
        Seguimiento,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documentos_expediente",
    )
    tarea = models.ForeignKey(
        Tarea,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documentos_expediente",
    )
    categoria = models.CharField(max_length=20, choices=CategoriaDocumento.choices)
    nombre = models.CharField(max_length=250)
    archivo = models.FileField(
        upload_to=ruta_archivo_expediente,
        validators=[validar_extension_archivo, validar_tamano_archivo],
    )
    nombre_original = models.CharField(max_length=250)
    mime = models.CharField(max_length=120, blank=True)
    tamano_bytes = models.BigIntegerField(default=0)
    hash_sha256 = models.CharField(max_length=64, blank=True)
    version = models.PositiveIntegerField(default=1)
    documento_padre = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="versiones"
    )
    es_version_vigente = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "documento de expediente"
        verbose_name_plural = "documentos de expediente"
        ordering = ["proyecto", "-creado_en"]
        indexes = [
            models.Index(fields=["proyecto"]),
            models.Index(fields=["hash_sha256"]),
        ]

    def __str__(self):
        return f"{self.proyecto.codigo} — {self.nombre} (v{self.version})"


class EntradaBitacora(ModeloBase):
    proyecto = models.ForeignKey(
        Proyecto,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="bitacora",
    )
    tipo_evento = models.CharField(max_length=30, choices=TipoEvento.choices)
    entidad = models.CharField(max_length=60)
    entidad_id = models.UUIDField()
    descripcion = models.CharField(max_length=500)
    datos_antes = models.JSONField(null=True, blank=True)
    datos_despues = models.JSONField(null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="entradas_bitacora",
    )
    ocurrido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "entrada de bitácora"
        verbose_name_plural = "entradas de bitácora"
        ordering = ["-ocurrido_en"]
        indexes = [models.Index(fields=["proyecto", "ocurrido_en"])]

    def __str__(self):
        return f"{self.ocurrido_en:%Y-%m-%d %H:%M} — {self.descripcion[:60]}"
