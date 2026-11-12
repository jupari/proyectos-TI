"""Reglas de negocio del seguimiento periódico (docs/plan/fase-09-seguimiento-expediente.md
§9.1 y docs/modelo-datos.md §7)."""

import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.choices import (
    EstadoAprobacion,
    EstadoCompromiso,
    EstadoSeguimiento,
    EstadoTarea,
    TipoEvento,
)
from apps.core.exceptions import ErrorConflicto
from apps.core.periodos import normalizar_periodo
from apps.core.services import registrar_evento
from apps.tablero.services import semaforo_calculado

CERO = Decimal("0")


def _horas_y_costo_entre(proyecto, desde, hasta):
    agregado = proyecto.registros_ejecucion.filter(
        activo=True,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        periodo_inicio__gte=desde,
        periodo_fin__lte=hasta,
    ).aggregate(horas=Sum("horas"), costo=Sum("costo"))
    return agregado["horas"] or CERO, agregado["costo"] or CERO


def _avance_anterior(proyecto, periodo_inicio):
    anterior = (
        proyecto.seguimientos.filter(activo=True, periodo_inicio__lt=periodo_inicio)
        .order_by("-periodo_inicio")
        .first()
    )
    return anterior.avance_reportado if anterior else CERO


def precargar(proyecto, periodicidad, periodo_inicio):
    """Borrador **sin guardar** con todo lo que necesita el formulario de
    seguimiento: lo calculado (congelable al publicar) y las listas
    informativas de apoyo para redactar (no se guardan en el modelo)."""
    periodo_inicio_norm, periodo_fin = normalizar_periodo(periodicidad, periodo_inicio)
    fecha_corte = min(periodo_fin, timezone.localdate())

    horas_periodo, costo_periodo = _horas_y_costo_entre(proyecto, periodo_inicio_norm, periodo_fin)
    horas_acumuladas, costo_acumulado = _horas_y_costo_entre(
        proyecto, proyecto.fecha_inicio_plan, fecha_corte
    )

    tareas_completadas_en_periodo = list(
        proyecto.tareas.filter(
            activo=True,
            estado=EstadoTarea.COMPLETADA,
            fecha_fin_real__gte=periodo_inicio_norm,
            fecha_fin_real__lte=periodo_fin,
        )
    )
    tareas_vencidas = list(
        proyecto.tareas.filter(activo=True, fecha_fin_plan__lt=fecha_corte).exclude(
            estado__in=[EstadoTarea.COMPLETADA, EstadoTarea.CANCELADA]
        )
    )
    hitos_del_periodo = list(
        proyecto.hitos.filter(
            activo=True, fecha_plan__gte=periodo_inicio_norm, fecha_plan__lte=periodo_fin
        )
    )
    tareas_creadas_en_periodo = list(
        proyecto.tareas.filter(
            activo=True,
            creado_en__date__gte=periodo_inicio_norm,
            creado_en__date__lte=periodo_fin,
        )
    )

    return {
        "proyecto": proyecto,
        "periodicidad": periodicidad,
        "periodo_inicio": periodo_inicio_norm,
        "periodo_fin": periodo_fin,
        "fecha_corte": fecha_corte,
        "horas_periodo": horas_periodo,
        "costo_periodo": costo_periodo,
        "horas_acumuladas": horas_acumuladas,
        "costo_acumulado": costo_acumulado,
        "semaforo_calculado": semaforo_calculado(proyecto, fecha_corte),
        "avance_reportado": _avance_anterior(proyecto, periodo_inicio_norm),
        "tareas_completadas_en_periodo": tareas_completadas_en_periodo,
        "tareas_vencidas": tareas_vencidas,
        "hitos_del_periodo": hitos_del_periodo,
        "tareas_creadas_en_periodo": tareas_creadas_en_periodo,
    }


@transaction.atomic
def publicar(seguimiento, usuario):
    if seguimiento.estado != EstadoSeguimiento.BORRADOR:
        raise ErrorConflicto("Solo se puede publicar un seguimiento en borrador.")

    calculado = semaforo_calculado(seguimiento.proyecto, seguimiento.fecha_corte)
    if seguimiento.semaforo != calculado and not seguimiento.justificacion_semaforo.strip():
        raise ValidationError(
            {
                "justificacion_semaforo": [
                    "El semáforo declarado difiere del calculado "
                    f"({calculado}); debe justificarlo."
                ]
            }
        )

    datos = precargar(seguimiento.proyecto, seguimiento.periodicidad, seguimiento.periodo_inicio)

    seguimiento.semaforo_calculado = calculado
    seguimiento.horas_periodo = datos["horas_periodo"]
    seguimiento.costo_periodo = datos["costo_periodo"]
    seguimiento.horas_acumuladas = datos["horas_acumuladas"]
    seguimiento.costo_acumulado = datos["costo_acumulado"]
    seguimiento.estado = EstadoSeguimiento.PUBLICADO
    seguimiento.publicado_en = timezone.now()
    seguimiento.publicado_por = usuario
    seguimiento.save(
        update_fields=[
            "semaforo_calculado",
            "horas_periodo",
            "costo_periodo",
            "horas_acumuladas",
            "costo_acumulado",
            "estado",
            "publicado_en",
            "publicado_por",
            "actualizado_en",
        ]
    )

    proyecto = seguimiento.proyecto
    proyecto.avance_reportado = seguimiento.avance_reportado
    proyecto.semaforo = seguimiento.semaforo
    proyecto.save(update_fields=["avance_reportado", "semaforo", "actualizado_en"])

    registrar_evento(
        tipo_evento=TipoEvento.PUBLICACION,
        entidad="Seguimiento",
        entidad_id=seguimiento.id,
        descripcion=(
            f"Seguimiento {seguimiento.periodicidad} de {proyecto.codigo} "
            f"({seguimiento.periodo_inicio} a {seguimiento.periodo_fin}) publicado."
        ),
        proyecto=proyecto,
        despues={
            "avance_reportado": str(seguimiento.avance_reportado),
            "semaforo": seguimiento.semaforo,
        },
        usuario=usuario,
    )
    return seguimiento


@transaction.atomic
def reabrir(seguimiento, usuario):
    if seguimiento.estado != EstadoSeguimiento.PUBLICADO:
        raise ErrorConflicto("Solo se puede reabrir un seguimiento publicado.")

    seguimiento.estado = EstadoSeguimiento.BORRADOR
    seguimiento.publicado_en = None
    seguimiento.publicado_por = None
    seguimiento.save(
        update_fields=["estado", "publicado_en", "publicado_por", "actualizado_en"]
    )

    registrar_evento(
        tipo_evento=TipoEvento.CAMBIO_ESTADO,
        entidad="Seguimiento",
        entidad_id=seguimiento.id,
        descripcion=f"Seguimiento de {seguimiento.proyecto.codigo} reabierto para corrección.",
        proyecto=seguimiento.proyecto,
        antes={"estado": EstadoSeguimiento.PUBLICADO},
        despues={"estado": EstadoSeguimiento.BORRADOR},
        usuario=usuario,
    )
    return seguimiento


@transaction.atomic
def convertir_en_tarea(
    compromiso,
    usuario,
    *,
    horas_estimadas,
    fecha_inicio_plan=None,
    fecha_fin_plan=None,
    responsable=None,
    fase=None,
):
    """Crea una `Tarea` a partir de `compromiso` y la enlaza (`compromiso.tarea`):
    así queda en el cronograma del proyecto y es medible en horas. Al
    completarse esa tarea, `cambiar_estado_tarea` cierra el compromiso
    automáticamente (ver `apps.tareas.services`)."""
    from apps.tareas.models import Tarea
    from apps.tareas.services import generar_codigo_tarea, marcar_creacion_durante_ejecucion

    if compromiso.tarea_id is not None:
        raise ErrorConflicto(
            f"Este compromiso ya fue convertido en la tarea {compromiso.tarea.codigo}."
        )
    if compromiso.estado in (EstadoCompromiso.CUMPLIDO, EstadoCompromiso.CANCELADO):
        raise ErrorConflicto("No se puede convertir un compromiso cumplido o cancelado.")
    if horas_estimadas is None or horas_estimadas <= 0:
        raise ValidationError({"horas_estimadas": ["Debe ser mayor que cero."]})

    proyecto = compromiso.seguimiento.proyecto
    fin = fecha_fin_plan or compromiso.fecha_compromiso
    # Si el compromiso ya venció, iniciar "hoy" dejaría fin < inicio; en ese
    # caso la ventana colapsa al día del vencimiento, lo cual es correcto:
    # la tarea nace ya atrasada, no con fechas inconsistentes.
    inicio = fecha_inicio_plan or min(datetime.date.today(), fin)
    if fin < inicio:
        raise ValidationError(
            {"fecha_fin_plan": ["Debe ser igual o posterior a la fecha de inicio."]}
        )
    if fase is not None and fase.proyecto_id != proyecto.id:
        raise ValidationError({"fase": ["La fase debe ser del mismo proyecto."]})
    if responsable is None:
        responsable = getattr(compromiso.responsable, "recurso", None)

    tarea = Tarea(
        proyecto=proyecto,
        fase=fase,
        nombre=compromiso.descripcion[:250],
        descripcion=compromiso.descripcion,
        responsable=responsable,
        fecha_inicio_plan=inicio,
        fecha_fin_plan=fin,
        horas_estimadas=horas_estimadas,
        motivo_creacion="Convertida desde un compromiso de seguimiento.",
    )
    marcar_creacion_durante_ejecucion(tarea)
    tarea.codigo = generar_codigo_tarea(proyecto)
    tarea.save()

    compromiso.tarea = tarea
    compromiso.save(update_fields=["tarea", "actualizado_en"])

    registrar_evento(
        tipo_evento=TipoEvento.CREACION,
        entidad="Tarea",
        entidad_id=tarea.id,
        descripcion=f"Tarea {tarea.codigo} creada a partir de un compromiso de seguimiento.",
        proyecto=proyecto,
        usuario=usuario,
    )
    return tarea


def marcar_compromisos_vencidos():
    """`VENCIDO` para los `ABIERTO` cuya `fecha_compromiso` ya pasó. En v1
    se corre a mano o por tarea programada del sistema operativo (sin
    Celery, fuera de alcance); ver `management/commands/actualizar_compromisos.py`."""
    from .models import CompromisoSeguimiento

    hoy = datetime.date.today()
    return CompromisoSeguimiento.objects.filter(
        activo=True, estado=EstadoCompromiso.ABIERTO, fecha_compromiso__lt=hoy
    ).update(estado=EstadoCompromiso.VENCIDO)
