"""Regla de negocio de tareas, actividades y su programación
(docs/plan/fase-07-tareas-programacion.md §7.1)."""

import datetime
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.choices import EstadoProyecto, EstadoTarea, TipoDependencia, TipoEvento
from apps.core.exceptions import ErrorConflicto
from apps.core.services import registrar_evento

PROFUNDIDAD_MAXIMA = 3
ESTADOS_TERMINALES_TAREA = {EstadoTarea.COMPLETADA, EstadoTarea.CANCELADA}


def generar_codigo_tarea(proyecto):
    """`<codigo_proyecto>-T<secuencia de 3 dígitos>`. Bloquea la fila del
    proyecto (no la de la última tarea, que podría no existir aún) para
    serializar la generación de código entre tareas creadas en paralelo
    sobre el mismo proyecto, igual que `generar_codigo_proyecto`."""
    from apps.proyectos.models import Proyecto
    from apps.tareas.models import Tarea

    prefijo = f"{proyecto.codigo}-T"
    with transaction.atomic():
        Proyecto.objects.select_for_update().get(pk=proyecto.pk)
        ultima = (
            Tarea.objects.select_for_update()
            .filter(proyecto=proyecto, codigo__startswith=prefijo)
            .order_by("-codigo")
            .first()
        )
        siguiente = int(ultima.codigo.rsplit("T", 1)[-1]) + 1 if ultima else 1
        return f"{prefijo}{siguiente:03d}"


def _profundidad(tarea):
    """Profundidad de `tarea` en su jerarquía: 1 para una raíz, 2 para su
    hija, etc."""
    profundidad = 1
    actual = tarea.tarea_padre
    while actual is not None:
        profundidad += 1
        actual = actual.tarea_padre
    return profundidad


def validar_jerarquia(tarea, padre):
    """`padre` debe ser del mismo proyecto que `tarea`, `tarea` no puede ser
    su propio ancestro, y la profundidad resultante no puede superar
    `PROFUNDIDAD_MAXIMA`. Se usa tanto en create como en update (reasignar
    `tarea_padre`), por lo que `tarea` puede llegar sin `pk` todavía."""
    if padre is None:
        return

    if padre.proyecto_id != tarea.proyecto_id:
        raise ValidationError(
            {"tarea_padre": ["La tarea padre debe ser del mismo proyecto."]}
        )

    actual = padre
    while actual is not None:
        if tarea.pk is not None and actual.pk == tarea.pk:
            raise ValidationError(
                {"tarea_padre": ["Una tarea no puede ser su propio ancestro."]}
            )
        actual = actual.tarea_padre

    if _profundidad(padre) >= PROFUNDIDAD_MAXIMA:
        raise ValidationError(
            {
                "tarea_padre": [
                    f"La jerarquía admite máximo {PROFUNDIDAD_MAXIMA} niveles; "
                    "esa tarea padre ya está en el último nivel permitido."
                ]
            }
        )


def detectar_ciclo(origen, destino):
    """Antes de crear la dependencia `origen -> destino`, recorre en
    profundidad las dependencias salientes de `destino` buscando un camino
    de vuelta a `origen`; si existe, crearla cerraría un ciclo. Lanza
    `ErrorConflicto` con la ruta completa del ciclo en `detalles` (incluido
    el código de origen al principio y al final), que es lo que hace útil
    el error para quien lo lee."""
    from apps.tareas.models import DependenciaTarea

    if origen.pk == destino.pk:
        raise ErrorConflicto({"tarea_destino": ["Una tarea no puede depender de sí misma."]})

    pila = [(destino, [origen.codigo, destino.codigo])]
    visitados = {destino.pk}
    while pila:
        actual, ruta = pila.pop()
        if actual.pk == origen.pk:
            raise ErrorConflicto({"ciclo": ruta})
        salientes = DependenciaTarea.objects.filter(
            activo=True, tarea_origen=actual
        ).select_related("tarea_destino")
        for dependencia in salientes:
            siguiente = dependencia.tarea_destino
            if siguiente.pk in visitados:
                continue
            visitados.add(siguiente.pk)
            pila.append((siguiente, [*ruta, siguiente.codigo]))


def recalcular_avance(tarea):
    """`avance` de una tarea con subtareas activas es el promedio ponderado
    por `horas_estimadas` de sus hijas (simple si todas pesan 0), nunca un
    valor escrito directamente. Se dispara al guardar una subtarea y sube
    recursivamente hasta la raíz."""
    subtareas = list(tarea.subtareas.filter(activo=True))
    if not subtareas:
        return

    total_horas = sum((sub.horas_estimadas for sub in subtareas), Decimal("0"))
    if total_horas > 0:
        suma_ponderada = sum(
            (sub.avance * sub.horas_estimadas for sub in subtareas), Decimal("0")
        )
        avance = suma_ponderada / total_horas
    else:
        avance = sum((sub.avance for sub in subtareas), Decimal("0")) / len(subtareas)

    tarea.avance = avance.quantize(Decimal("0.01"))
    tarea.save(update_fields=["avance", "actualizado_en"])

    if tarea.tarea_padre_id:
        recalcular_avance(tarea.tarea_padre)


def marcar_creacion_durante_ejecucion(tarea):
    """Si el proyecto está en `EJECUCION` al crear `tarea`, exige
    `motivo_creacion` y marca `creada_durante_ejecucion=True`. Alimenta el
    indicador de alcance adicional del tablero (fase 10)."""
    if tarea.proyecto.estado == EstadoProyecto.EJECUCION:
        if not tarea.motivo_creacion:
            raise ValidationError(
                {
                    "motivo_creacion": [
                        "Debe indicar el motivo: el proyecto ya está en ejecución."
                    ]
                }
            )
        tarea.creada_durante_ejecucion = True
    return tarea


@transaction.atomic
def cambiar_estado_tarea(
    tarea, estado_nuevo, usuario, *, fecha_inicio_real=None, fecha_fin_real=None, nota=None
):
    hoy = datetime.date.today()
    estado_anterior = tarea.estado
    campos = ["estado", "actualizado_en"]

    if estado_nuevo == EstadoTarea.EN_PROGRESO:
        tarea.fecha_inicio_real = fecha_inicio_real or tarea.fecha_inicio_real or hoy
        campos.append("fecha_inicio_real")

    if estado_nuevo == EstadoTarea.COMPLETADA:
        subtareas_abiertas = tarea.subtareas.filter(activo=True).exclude(
            estado__in=ESTADOS_TERMINALES_TAREA
        )
        if subtareas_abiertas.exists():
            raise ErrorConflicto(
                {"estado": ["No se puede completar una tarea con subtareas abiertas."]}
            )
        tarea.fecha_fin_real = fecha_fin_real or tarea.fecha_fin_real or hoy
        tarea.avance = Decimal("100")
        campos += ["fecha_fin_real", "avance"]

    if estado_nuevo == EstadoTarea.BLOQUEADA and not nota:
        raise ValidationError({"nota": ["Debe indicar el motivo del bloqueo."]})

    tarea.estado = estado_nuevo
    tarea.save(update_fields=campos)

    if tarea.tarea_padre_id:
        recalcular_avance(tarea.tarea_padre)

    despues = {"estado": estado_nuevo}
    if nota:
        despues["nota"] = nota
    registrar_evento(
        tipo_evento=TipoEvento.CAMBIO_ESTADO,
        entidad="Tarea",
        entidad_id=tarea.id,
        descripcion=f"Cambio de estado de {tarea.codigo}: {estado_anterior} → {estado_nuevo}.",
        proyecto=tarea.proyecto,
        antes={"estado": estado_anterior},
        despues=despues,
        usuario=usuario,
    )
    return tarea


def fechas_sugeridas(tarea):
    """Fecha de inicio más temprana posible según las dependencias `FI`
    entrantes de `tarea` (fin del predecesor + 1 día + `dias_desfase`; el
    día adicional es la convención de que una tarea `FI` empieza el día
    siguiente al que termina su predecesora, no el mismo día). Es
    **sugerencia**: no se impone, la UI solo ofrece rellenar los campos con
    el resultado. Conserva la duración original de `tarea` para sugerir
    también la fecha de fin."""
    dependencias = tarea.dependencias_entrantes.filter(
        activo=True, tipo=TipoDependencia.FI
    ).select_related("tarea_origen")
    candidatas = [
        dependencia.tarea_origen.fecha_fin_plan
        + datetime.timedelta(days=1 + dependencia.dias_desfase)
        for dependencia in dependencias
    ]
    if not candidatas:
        return {"fecha_inicio_sugerida": None, "fecha_fin_sugerida": None}

    fecha_inicio = max(candidatas)
    duracion = (tarea.fecha_fin_plan - tarea.fecha_inicio_plan).days
    return {
        "fecha_inicio_sugerida": fecha_inicio,
        "fecha_fin_sugerida": fecha_inicio + datetime.timedelta(days=duracion),
    }
