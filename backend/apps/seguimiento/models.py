from django.conf import settings
from django.db import models

from apps.core.choices import EstadoCompromiso, EstadoSeguimiento, Periodicidad, Semaforo
from apps.core.models import ModeloBase
from apps.core.validators import validar_porcentaje
from apps.proyectos.models import Proyecto


class Seguimiento(ModeloBase):
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, related_name="seguimientos"
    )
    periodicidad = models.CharField(max_length=10, choices=Periodicidad.choices)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    fecha_corte = models.DateField()
    avance_reportado = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[validar_porcentaje]
    )
    semaforo = models.CharField(max_length=10, choices=Semaforo.choices)
    semaforo_calculado = models.CharField(
        max_length=10, choices=Semaforo.choices, default=Semaforo.VERDE, editable=False
    )
    justificacion_semaforo = models.TextField(blank=True)
    logros = models.TextField(blank=True)
    dificultades = models.TextField(blank=True)
    riesgos = models.TextField(blank=True)
    acciones_siguientes = models.TextField(blank=True)
    horas_periodo = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    costo_periodo = models.DecimalField(max_digits=18, decimal_places=2, default=0, editable=False)
    horas_acumuladas = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, editable=False
    )
    costo_acumulado = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, editable=False
    )
    estado = models.CharField(
        max_length=10, choices=EstadoSeguimiento.choices, default=EstadoSeguimiento.BORRADOR
    )
    publicado_en = models.DateTimeField(null=True, blank=True)
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="seguimientos_publicados",
    )

    class Meta:
        verbose_name = "seguimiento"
        verbose_name_plural = "seguimientos"
        ordering = ["-fecha_corte"]
        constraints = [
            models.UniqueConstraint(
                fields=["proyecto", "periodicidad", "periodo_inicio"],
                name="seguimiento_unico",
            ),
        ]
        indexes = [models.Index(fields=["proyecto", "fecha_corte"])]

    def __str__(self):
        return f"{self.proyecto.codigo} — {self.periodo_inicio} a {self.periodo_fin}"


class CompromisoSeguimiento(ModeloBase):
    seguimiento = models.ForeignKey(
        Seguimiento, on_delete=models.CASCADE, related_name="compromisos"
    )
    descripcion = models.TextField()
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="compromisos_asignados"
    )
    fecha_compromiso = models.DateField()
    estado = models.CharField(
        max_length=15, choices=EstadoCompromiso.choices, default=EstadoCompromiso.ABIERTO
    )
    fecha_cumplimiento = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "compromiso de seguimiento"
        verbose_name_plural = "compromisos de seguimiento"
        ordering = ["fecha_compromiso"]

    def __str__(self):
        return f"{self.seguimiento} — {self.descripcion[:60]}"

    @property
    def esta_vencido(self):
        from datetime import date

        return self.estado == EstadoCompromiso.ABIERTO and self.fecha_compromiso < date.today()
