from django.core.management.base import BaseCommand

from apps.proyectos.models import Proyecto
from apps.tablero.services import semaforo_calculado


class Command(BaseCommand):
    help = "Recalcula y guarda el semáforo de todos los proyectos activos."

    def handle(self, *args, **options):
        actualizados = 0
        for proyecto in Proyecto.activos.all():
            semaforo = semaforo_calculado(proyecto)
            if semaforo != proyecto.semaforo:
                proyecto.semaforo = semaforo
                proyecto.save(update_fields=["semaforo", "actualizado_en"])
                actualizados += 1
        self.stdout.write(self.style.SUCCESS(f"{actualizados} proyecto(s) actualizado(s)."))
