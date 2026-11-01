import uuid

from django.conf import settings
from django.db import models


class ManagerActivos(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class ModeloBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    activo = models.BooleanField(default=True)

    objects = models.Manager()
    activos = ManagerActivos()

    class Meta:
        abstract = True

    def eliminar_logico(self, usuario=None):
        self.activo = False
        if usuario is not None:
            self.actualizado_por = usuario
        self.save()
