"""Mantiene `Proyecto.avance_tareas` al día cuando cambia una tarea. Se conecta
en `TareasConfig.ready()` (igual que las señales de auditoría de `core`)."""

from apps.proyectos.services import recalcular_avance_proyecto


def recalcular_avance_del_proyecto(sender, instance, **kwargs):
    recalcular_avance_proyecto(instance.proyecto)
