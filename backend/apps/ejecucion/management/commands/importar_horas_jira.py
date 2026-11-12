"""Importa horas reales desde Jira/Tempo como `RegistroEjecucion`
(docs/plan/fase-12-integracion-jira.md). Se corre a mano; no hay disparo
automático ni botón en el frontend en esta fase."""

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.ejecucion.services import importar_horas_jira

VARIABLES_REQUERIDAS = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "TEMPO_API_TOKEN")


class Command(BaseCommand):
    help = (
        "Importa worklogs de Tempo entre --desde y --hasta como RegistroEjecucion "
        "(origen=JIRA). No modifica nada con --dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument("--desde", required=True, help="YYYY-MM-DD")
        parser.add_argument("--hasta", required=True, help="YYYY-MM-DD")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Calcula y valida todo, pero no escribe nada en la base.",
        )

    def handle(self, *args, **options):
        faltantes = [nombre for nombre in VARIABLES_REQUERIDAS if not getattr(settings, nombre)]
        if faltantes:
            raise CommandError(
                "Faltan las siguientes variables de entorno: " + ", ".join(faltantes)
            )

        try:
            desde = datetime.date.fromisoformat(options["desde"])
            hasta = datetime.date.fromisoformat(options["hasta"])
        except ValueError as exc:
            raise CommandError(f"Fecha inválida, use YYYY-MM-DD: {exc}") from exc
        if hasta < desde:
            raise CommandError("--hasta debe ser igual o posterior a --desde.")

        resumen = importar_horas_jira(desde, hasta, dry_run=options["dry_run"])

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("--dry-run: no se escribió nada en la base.\n"))

        self.stdout.write(f"Creados: {resumen['creados']}")
        self.stdout.write(f"Actualizados: {resumen['actualizados']}")
        self.stdout.write(f"Omitidos: {len(resumen['omitidos'])}")
        for omitido in resumen["omitidos"]:
            self.stdout.write(f"  - {omitido}")
        self.stdout.write(f"Errores: {len(resumen['errores'])}")
        for error in resumen["errores"]:
            self.stdout.write(self.style.ERROR(f"  - {error}"))
