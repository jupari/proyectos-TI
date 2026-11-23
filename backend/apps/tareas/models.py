from django.db import models
from django.db.models import Q

from apps.core.choices import EstadoSprint, EstadoTarea, Prioridad, TipoDependencia, TipoTarea
from apps.core.models import ModeloBase
from apps.core.validators import validar_porcentaje, validar_positivo
from apps.proyectos.models import FaseProyecto, Proyecto
from apps.recursos.models import Recurso


class Sprint(ModeloBase):
    """Sprint de Jira (fase 14). Solo se crea desde la importación: la
    aplicación no lo edita, igual que `RegistroEjecucion.origen=JIRA`."""

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="sprints")
    id_jira = models.PositiveIntegerField()
    nombre = models.CharField(max_length=200)
    estado = models.CharField(
        max_length=10, choices=EstadoSprint.choices, default=EstadoSprint.FUTURO
    )
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    fecha_cierre = models.DateField(null=True, blank=True)
    meta = models.TextField(blank=True)

    class Meta:
        verbose_name = "sprint"
        verbose_name_plural = "sprints"
        ordering = ["proyecto", "-fecha_inicio", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["proyecto", "id_jira"], name="sprint_jira_unico"),
        ]

    def __str__(self):
        return f"{self.proyecto.codigo} — {self.nombre}"


class Tarea(ModeloBase):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="tareas")
    fase = models.ForeignKey(
        FaseProyecto, null=True, blank=True, on_delete=models.SET_NULL, related_name="tareas"
    )
    tarea_padre = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="subtareas"
    )
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=250)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TipoTarea.choices, default=TipoTarea.TAREA)
    estado = models.CharField(
        max_length=20, choices=EstadoTarea.choices, default=EstadoTarea.PENDIENTE
    )
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    responsable = models.ForeignKey(
        Recurso, null=True, blank=True, on_delete=models.SET_NULL, related_name="tareas"
    )
    fecha_inicio_plan = models.DateField()
    fecha_fin_plan = models.DateField()
    fecha_inicio_real = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateField(null=True, blank=True)
    horas_estimadas = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[validar_positivo]
    )
    horas_ejecutadas = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, editable=False
    )
    avance = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, validators=[validar_porcentaje]
    )
    orden = models.PositiveIntegerField(default=0)
    creada_durante_ejecucion = models.BooleanField(default=False)
    motivo_creacion = models.TextField(blank=True)
    clave_jira = models.CharField(max_length=30, null=True, blank=True, unique=True)
    # Datos que llegan de Jira (fase 14); la aplicación no los edita.
    sprint = models.ForeignKey(
        Sprint, null=True, blank=True, on_delete=models.SET_NULL, related_name="tareas"
    )
    epica_clave = models.CharField(max_length=30, blank=True, default="")
    epica_nombre = models.CharField(max_length=250, blank=True, default="")

    class Meta:
        verbose_name = "tarea"
        verbose_name_plural = "tareas"
        ordering = ["proyecto", "orden"]
        constraints = [
            models.UniqueConstraint(fields=["proyecto", "codigo"], name="tarea_codigo_unico"),
        ]
        indexes = [
            models.Index(fields=["proyecto", "estado"]),
            models.Index(fields=["responsable", "estado"]),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class DependenciaTarea(ModeloBase):
    tarea_origen = models.ForeignKey(
        Tarea, on_delete=models.CASCADE, related_name="dependencias_salientes"
    )
    tarea_destino = models.ForeignKey(
        Tarea, on_delete=models.CASCADE, related_name="dependencias_entrantes"
    )
    tipo = models.CharField(max_length=10, choices=TipoDependencia.choices)
    dias_desfase = models.IntegerField(default=0)

    class Meta:
        verbose_name = "dependencia de tarea"
        verbose_name_plural = "dependencias de tarea"
        ordering = ["tarea_origen", "tarea_destino"]
        constraints = [
            models.UniqueConstraint(
                fields=["tarea_origen", "tarea_destino"], name="dependenciatarea_par_unico"
            ),
            models.CheckConstraint(
                condition=~Q(tarea_origen=models.F("tarea_destino")),
                name="dependenciatarea_no_autodependencia",
            ),
        ]

    def __str__(self):
        return f"{self.tarea_origen.codigo} → {self.tarea_destino.codigo} ({self.tipo})"
