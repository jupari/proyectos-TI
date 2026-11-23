"""Lectura de las incidencias de un proyecto de Jira y su traducción a tareas
(docs/plan/fase-14-jira-tareas-sprints.md). Esta fase es **solo lectura**: no
escribe nada en la base; resume qué traería la importación (tipos, estados,
sprints, épicas, estimaciones y responsables) para revisar la traducción de
estados con datos reales antes de importar de verdad."""

import re
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from apps.core.choices import EstadoTarea, TipoTarea
from apps.recursos.models import Recurso

MUESTRA_FILAS = 25
CATEGORIAS_JIRA = {"new": "Por hacer", "indeterminate": "En curso", "done": "Listo"}

_RE_BLOQUEADO = re.compile(r"bloquea|blocked|impedi|on hold|en espera", re.IGNORECASE)
_RE_REVISION = re.compile(r"revis|review|qa|prueba|testing", re.IGNORECASE)
_RE_CANCELADO = re.compile(r"cancel|descart|won'?t do|rechaz|duplicad", re.IGNORECASE)
_RE_HISTORIA = re.compile(r"historia|story", re.IGNORECASE)
_RE_INCIDENCIA = re.compile(r"bug|error|incident|defect", re.IGNORECASE)


def estado_app_para(nombre_estado, categoria):
    """Traducción propuesta de un estado de Jira a `EstadoTarea`. La categoría
    (`new`/`indeterminate`/`done`) manda; el nombre solo afina los estados que
    Jira no distingue por categoría (bloqueado, en revisión, cancelado)."""
    nombre = nombre_estado or ""
    if categoria == "done":
        return EstadoTarea.CANCELADA if _RE_CANCELADO.search(nombre) else EstadoTarea.COMPLETADA
    if _RE_BLOQUEADO.search(nombre):
        return EstadoTarea.BLOQUEADA
    if _RE_REVISION.search(nombre):
        return EstadoTarea.EN_REVISION
    if categoria == "indeterminate":
        return EstadoTarea.EN_PROGRESO
    return EstadoTarea.PENDIENTE


def _es_epica(tipo_incidencia):
    tipo = tipo_incidencia or {}
    if tipo.get("hierarchyLevel") == 1:
        return True
    return (tipo.get("name") or "").strip().lower() in {"epic", "épica", "epica"}


def tipo_app_para(tipo_incidencia):
    """`TipoTarea` para un tipo de incidencia de Jira (las épicas no son tareas)."""
    tipo = tipo_incidencia or {}
    nombre = tipo.get("name") or ""
    if tipo.get("subtask") or tipo.get("hierarchyLevel") == -1:
        return TipoTarea.TAREA
    if _RE_HISTORIA.search(nombre):
        return TipoTarea.HISTORIA
    if _RE_INCIDENCIA.search(nombre):
        return TipoTarea.INCIDENCIA
    return TipoTarea.TAREA


def _horas(segundos):
    if not segundos:
        return None
    return float((Decimal(segundos) / Decimal(3600)).quantize(Decimal("0.01"), ROUND_HALF_UP))


def _fecha(valor):
    return valor[:10] if valor else None


def _sprints_de(valor):
    """Los sprints que Jira devuelve en el campo personalizado (lista de objetos)."""
    sprints = []
    for crudo in valor or []:
        if not isinstance(crudo, dict) or "id" not in crudo:
            continue
        sprints.append(
            {
                "id": crudo["id"],
                "nombre": crudo.get("name", ""),
                "estado": (crudo.get("state") or "").lower(),
                "fecha_inicio": _fecha(crudo.get("startDate")),
                "fecha_fin": _fecha(crudo.get("endDate")),
                "fecha_cierre": _fecha(crudo.get("completeDate")),
                "meta": crudo.get("goal") or "",
            }
        )
    return sprints


def normalizar_incidencia(incidencia, campo_sprint=""):
    """Una incidencia cruda de Jira con solo lo que usa la importación."""
    campos = incidencia.get("fields", {})
    estado = campos.get("status") or {}
    categoria = (estado.get("statusCategory") or {}).get("key", "")
    padre = campos.get("parent") or {}
    padre_campos = padre.get("fields", {})
    responsable = campos.get("assignee") or {}
    sprints = _sprints_de(campos.get(campo_sprint)) if campo_sprint else []
    # Si está en varios sprints (arrastrada), vale el activo o, si no, el último.
    sprint = next((s for s in sprints if s["estado"] == "active"), sprints[-1] if sprints else None)
    padre_es_epica = bool(padre) and _es_epica(padre_campos.get("issuetype"))

    return {
        "clave": incidencia["key"],
        "resumen": campos.get("summary", ""),
        "es_epica": _es_epica(campos.get("issuetype")),
        "tipo": tipo_app_para(campos.get("issuetype")),
        "tipo_jira": (campos.get("issuetype") or {}).get("name", ""),
        "estado_jira": estado.get("name", ""),
        "categoria": categoria,
        "estado": estado_app_para(estado.get("name"), categoria),
        "padre_clave": padre.get("key"),
        "epica_clave": padre.get("key") if padre_es_epica else "",
        "epica_nombre": padre_campos.get("summary", "") if padre_es_epica else "",
        "responsable_id": responsable.get("accountId"),
        "responsable_nombre": responsable.get("displayName", ""),
        "prioridad": (campos.get("priority") or {}).get("name", ""),
        "horas_estimadas": _horas(campos.get("timeoriginalestimate")),
        "horas_registradas": _horas(campos.get("timespent")),
        "vencimiento": campos.get("duedate"),
        "sprint": sprint,
        "sprints": sprints,
    }


def resumir_incidencias(incidencias, *, clave_proyecto, campo_sprint="", truncado=False):
    """Resumen de lo que traería la importación, sin tocar la base de datos."""
    normalizadas = [normalizar_incidencia(i, campo_sprint) for i in incidencias]
    epicas = {n["clave"]: n["resumen"] for n in normalizadas if n["es_epica"]}
    tareas = [n for n in normalizadas if not n["es_epica"]]

    # Las subtareas heredan la épica de su historia (Jira solo la pone en el padre).
    epica_de = {n["clave"]: (n["epica_clave"], n["epica_nombre"]) for n in tareas}
    for tarea in tareas:
        if not tarea["epica_clave"] and tarea["padre_clave"] in epica_de:
            tarea["epica_clave"], tarea["epica_nombre"] = epica_de[tarea["padre_clave"]]
        if tarea["epica_clave"]:
            epicas.setdefault(tarea["epica_clave"], tarea["epica_nombre"])

    por_estado = Counter((t["estado_jira"], t["categoria"], t["estado"]) for t in tareas)
    estados = [
        {
            "nombre": nombre,
            "categoria": CATEGORIAS_JIRA.get(categoria, categoria or "—"),
            "estado_app": estado_app,
            "cantidad": cantidad,
        }
        for (nombre, categoria, estado_app), cantidad in sorted(
            por_estado.items(), key=lambda par: (-par[1], par[0][0])
        )
    ]

    sprints = {}
    for tarea in tareas:
        for sprint in tarea["sprints"]:
            actual = sprints.setdefault(sprint["id"], {**sprint, "incidencias": 0})
            actual["incidencias"] += 1
    sprints_ordenados = sorted(
        sprints.values(), key=lambda s: (s["fecha_inicio"] or "", s["id"]), reverse=True
    )

    cuentas = Counter(
        (t["responsable_id"], t["responsable_nombre"]) for t in tareas if t["responsable_id"]
    )
    con_recurso = set(
        Recurso.objects.filter(jira_account_id__in=[c[0] for c in cuentas]).values_list(
            "jira_account_id", flat=True
        )
    )
    sin_recurso = [
        {"jira_account_id": cuenta, "nombre": nombre, "incidencias": cantidad}
        for (cuenta, nombre), cantidad in cuentas.most_common()
        if cuenta not in con_recurso
    ]

    advertencias = []
    if truncado:
        advertencias.append(
            "El proyecto tiene más incidencias de las que se leen de una vez; "
            "acote la consulta con una fecha «Desde»."
        )
    if not campo_sprint:
        advertencias.append(
            "Esta instancia de Jira no tiene el campo Sprint: no se importarán sprints."
        )
    estados_sin_categoria = [e["nombre"] for e in estados if e["categoria"] == "—"]
    if estados_sin_categoria:
        advertencias.append(
            "Estados sin categoría de Jira (se tratan como Pendiente): "
            + ", ".join(estados_sin_categoria)
        )

    return {
        "clave_proyecto": clave_proyecto,
        "total_incidencias": len(tareas),
        "truncado": truncado,
        "por_tipo": dict(Counter(t["tipo"] for t in tareas)),
        "estados": estados,
        "sprints": sprints_ordenados,
        "epicas": [{"clave": k, "nombre": v} for k, v in sorted(epicas.items())],
        "sin_estimacion": sum(1 for t in tareas if t["horas_estimadas"] is None),
        "sin_responsable": sum(1 for t in tareas if not t["responsable_id"]),
        "sin_sprint": sum(1 for t in tareas if t["sprint"] is None),
        "responsables_sin_recurso": sin_recurso,
        "advertencias": advertencias,
        "muestra": [
            {
                "clave": t["clave"],
                "resumen": t["resumen"],
                "tipo": t["tipo"],
                "tipo_jira": t["tipo_jira"],
                "estado_jira": t["estado_jira"],
                "estado_app": t["estado"],
                "responsable": t["responsable_nombre"],
                "horas_estimadas": t["horas_estimadas"],
                "sprint": t["sprint"]["nombre"] if t["sprint"] else None,
                "epica": t["epica_clave"],
                "padre": t["padre_clave"],
            }
            for t in tareas[:MUESTRA_FILAS]
        ],
    }


def simular_importacion_tareas(clave_proyecto, desde=None, cliente=None):
    """Lee el proyecto de Jira y devuelve el resumen de lo que se importaría."""
    from apps.ejecucion.integraciones.jira_tempo import ClienteJiraTempo

    cliente = cliente or ClienteJiraTempo()
    lectura = cliente.buscar_incidencias(clave_proyecto, desde)
    return resumir_incidencias(
        lectura["incidencias"],
        clave_proyecto=clave_proyecto,
        campo_sprint=lectura["campo_sprint"],
        truncado=lectura["truncado"],
    )
