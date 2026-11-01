from django.conf import settings
from django.db import models

from apps.core.models import ModeloBase


class Area(ModeloBase):
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="areas_responsable",
    )

    class Meta:
        verbose_name = "área"
        verbose_name_plural = "áreas"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["codigo"], name="area_codigo_unico"),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class Portafolio(ModeloBase):
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="portafolios_responsable",
    )

    class Meta:
        verbose_name = "portafolio"
        verbose_name_plural = "portafolios"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["codigo"], name="portafolio_codigo_unico"),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class PerfilRecurso(ModeloBase):
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=120)
    tarifa_hora_referencia = models.DecimalField(max_digits=18, decimal_places=2)
    moneda = models.CharField(max_length=3, default="COP")

    class Meta:
        verbose_name = "perfil de recurso"
        verbose_name_plural = "perfiles de recurso"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["codigo"], name="perfilrecurso_codigo_unico"),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"
