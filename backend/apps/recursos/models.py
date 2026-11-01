from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.catalogos.models import PerfilRecurso
from apps.core.choices import TipoRecurso
from apps.core.models import ModeloBase
from apps.core.validators import validar_porcentaje, validar_positivo
from apps.proyectos.models import FaseProyecto, Proyecto


class Recurso(ModeloBase):
    tipo = models.CharField(max_length=20, choices=TipoRecurso.choices)
    nombre = models.CharField(max_length=200)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recurso",
    )
    perfil = models.ForeignKey(
        PerfilRecurso, null=True, blank=True, on_delete=models.SET_NULL, related_name="recursos"
    )
    email = models.EmailField(null=True, blank=True)  # noqa: DJ001
    capacidad_horas_mes = models.DecimalField(max_digits=10, decimal_places=2, default=160)
    fecha_ingreso = models.DateField(null=True, blank=True)
    fecha_retiro = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "recurso"
        verbose_name_plural = "recursos"
        ordering = ["nombre"]
        indexes = [models.Index(fields=["nombre"])]

    def __str__(self):
        return self.nombre


class TarifaRecurso(ModeloBase):
    recurso = models.ForeignKey(Recurso, on_delete=models.CASCADE, related_name="tarifas")
    valor_hora = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[validar_positivo]
    )
    moneda = models.CharField(max_length=3, default="COP")
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "tarifa de recurso"
        verbose_name_plural = "tarifas de recurso"
        ordering = ["recurso", "-vigente_desde"]
        constraints = [
            models.UniqueConstraint(
                fields=["recurso", "vigente_desde"], name="tarifarecurso_vigencia_unica"
            ),
        ]

    def __str__(self):
        return f"{self.recurso.nombre} — {self.valor_hora} desde {self.vigente_desde}"


class AsignacionRecurso(ModeloBase):
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, related_name="asignaciones"
    )
    recurso = models.ForeignKey(
        Recurso, on_delete=models.CASCADE, related_name="asignaciones"
    )
    fase = models.ForeignKey(
        FaseProyecto,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="asignaciones",
    )
    rol_en_proyecto = models.CharField(max_length=120)
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField()
    porcentaje_dedicacion = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[validar_porcentaje]
    )
    horas_planeadas = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[validar_positivo]
    )
    valor_hora_plan = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[validar_positivo]
    )
    costo_planeado = models.DecimalField(max_digits=18, decimal_places=2, editable=False)

    class Meta:
        verbose_name = "asignación de recurso"
        verbose_name_plural = "asignaciones de recurso"
        ordering = ["proyecto", "recurso", "fecha_desde"]
        constraints = [
            models.UniqueConstraint(
                fields=["proyecto", "recurso", "fase", "fecha_desde"],
                name="asignacionrecurso_unica",
            ),
            models.CheckConstraint(
                condition=Q(fecha_hasta__gte=models.F("fecha_desde")),
                name="asignacionrecurso_fin_despues_de_inicio",
            ),
        ]

    def __str__(self):
        return f"{self.proyecto.codigo} — {self.recurso.nombre} ({self.fecha_desde})"

    def save(self, *args, **kwargs):
        self.costo_planeado = self.horas_planeadas * self.valor_hora_plan
        super().save(*args, **kwargs)
