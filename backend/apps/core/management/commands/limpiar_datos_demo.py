"""Borra todos los datos de `seed_demo` para empezar a cargar datos reales:
proyectos (y todo lo que cuelga de ellos: fases, hitos, rubros, asignaciones,
tareas, registros de ejecución, gastos, seguimientos, compromisos,
documentos del expediente y bitácora), recursos, áreas, portafolios,
perfiles de recurso, y los usuarios de demostración de `seed_demo`
(`USUARIOS_DEMO`) — **salvo cualquier usuario `is_superuser`**, para no
dejar la aplicación sin con quién entrar.

Los roles (`RolMeta`/`Group`) nunca se tocan: son catálogo de la aplicación,
no datos de ejemplo.

El orden de borrado importa: `Proyecto.area_solicitante` y
`Proyecto.gerente` son `PROTECT`, así que los proyectos se borran primero
(arrastran en cascada casi todo lo demás) y solo después los catálogos y los
usuarios que pudieran estar protegidos por ellos.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalogos.models import Area, PerfilRecurso, Portafolio
from apps.core.management.commands.seed_demo import USUARIOS_DEMO
from apps.proyectos.models import Proyecto
from apps.recursos.models import Recurso

Usuario = get_user_model()


class Command(BaseCommand):
    help = (
        "Borra todos los datos de seed_demo (proyectos, recursos, catálogos y "
        "usuarios de demostración)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--si",
            action="store_true",
            help="No pedir confirmación interactiva (útil en scripts/CI).",
        )

    def handle(self, *args, **options):
        if not options["si"]:
            respuesta = input(
                "Esto borra TODOS los proyectos, recursos, catálogos y usuarios de "
                "demostración de la base de datos actual. Esta acción no se puede "
                "deshacer. Escriba 'si' para continuar: "
            )
            if respuesta.strip().lower() != "si":
                raise CommandError("Operación cancelada.")

        with transaction.atomic():
            resumen = self._borrar_todo()

        self.stdout.write(self.style.SUCCESS("Datos de demostración eliminados:"))
        for etiqueta, total in resumen.items():
            self.stdout.write(f"  {etiqueta}: {total}")

    def _borrar_todo(self):
        resumen = {}

        # 1. Proyectos primero: arrastran en cascada fases, hitos, rubros,
        # asignaciones, tareas, registros de ejecución, gastos, seguimientos
        # (y sus compromisos), documentos del expediente y bitácora.
        resumen["proyectos (y dependientes)"] = Proyecto.objects.all().delete()[0]

        # 2. Recursos: ahora sin asignaciones/registros que los referencien.
        resumen["recursos"] = Recurso.objects.all().delete()[0]

        # 3. Catálogos: ahora sin ningún proyecto que los proteja.
        resumen["áreas"] = Area.objects.all().delete()[0]
        resumen["portafolios"] = Portafolio.objects.all().delete()[0]
        resumen["perfiles de recurso"] = PerfilRecurso.objects.all().delete()[0]

        # 4. Usuarios de demostración, nunca los `is_superuser` (para no
        # quedarse sin con quién entrar a la aplicación).
        correos_demo = [correo for correo, *_ in USUARIOS_DEMO]
        resumen["usuarios de demostración"] = (
            Usuario.objects.filter(email__in=correos_demo, is_superuser=False).delete()[0]
        )

        return resumen
