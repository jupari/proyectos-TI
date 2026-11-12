"""Recalcula desde cero los tres campos derivados del proyecto
(`Tarea.horas_ejecutadas`, `RubroPresupuesto.monto_ejecutado`,
`AsignacionRecurso.costo_planeado`) y reporta cualquier diferencia contra el
valor guardado, sin modificar nada (fase 11 §11.1.4). Reutiliza las mismas
funciones de suma que usan `recalcular_tarea`/`recalcular_rubro` en
`apps.ejecucion.services` — nunca una segunda copia de la fórmula.

Sirve también en operación (docs/operacion.md): correrlo tras una migración
de datos o una sospecha de inconsistencia. Un derivado desalineado casi
siempre significa que algo escribió el campo directamente en vez de pasar
por `aprobar`/`rechazar`/`reabrir`/`save()`."""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.ejecucion.services import _suma_gastos_aprobados_rubro, _suma_horas_aprobadas_tarea
from apps.proyectos.models import RubroPresupuesto
from apps.recursos.models import AsignacionRecurso
from apps.tareas.models import Tarea


class Command(BaseCommand):
    help = (
        "Recalcula Tarea.horas_ejecutadas, RubroPresupuesto.monto_ejecutado y "
        "AsignacionRecurso.costo_planeado desde cero y reporta diferencias contra el "
        "valor guardado. No modifica nada; termina con error si encuentra alguna."
    )

    def handle(self, *args, **options):
        diferencias = [
            *self._verificar_tareas(),
            *self._verificar_rubros(),
            *self._verificar_asignaciones(),
        ]

        if diferencias:
            self.stdout.write(self.style.ERROR(f"{len(diferencias)} diferencia(s) encontrada(s):"))
            for diferencia in diferencias:
                self.stdout.write(f"  - {diferencia}")
            raise CommandError(f"{len(diferencias)} diferencia(s) de consistencia encontrada(s).")

        self.stdout.write(self.style.SUCCESS("Sin diferencias: todos los derivados cuadran."))

    def _verificar_tareas(self):
        diferencias = []
        for tarea in Tarea.objects.filter(activo=True):
            recalculado = _suma_horas_aprobadas_tarea(tarea)
            if recalculado != tarea.horas_ejecutadas:
                diferencias.append(
                    f"Tarea {tarea.codigo} ({tarea.id}): horas_ejecutadas guardado="
                    f"{tarea.horas_ejecutadas}, recalculado={recalculado}"
                )
        return diferencias

    def _verificar_rubros(self):
        diferencias = []
        for rubro in RubroPresupuesto.objects.filter(activo=True):
            recalculado = _suma_gastos_aprobados_rubro(rubro)
            if recalculado != rubro.monto_ejecutado:
                diferencias.append(
                    f"RubroPresupuesto {rubro.descripcion} ({rubro.id}): monto_ejecutado "
                    f"guardado={rubro.monto_ejecutado}, recalculado={recalculado}"
                )
        return diferencias

    def _verificar_asignaciones(self):
        diferencias = []
        for asignacion in AsignacionRecurso.objects.filter(activo=True):
            recalculado = asignacion.horas_planeadas * asignacion.valor_hora_plan
            if recalculado != (asignacion.costo_planeado or Decimal("0")):
                diferencias.append(
                    f"AsignacionRecurso ({asignacion.id}): costo_planeado guardado="
                    f"{asignacion.costo_planeado}, recalculado={recalculado}"
                )
        return diferencias
