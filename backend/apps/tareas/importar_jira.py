"""Importación real de historias, tareas, bugs y subtareas de un proyecto de
Jira, con sus sprints y épicas (docs/plan/fase-14-jira-tareas-sprints.md).

Solo lee de Jira y es idempotente: identifica por `Tarea.clave_jira` y
`Sprint(proyecto, id_jira)`, reutilizando y reactivando lo borrado lógicamente
(el mismo fallo que hubo con las horas). Jira manda en estado, sprint,
responsable y estimación; la aplicación conserva fase, dependencias, fechas
del plan y observaciones."""

import datetime
import re
import unicodedata
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.choices import EstadoSprint, EstadoTarea, Prioridad, TipoEvento
from apps.core.services import registrar_evento
from apps.proyectos.models import Proyecto
from apps.proyectos.services import pausar_recalculo_avance, recalcular_avance_proyecto
from apps.recursos.models import Recurso

from .importacion_jira import preparar_tareas
from .models import Sprint, Tarea
from .services import generar_codigo_tarea, recalcular_avance

_PRIORIDADES = (
    (re.compile(r"highest|blocker|cr[ií]tic|urgent", re.IGNORECASE), Prioridad.CRITICA),
    (re.compile(r"high|alta|major", re.IGNORECASE), Prioridad.ALTA),
    (re.compile(r"low|baja|minor|trivial", re.IGNORECASE), Prioridad.BAJA),
)
ESTADOS_EN_CURSO = {EstadoTarea.EN_PROGRESO, EstadoTarea.BLOQUEADA, EstadoTarea.EN_REVISION}
AVANCE_MAXIMO_EN_CURSO = Decimal("90")
ESTADOS_SPRINT = {"active": EstadoSprint.ACTIVO, "closed": EstadoSprint.CERRADO}


def _normalizar_nombre(texto):
    """Nombre sin tildes ni mayúsculas y sin importar el orden de las palabras."""
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return tuple(sorted(re.findall(r"[a-z0-9]+", sin_tildes.lower())))


def asociar_recursos_por_nombre_o_correo(tareas):
    """Liga a su persona de Jira los recursos que aún no tienen cuenta asociada.

    Se reconoce por correo (si Jira lo muestra) o por nombre completo, y solo
    cuando la coincidencia es única: ante la duda no se asocia a nadie. Así las
    tareas dejan de quedar «sin asignar» solo porque nadie asoció la cuenta a
    mano. Devuelve cuántos recursos se asociaron."""
    personas = {}
    for t in tareas:
        if t["responsable_id"]:
            personas[t["responsable_id"]] = (
                t["responsable_nombre"],
                (t.get("responsable_email") or "").lower(),
            )
    ya_asociadas = set(
        Recurso.objects.filter(jira_account_id__in=personas).values_list(
            "jira_account_id", flat=True
        )
    )
    libres = list(Recurso.objects.filter(jira_account_id__isnull=True, activo=True))
    asociados = 0
    for cuenta, (nombre, email) in personas.items():
        if cuenta in ya_asociadas:
            continue
        coincidencias = [r for r in libres if email and (r.email or "").lower() == email]
        if not coincidencias and nombre:
            clave = _normalizar_nombre(nombre)
            coincidencias = [r for r in libres if _normalizar_nombre(r.nombre) == clave]
        if len(coincidencias) == 1:
            recurso = coincidencias[0]
            # update() evita llenar la bitácora con una señal por cada asociación.
            Recurso.objects.filter(pk=recurso.pk).update(jira_account_id=cuenta)
            libres.remove(recurso)
            asociados += 1
    return asociados


def prioridad_app_para(nombre):
    for patron, prioridad in _PRIORIDADES:
        if patron.search(nombre or ""):
            return prioridad
    return Prioridad.MEDIA


def _a_fecha(valor):
    return datetime.date.fromisoformat(valor) if valor else None


def avance_de(tarea_jira):
    """0 pendiente o cancelada, 100 completada y, en curso, lo registrado sobre
    la estimación original con tope en 90 (la última parte la da cerrar)."""
    estado = tarea_jira["estado"]
    if estado == EstadoTarea.COMPLETADA:
        return Decimal("100")
    estimadas = tarea_jira["horas_estimadas"]
    registradas = tarea_jira["horas_registradas"]
    if estado in ESTADOS_EN_CURSO and estimadas and registradas:
        avance = Decimal(str(registradas)) / Decimal(str(estimadas)) * 100
        return min(avance, AVANCE_MAXIMO_EN_CURSO).quantize(Decimal("0.01"))
    return Decimal("0")


def fechas_plan(tarea_jira):
    """Inicio: el del sprint o, si no, cuando se creó en Jira. Fin: el
    vencimiento, el fin del sprint o la resolución, lo que haya primero."""
    sprint = tarea_jira["sprint"] or {}
    inicio = (
        _a_fecha(sprint.get("fecha_inicio"))
        or _a_fecha(tarea_jira["creada"])
        or datetime.date.today()
    )
    fin = (
        _a_fecha(tarea_jira["vencimiento"])
        or _a_fecha(sprint.get("fecha_fin"))
        or _a_fecha(tarea_jira["resuelta"])
        or inicio
    )
    return inicio, max(fin, inicio)


def _profundidad_en_lote(tarea_jira, por_clave):
    profundidad = 0
    visto = set()
    actual = tarea_jira
    while actual["padre_clave"] in por_clave and actual["clave"] not in visto:
        visto.add(actual["clave"])
        actual = por_clave[actual["padre_clave"]]
        profundidad += 1
    return profundidad


def _texto_error(exc):
    detalle = getattr(exc, "detail", None)
    if detalle is None:
        return str(exc)
    if isinstance(detalle, dict):
        return "; ".join(f"{c}: {', '.join(str(m) for m in ms)}" for c, ms in detalle.items())
    if isinstance(detalle, list):
        return ", ".join(str(m) for m in detalle)
    return str(detalle)


def _guardar_sprint(proyecto, datos, resumen):
    """Crea o actualiza el `Sprint` (y reactiva uno borrado)."""
    sprint = Sprint.objects.filter(proyecto=proyecto, id_jira=datos["id"]).first()
    creado = sprint is None
    if creado:
        sprint = Sprint(proyecto=proyecto, id_jira=datos["id"])
    sprint.activo = True
    sprint.nombre = datos["nombre"][:200]
    sprint.estado = ESTADOS_SPRINT.get(datos["estado"], EstadoSprint.FUTURO)
    sprint.fecha_inicio = _a_fecha(datos["fecha_inicio"])
    sprint.fecha_fin = _a_fecha(datos["fecha_fin"])
    sprint.fecha_cierre = _a_fecha(datos["fecha_cierre"])
    sprint.meta = datos["meta"]
    sprint.save()
    resumen["sprints_creados" if creado else "sprints_actualizados"] += 1
    return sprint


def _guardar_tarea(proyecto, tarea_jira, sprint, responsables):
    existente = Tarea.objects.filter(clave_jira=tarea_jira["clave"]).first()
    if existente is not None and existente.proyecto_id != proyecto.id:
        raise ValidationError(
            {"clave_jira": [f"{tarea_jira['clave']} ya está importada en otro proyecto."]}
        )

    padre = None
    if tarea_jira["padre_clave"]:
        padre = Tarea.objects.filter(
            clave_jira=tarea_jira["padre_clave"], proyecto=proyecto
        ).first()

    creada = existente is None
    tarea = existente or Tarea(proyecto=proyecto, clave_jira=tarea_jira["clave"])
    inicio, fin = fechas_plan(tarea_jira)
    if creada:
        # Las fechas del plan son de la aplicación: se fijan al crear y no se
        # pisan en las siguientes importaciones. Una tarea que llega de Jira
        # no cuenta como alcance adicional (`creada_durante_ejecucion`).
        tarea.codigo = generar_codigo_tarea(proyecto)
        tarea.fecha_inicio_plan = inicio
        tarea.fecha_fin_plan = fin

    tarea.activo = True
    tarea.nombre = tarea_jira["resumen"][:250]
    tarea.tipo = tarea_jira["tipo"]
    tarea.estado = tarea_jira["estado"]
    tarea.prioridad = prioridad_app_para(tarea_jira["prioridad"])
    tarea.responsable = responsables.get(tarea_jira["responsable_id"])
    tarea.horas_estimadas = Decimal(str(tarea_jira["horas_estimadas"] or 0))
    tarea.avance = avance_de(tarea_jira)
    tarea.sprint = sprint
    tarea.epica_clave = tarea_jira["epica_clave"]
    tarea.epica_nombre = tarea_jira["epica_nombre"][:250]
    tarea.tarea_padre = padre
    if tarea.estado in ESTADOS_EN_CURSO | {EstadoTarea.COMPLETADA}:
        tarea.fecha_inicio_real = tarea.fecha_inicio_real or inicio
    if tarea.estado == EstadoTarea.COMPLETADA:
        tarea.fecha_fin_real = tarea.fecha_fin_real or _a_fecha(tarea_jira["resuelta"]) or fin
    tarea.save()

    # Una historia con subtareas toma su avance de ellas, no de su propio estado.
    recalcular_avance(tarea)
    if padre is not None:
        recalcular_avance(padre)
    return tarea, creada


def importar_tareas_jira(clave_proyecto, desde=None, *, dry_run=False, cliente=None, usuario=None):
    """Importa a la aplicación las incidencias de un proyecto de Jira. El
    proyecto debe estar asociado antes (`Proyecto.clave_jira`). Con `dry_run`
    hace todo y deshace los cambios."""
    from apps.ejecucion.integraciones.jira_tempo import ClienteJiraTempo

    proyecto = Proyecto.objects.filter(clave_jira=clave_proyecto, activo=True).first()
    if proyecto is None:
        raise ValidationError(
            {
                "clave_proyecto": [
                    "Ningún proyecto de la aplicación está asociado a esa clave de Jira. "
                    "Asócielo primero en Editar proyecto."
                ]
            }
        )

    resumen = {
        "clave_proyecto": clave_proyecto,
        "proyecto": f"{proyecto.codigo} — {proyecto.nombre}",
        "creadas": 0,
        "actualizadas": 0,
        "sprints_creados": 0,
        "sprints_actualizados": 0,
        "sin_responsable_asociado": [],
        "advertencias": [],
        "errores": [],
        "detalle": [],
    }
    cliente = cliente or ClienteJiraTempo()
    lectura = cliente.buscar_incidencias(clave_proyecto, desde)
    if lectura["truncado"]:
        resumen["advertencias"].append(
            "El proyecto tiene más incidencias de las que se leen de una vez; "
            "acote la importación con una fecha «Desde»."
        )

    tareas, _epicas = preparar_tareas(lectura["incidencias"], lectura["campo_sprint"])
    por_clave = {t["clave"]: t for t in tareas}
    tareas.sort(key=lambda t: _profundidad_en_lote(t, por_clave))

    cuentas = {t["responsable_id"] for t in tareas if t["responsable_id"]}
    asociar_recursos_por_nombre_o_correo(tareas)
    responsables = {
        r.jira_account_id: r for r in Recurso.objects.filter(jira_account_id__in=cuentas)
    }
    resumen["sin_responsable_asociado"] = sorted(
        {t["responsable_nombre"] for t in tareas if t["responsable_id"] not in responsables}
        - {""}
    )

    with transaction.atomic(), pausar_recalculo_avance():
        # Los sprints primero y fuera de la transacción de cada tarea: si una
        # tarea falla y se deshace, los sprints que ya usan otras no se pierden.
        sprints = {}
        for tarea_jira in tareas:
            datos = tarea_jira["sprint"]
            if datos is not None and datos["id"] not in sprints:
                sprints[datos["id"]] = _guardar_sprint(proyecto, datos, resumen)

        for tarea_jira in tareas:
            try:
                with transaction.atomic():
                    sprint = sprints.get((tarea_jira["sprint"] or {}).get("id"))
                    tarea, creada = _guardar_tarea(proyecto, tarea_jira, sprint, responsables)
            except Exception as exc:  # noqa: BLE001 - se reporta, no se interrumpe el lote
                resumen["errores"].append(
                    {
                        "clave": tarea_jira["clave"],
                        "motivo": "no se pudo guardar la tarea",
                        "detalle": _texto_error(exc),
                    }
                )
                continue
            resumen["creadas" if creada else "actualizadas"] += 1
            resumen["detalle"].append(
                {
                    "clave": tarea_jira["clave"],
                    "codigo": tarea.codigo,
                    "nombre": tarea.nombre,
                    "tipo": tarea.tipo,
                    "estado": tarea.estado,
                    "accion": "creada" if creada else "actualizada",
                }
            )

        recalcular_avance_proyecto(proyecto, forzar=True)
        registrar_evento(
            tipo_evento=TipoEvento.IMPORTACION,
            entidad="Proyecto",
            entidad_id=proyecto.id,
            descripcion=f"Importación de tareas y sprints desde Jira para {proyecto.codigo}.",
            proyecto=proyecto,
            despues={
                "creadas": resumen["creadas"],
                "actualizadas": resumen["actualizadas"],
                "errores": len(resumen["errores"]),
            },
            usuario=usuario,
        )
        if dry_run:
            transaction.set_rollback(True)
    return resumen
