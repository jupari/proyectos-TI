from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.catalogos.models import Area, Portafolio
from apps.core.choices import (
    CategoriaRubro,
    EstadoEntregable,
    EstadoFase,
    EstadoHito,
    EstadoProyecto,
    Prioridad,
    Semaforo,
)
from apps.core.models import ModeloBase
from apps.core.validators import validar_porcentaje, validar_positivo


class Proyecto(ModeloBase):
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    objetivo = models.TextField(blank=True)
    portafolio = models.ForeignKey(
        Portafolio, null=True, blank=True, on_delete=models.SET_NULL, related_name="proyectos"
    )
    area_solicitante = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="proyectos")
    gerente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="proyectos_como_gerente",
    )
    lider_tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="proyectos_como_lider",
    )
    estado = models.CharField(
        max_length=20, choices=EstadoProyecto.choices, default=EstadoProyecto.BORRADOR
    )
    # Solo se marcan cuando el estado es `PRODUCCION_SOPORTE`; un proyecto puede
    # estar en producción y en soporte a la vez.
    en_produccion = models.BooleanField(default=False)
    en_soporte = models.BooleanField(default=False)
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    fecha_inicio_plan = models.DateField()
    fecha_fin_plan = models.DateField()
    fecha_inicio_real = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateField(null=True, blank=True)
    moneda = models.CharField(max_length=3, default="COP")
    presupuesto_horas = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[validar_positivo]
    )
    presupuesto_dinero = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[validar_positivo]
    )
    avance_reportado = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, validators=[validar_porcentaje]
    )
    # Fase 14: el avance que resulta de las tareas (calculado, nunca se escribe a mano).
    # Con `avance_desde_tareas` activo, `avance_reportado` lo sigue automáticamente.
    avance_tareas = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, editable=False
    )
    avance_desde_tareas = models.BooleanField(default=False)
    semaforo = models.CharField(
        max_length=10, choices=Semaforo.choices, default=Semaforo.VERDE, editable=False
    )
    observaciones = models.TextField(blank=True)
    clave_jira = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        verbose_name = "proyecto"
        verbose_name_plural = "proyectos"
        ordering = ["-fecha_inicio_plan", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["codigo"], name="proyecto_codigo_unico"),
            models.CheckConstraint(
                condition=Q(fecha_fin_plan__gte=models.F("fecha_inicio_plan")),
                name="proyecto_fin_despues_de_inicio",
            ),
        ]
        indexes = [
            models.Index(fields=["codigo"]),
            models.Index(fields=["nombre"]),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class FaseProyecto(ModeloBase):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="fases")
    nombre = models.CharField(max_length=150)
    orden = models.PositiveIntegerField()
    peso = models.DecimalField(max_digits=5, decimal_places=2, validators=[validar_porcentaje])
    fecha_inicio_plan = models.DateField()
    fecha_fin_plan = models.DateField()
    fecha_inicio_real = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=EstadoFase.choices, default=EstadoFase.PENDIENTE
    )

    class Meta:
        verbose_name = "fase de proyecto"
        verbose_name_plural = "fases de proyecto"
        ordering = ["proyecto", "orden"]
        constraints = [
            models.UniqueConstraint(fields=["proyecto", "orden"], name="faseproyecto_orden_unico"),
        ]

    def __str__(self):
        return f"{self.proyecto.codigo} — {self.orden}. {self.nombre}"


class Hito(ModeloBase):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="hitos")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_plan = models.DateField()
    fecha_real = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=EstadoHito.choices, default=EstadoHito.PENDIENTE
    )
    criterio_cumplimiento = models.TextField(blank=True)
    es_entregable = models.BooleanField(default=False)

    class Meta:
        verbose_name = "hito"
        verbose_name_plural = "hitos"
        ordering = ["proyecto", "fecha_plan"]

    def __str__(self):
        return f"{self.proyecto.codigo} — {self.nombre}"


class EntregableHito(ModeloBase):
    """Producto concreto que se debe entregar para dar un hito por cumplido
    (acta, manual, módulo desplegado...). `proyecto` se repite aquí (igual que
    en `Hito`) para que el alcance por rol y la bitácora lo resuelvan sin
    pasar por el hito; el serializer garantiza que coincida con `hito.proyecto`."""

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="entregables")
    hito = models.ForeignKey(Hito, on_delete=models.CASCADE, related_name="entregables")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20, choices=EstadoEntregable.choices, default=EstadoEntregable.PENDIENTE
    )
    fecha_entrega = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "entregable de hito"
        verbose_name_plural = "entregables de hito"
        ordering = ["hito", "creado_en"]

    def __str__(self):
        return f"{self.hito.nombre} — {self.nombre}"


class RubroPresupuesto(ModeloBase):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="rubros")
    categoria = models.CharField(max_length=20, choices=CategoriaRubro.choices)
    descripcion = models.CharField(max_length=255)
    monto_planeado = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[validar_positivo]
    )
    monto_ejecutado = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, editable=False
    )

    class Meta:
        verbose_name = "rubro de presupuesto"
        verbose_name_plural = "rubros de presupuesto"
        ordering = ["proyecto", "categoria"]

    def __str__(self):
        return f"{self.proyecto.codigo} — {self.get_categoria_display()}: {self.descripcion}"
