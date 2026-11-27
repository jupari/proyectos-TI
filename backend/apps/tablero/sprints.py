"""Métricas de sprints y la vista «Mi trabajo» (docs/plan/fase-14-jira-tareas-sprints.md,
fase 5). Todo es de solo lectura sobre lo que ya importó la fase 3.

Dos convenciones que conviene tener presentes al leer los números:
- **Se mide con las tareas hoja** (las que no tienen subtareas activas): una
  historia con subtareas ya está representada por ellas, y contar ambas
  duplicaría las horas.
- **El burndown es una aproximación.** No se guarda el historial de cambios de
  Jira, así que el trabajo restante de cada día se reconstruye con el alcance
  *actual* del sprint y la fecha en que se cerró cada tarea. No refleja el
  trabajo que se agregó o quitó a mitad del sprint."""

import datetime
from decimal import Decimal

from django.conf import settings
from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.core.choices import EstadoSprint, EstadoTarea
from apps.core.roles import codigos_roles_de
from apps.tareas.models import Sprint, Tarea

CERO = Decimal("0")
MAX_DIAS_BURNDOWN = 120
SPRINTS_PARA_VELOCIDAD = 3
ESTADOS_TERMINALES = [EstadoTarea.COMPLETADA, EstadoTarea.CANCELADA]


def _redondear(valor):
    return float(Decimal(valor).quantize(Decimal("0.01")))


def tareas_hoja(sprint):
    """Tareas activas y no canceladas del sprint que no tienen subtareas activas."""
    con_hijas = Tarea.objects.filter(tarea_padre=OuterRef("pk"), activo=True)
    return (
        sprint.tareas.filter(activo=True)
        .exclude(estado=EstadoTarea.CANCELADA)
        .annotate(tiene_hijas=Exists(con_hijas))
        .filter(tiene_hijas=False)
    )


def metricas_sprint(sprint):
    hojas = list(tareas_hoja(sprint).values("estado", "horas_estimadas", "horas_ejecutadas"))
    comprometidas = sum((h["horas_estimadas"] for h in hojas), CERO)
    completadas = sum(
        (h["horas_estimadas"] for h in hojas if h["estado"] == EstadoTarea.COMPLETADA), CERO
    )
    ejecutadas = sum((h["horas_ejecutadas"] for h in hojas), CERO)
    tareas_completadas = sum(1 for h in hojas if h["estado"] == EstadoTarea.COMPLETADA)
    if comprometidas > 0:
        porcentaje = completadas / comprometidas * 100
    else:
        porcentaje = Decimal(tareas_completadas) / len(hojas) * 100 if hojas else CERO
    return {
        "id": str(sprint.id),
        "nombre": sprint.nombre,
        "estado": sprint.estado,
        "fecha_inicio": sprint.fecha_inicio.isoformat() if sprint.fecha_inicio else None,
        "fecha_fin": sprint.fecha_fin.isoformat() if sprint.fecha_fin else None,
        "meta": sprint.meta,
        "tareas_total": len(hojas),
        "tareas_completadas": tareas_completadas,
        "horas_comprometidas": _redondear(comprometidas),
        "horas_completadas": _redondear(completadas),
        "horas_ejecutadas": _redondear(ejecutadas),
        "porcentaje_completado": _redondear(porcentaje),
    }


def sprints_del_proyecto(proyecto):
    """Sprints del proyecto, del más reciente al más antiguo, con su velocidad
    (horas estimadas de lo que se completó). `velocidad_promedio` usa los
    últimos sprints cerrados."""
    sprints = proyecto.sprints.filter(activo=True).order_by("-fecha_inicio", "-id_jira")
    filas = [metricas_sprint(s) for s in sprints]
    cerrados = [f for f in filas if f["estado"] == EstadoSprint.CERRADO][:SPRINTS_PARA_VELOCIDAD]
    velocidad = (
        _redondear(sum(Decimal(str(f["horas_completadas"])) for f in cerrados) / len(cerrados))
        if cerrados
        else None
    )
    return {
        "sprints": filas,
        "velocidad_promedio": velocidad,
        "sprints_en_velocidad": len(cerrados),
    }


def burndown_sprint(sprint, hoy=None):
    """Trabajo restante (horas estimadas) por día, frente a la línea ideal."""
    hoy = hoy or timezone.localdate()
    resumen = metricas_sprint(sprint)
    if not (sprint.fecha_inicio and sprint.fecha_fin):
        return {
            "disponible": False,
            "motivo": "El sprint no tiene fechas de inicio y fin en Jira.",
            "sprint": resumen,
        }

    dias = (sprint.fecha_fin - sprint.fecha_inicio).days + 1
    if dias < 1 or dias > MAX_DIAS_BURNDOWN:
        return {
            "disponible": False,
            "motivo": "Las fechas del sprint no permiten dibujar el gráfico.",
            "sprint": resumen,
        }
    fechas = [sprint.fecha_inicio + datetime.timedelta(days=i) for i in range(dias)]

    hojas = list(tareas_hoja(sprint).values("estado", "horas_estimadas", "fecha_fin_real"))
    total = sum((h["horas_estimadas"] for h in hojas), CERO)

    # Fecha en la que se dio por hecha cada tarea completada, acotada al sprint.
    cierre_por_defecto = sprint.fecha_cierre or sprint.fecha_fin
    cierres = []
    for hoja in hojas:
        if hoja["estado"] != EstadoTarea.COMPLETADA:
            continue
        cierre = hoja["fecha_fin_real"] or cierre_por_defecto
        cierres.append((max(cierre, sprint.fecha_inicio), hoja["horas_estimadas"]))

    if sprint.estado == EstadoSprint.CERRADO:
        limite = sprint.fecha_fin
    else:
        limite = min(hoy, sprint.fecha_fin)
    ideal = []
    real = []
    for indice, dia in enumerate(fechas):
        fraccion = Decimal(indice) / (dias - 1) if dias > 1 else CERO
        ideal.append(_redondear(total * (1 - fraccion)))
        if dia > limite:
            real.append(None)
        else:
            hecho = sum((horas for cierre, horas in cierres if cierre <= dia), CERO)
            real.append(_redondear(total - hecho))

    return {
        "disponible": True,
        "sprint": resumen,
        "fechas": [d.isoformat() for d in fechas],
        "ideal": ideal,
        "real": real,
        "horas_comprometidas": _redondear(total),
        "nota": (
            "Aproximación: usa el alcance actual del sprint y la fecha de cierre de cada "
            "tarea; no refleja trabajo agregado o quitado durante el sprint."
        ),
    }


def _enlace_jira(clave):
    base = (settings.JIRA_BASE_URL or "").rstrip("/")
    return f"{base}/browse/{clave}" if base and clave else None


def _fila_tarea(tarea, hoy):
    return {
        "id": str(tarea.id),
        "codigo": tarea.codigo,
        "clave_jira": tarea.clave_jira,
        "enlace_jira": _enlace_jira(tarea.clave_jira),
        "nombre": tarea.nombre,
        "tipo": tarea.tipo,
        "estado": tarea.estado,
        "avance": float(tarea.avance),
        "horas_estimadas": float(tarea.horas_estimadas),
        "horas_ejecutadas": float(tarea.horas_ejecutadas),
        "horas_jira": float(tarea.horas_jira),
        "fecha_fin_plan": tarea.fecha_fin_plan.isoformat(),
        "vencida": tarea.fecha_fin_plan < hoy,
        "proyecto_id": str(tarea.proyecto_id),
        "proyecto_codigo": tarea.proyecto.codigo,
        "proyecto_nombre": tarea.proyecto.nombre,
        "sprint_nombre": tarea.sprint.nombre if tarea.sprint else None,
        "sprint_activo": bool(tarea.sprint and tarea.sprint.estado == EstadoSprint.ACTIVO),
        "responsable_id": str(tarea.responsable_id) if tarea.responsable_id else None,
        "responsable_nombre": tarea.responsable.nombre if tarea.responsable else None,
    }


def _resumen_filas(filas):
    pendientes = sum(
        (
            max(Decimal(str(f["horas_estimadas"])) - Decimal(str(f["horas_jira"])), CERO)
            for f in filas
        ),
        CERO,
    )
    return {
        "total": len(filas),
        "vencidas": sum(1 for f in filas if f["vencida"]),
        "bloqueadas": sum(1 for f in filas if f["estado"] == EstadoTarea.BLOQUEADA),
        "horas_pendientes": _redondear(pendientes),
    }


def mi_trabajo(usuario, hoy=None):
    """Tareas abiertas, con las del sprint activo primero. Una persona ve las
    del recurso ligado a su usuario (`alcance="personal"`); un `ADMIN` ve las
    de todo el equipo (`alcance="equipo"`), incluidas las sin responsable, con
    la lista de responsables para filtrar."""
    hoy = hoy or timezone.localdate()
    es_admin = "ADMIN" in codigos_roles_de(usuario)
    recurso = getattr(usuario, "recurso", None)

    if es_admin:
        consulta = Tarea.objects.filter(activo=True, proyecto__activo=True)
    elif recurso is not None:
        consulta = Tarea.objects.filter(responsable=recurso, activo=True, proyecto__activo=True)
    else:
        return {
            "alcance": "personal",
            "recurso": None,
            "mensaje": (
                "Su usuario no está asociado a un recurso, por eso no tiene tareas asignadas."
            ),
            "resumen": {"total": 0, "vencidas": 0, "bloqueadas": 0, "horas_pendientes": 0},
            "responsables": [],
            "tareas": [],
        }

    tareas = list(
        consulta.exclude(estado__in=ESTADOS_TERMINALES).select_related(
            "proyecto", "sprint", "responsable"
        )
    )
    tareas.sort(
        key=lambda t: (
            t.sprint is None or t.sprint.estado != EstadoSprint.ACTIVO,
            t.fecha_fin_plan,
            t.codigo,
        )
    )
    filas = [_fila_tarea(t, hoy) for t in tareas]

    responsables = []
    if es_admin:
        por_responsable = {}
        for fila in filas:
            clave = fila["responsable_id"]
            if clave not in por_responsable:
                por_responsable[clave] = {
                    "id": clave,
                    "nombre": fila["responsable_nombre"] or "Sin asignar",
                    "total": 0,
                }
            por_responsable[clave]["total"] += 1
        responsables = sorted(
            por_responsable.values(), key=lambda r: (r["id"] is None, r["nombre"])
        )

    return {
        "alcance": "equipo" if es_admin else "personal",
        "recurso": {"id": str(recurso.id), "nombre": recurso.nombre} if recurso else None,
        "mensaje": "",
        "resumen": _resumen_filas(filas),
        "responsables": responsables,
        "tareas": filas,
    }


def tareas_para_excel(usuario, *, proyecto=None, responsable=None, estado=None):
    """Todas las tareas del alcance de `usuario` (también las terminadas, porque ahí
    quedan las horas empleadas), con los mismos filtros de la pantalla. `responsable`
    es un id de recurso o `'sin-asignar'`."""
    es_admin = "ADMIN" in codigos_roles_de(usuario)
    recurso = getattr(usuario, "recurso", None)
    if es_admin:
        consulta = Tarea.objects.filter(activo=True, proyecto__activo=True)
    elif recurso is not None:
        consulta = Tarea.objects.filter(responsable=recurso, activo=True, proyecto__activo=True)
    else:
        return []

    if proyecto:
        consulta = consulta.filter(proyecto_id=proyecto)
    if es_admin and responsable:
        if responsable == "sin-asignar":
            consulta = consulta.filter(responsable__isnull=True)
        else:
            consulta = consulta.filter(responsable_id=responsable)
    if estado:
        consulta = consulta.filter(estado=estado)
    return list(
        consulta.select_related("proyecto", "sprint", "responsable").order_by(
            "proyecto__codigo", "responsable__nombre", "codigo"
        )
    )


def sprint_de(proyectos, sprint_id):
    """El `Sprint` si pertenece a alguno de `proyectos` (ya acotados por rol)."""
    return Sprint.objects.filter(pk=sprint_id, activo=True, proyecto__in=proyectos).first()
