from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.choices import EstadoAprobacion, Periodicidad
from apps.core.models import ModeloBase
from apps.core.validators import validar_positivo
from apps.proyectos.models import Proyecto, RubroPresupuesto
from apps.recursos.models import Recurso
from apps.tareas.models import Tarea


class RegistroEjecucion(ModeloBase):
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, related_name="registros_ejecucion"
    )
    tarea = models.ForeignKey(
        Tarea, null=True, blank=True, on_delete=models.SET_NULL, related_name="registros_ejecucion"
    )
    recurso = models.ForeignKey(
        Recurso, on_delete=models.CASCADE, related_name="registros_ejecucion"
    )
    periodicidad = models.CharField(max_length=10, choices=Periodicidad.choices)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    horas = models.DecimalField(max_digits=10, decimal_places=2, validators=[validar_positivo])
    valor_hora_aplicado = models.DecimalField(max_digits=18, decimal_places=2, editable=False)
    costo = models.DecimalField(max_digits=18, decimal_places=2, editable=False)
    descripcion = models.TextField(blank=True)
    estado_aprobacion = models.CharField(
        max_length=10, choices=EstadoAprobacion.choices, default=EstadoAprobacion.BORRADOR
    )
    motivo_rechazo = models.TextField(blank=True)
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registros_ejecucion_aprobados",
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registros_ejecucion_registrados",
    )

    class Meta:
        verbose_name = "registro de ejecución"
        verbose_name_plural = "registros de ejecución"
        ordering = ["-periodo_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["recurso", "proyecto", "tarea", "periodicidad", "periodo_inicio"],
                name="registroejecucion_unico",
            ),
            models.CheckConstraint(
                condition=Q(horas__gt=0), name="registroejecucion_horas_positivas"
            ),
            models.CheckConstraint(
                condition=Q(periodo_fin__gte=models.F("periodo_inicio")),
                name="registroejecucion_fin_despues_de_inicio",
            ),
        ]
        indexes = [
            models.Index(fields=["proyecto", "periodo_inicio"]),
            models.Index(fields=["recurso", "periodo_inicio"]),
            models.Index(fields=["estado_aprobacion"]),
        ]

    def __str__(self):
        return f"{self.recurso.nombre} — {self.periodo_inicio} ({self.horas} h)"

    def save(self, *args, **kwargs):
        self.costo = self.horas * self.valor_hora_aplicado
        super().save(*args, **kwargs)


class GastoEjecutado(ModeloBase):
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, related_name="gastos_ejecutados"
    )
    rubro = models.ForeignKey(
        RubroPresupuesto, on_delete=models.CASCADE, related_name="gastos_ejecutados"
    )
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=18, decimal_places=2, validators=[validar_positivo])
    proveedor = models.CharField(max_length=200, blank=True)
    numero_documento = models.CharField(max_length=60, blank=True)
    descripcion = models.TextField(blank=True)
    estado_aprobacion = models.CharField(
        max_length=10, choices=EstadoAprobacion.choices, default=EstadoAprobacion.BORRADOR
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gastos_ejecutados_aprobados",
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "gasto ejecutado"
        verbose_name_plural = "gastos ejecutados"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.proyecto.codigo} — {self.rubro.descripcion}: {self.monto}"
