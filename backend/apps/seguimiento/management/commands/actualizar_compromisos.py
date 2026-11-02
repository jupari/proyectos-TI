from django.core.management.base import BaseCommand

from apps.seguimiento.services import marcar_compromisos_vencidos


class Command(BaseCommand):
    help = (
        "Marca VENCIDO los CompromisoSeguimiento en ABIERTO cuya fecha_compromiso ya pasó. "
        "Sin Celery en v1: córrelo a mano o por tarea programada del sistema operativo."
    )

    def handle(self, *args, **options):
        total = marcar_compromisos_vencidos()
        self.stdout.write(self.style.SUCCESS(f"{total} compromiso(s) marcado(s) como VENCIDO."))
