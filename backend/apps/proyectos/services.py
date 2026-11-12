"""Toda la regla de negocio de proyectos vive aquí, no en los serializers
(docs/plan/fase-05-proyectos-presupuesto.md §5.2)."""

import datetime

from django.db import transaction
from django.db.models import Sum

from apps.core.choices import EstadoProyecto, EstadoTarea, TipoEvento
from apps.core.exceptions import ErrorConflicto, ErrorReglaNegocio
from apps.core.services import registrar_evento

# Grafo de transiciones válidas (docs/modelo-datos.md §3).
TRANSICIONES = {
    EstadoProyecto.BORRADOR: {EstadoProyecto.PLANEACION, EstadoProyecto.CANCELADO},
    EstadoProyecto.PLANEACION: {EstadoProyecto.EJECUCION, EstadoProyecto.CANCELADO},
    EstadoProyecto.EJECUCION: {
        EstadoProyecto.SUSPENDIDO,
        EstadoProyecto.CERRADO,
        EstadoProyecto.CANCELADO,
    },
    EstadoProyecto.SUSPENDIDO: {EstadoProyecto.EJECUCION, EstadoProyecto.CANCELADO},
    EstadoProyecto.CERRADO: {EstadoProyecto.PRODUCCION_SOPORTE},
    EstadoProyecto.CANCELADO: set(),
    EstadoProyecto.PRODUCCION_SOPORTE: set(),
}


def validar_transicion(proyecto, estado_nuevo):
    permitidos = TRANSICIONES.get(proyecto.estado, set())
    if estado_nuevo not in permitidos:
        raise ErrorConflicto(
            {
                "estado": [f"No se puede pasar de {proyecto.estado} a {estado_nuevo}."],
                "transiciones_validas": sorted(permitidos),
            }
        )


def _validar_precondiciones(proyecto, estado_nuevo):
    if estado_nuevo == EstadoProyecto.EJECUCION:
        if not proyecto.fecha_inicio_real:
            raise ErrorReglaNegocio(
                {"fecha_inicio_real": ["Debe registrar la fecha de inicio real."]}
            )
        if not proyecto.asignaciones.filter(activo=True).exists():
            raise ErrorReglaNegocio(
                {
                    "asignaciones": [
                        "El proyecto debe tener al menos una asignación de recurso."
                    ]
                }
            )
    if estado_nuevo == EstadoProyecto.CERRADO:
        if not proyecto.fecha_fin_real:
            raise ErrorReglaNegocio({"fecha_fin_real": ["Debe registrar la fecha de fin real."]})
        if proyecto.tareas.filter(activo=True, estado=EstadoTarea.EN_PROGRESO).exists():
            raise ErrorReglaNegocio(
                {"tareas": ["No puede cerrar el proyecto mientras tenga tareas en progreso."]}
            )


@transaction.atomic
def cambiar_estado(proyecto, estado_nuevo, observacion, usuario):
    validar_transicion(proyecto, estado_nuevo)
    _validar_precondiciones(proyecto, estado_nuevo)

    estado_anterior = proyecto.estado
    proyecto.estado = estado_nuevo
    proyecto.save(update_fields=["estado", "actualizado_en"])

    registrar_evento(
        tipo_evento=TipoEvento.CAMBIO_ESTADO,
        entidad="Proyecto",
        entidad_id=proyecto.id,
        descripcion=f"Cambio de estado de {proyecto.codigo}: {estado_anterior} → {estado_nuevo}.",
        proyecto=proyecto,
        antes={"estado": estado_anterior},
        despues={"estado": estado_nuevo, "observacion": observacion},
        usuario=usuario,
    )
    return proyecto


def validar_pesos_fases(proyecto):
    """La suma de `peso` de las fases activas debe ser 100 (docs/modelo-datos.md §3)."""
    suma = proyecto.fases.filter(activo=True).aggregate(total=Sum("peso"))["total"] or 0
    diferencia = suma - 100
    if diferencia > 0:
        raise ErrorReglaNegocio(
            {"peso": [f"La suma de los pesos de las fases excede 100 en {diferencia}."]}
        )
    if diferencia < 0:
        raise ErrorReglaNegocio(
            {"peso": [f"La suma de los pesos de las fases es {suma}; faltan {-diferencia}."]}
        )


def validar_presupuesto(proyecto):
    """`presupuesto_dinero` debe ser >= la suma de `RubroPresupuesto.monto_planeado`."""
    suma_rubros = (
        proyecto.rubros.filter(activo=True).aggregate(total=Sum("monto_planeado"))["total"] or 0
    )
    if proyecto.presupuesto_dinero < suma_rubros:
        raise ErrorReglaNegocio(
            {
                "presupuesto_dinero": [
                    f"El presupuesto ({proyecto.presupuesto_dinero}) es menor que la suma de "
                    f"los rubros planeados ({suma_rubros})."
                ]
            }
        )


def generar_codigo_proyecto():
    """`PRY-<año>-<secuencia de 3 dígitos>`, con bloqueo de fila sobre el
    último del año para evitar colisiones bajo escrituras concurrentes."""
    from apps.proyectos.models import Proyecto

    anio = datetime.date.today().year
    prefijo = f"PRY-{anio}-"
    with transaction.atomic():
        ultimo = (
            Proyecto.objects.select_for_update()
            .filter(codigo__startswith=prefijo)
            .order_by("-codigo")
            .first()
        )
        siguiente = int(ultimo.codigo.rsplit("-", 1)[-1]) + 1 if ultimo else 1
        return f"{prefijo}{siguiente:03d}"
