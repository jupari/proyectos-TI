from django.apps import AppConfig


class TareasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tareas"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from apps.tareas import signals
        from apps.tareas.models import Tarea

        post_save.connect(
            signals.recalcular_avance_del_proyecto,
            sender=Tarea,
            dispatch_uid="tareas.recalcular_avance_proyecto_guardar",
        )
        post_delete.connect(
            signals.recalcular_avance_del_proyecto,
            sender=Tarea,
            dispatch_uid="tareas.recalcular_avance_proyecto_borrar",
        )
