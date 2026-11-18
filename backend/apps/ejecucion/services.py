"""Reglas de negocio de la ingesta de ejecución (docs/plan/fase-08-ejecucion-ingesta.md
§8.1 y docs/modelo-datos.md §6): la validación de solapamiento es la pieza
más importante del proyecto porque es lo único que impide contar las mismas
horas dos veces entre periodicidades distintas."""

import datetime
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.calculos import division_segura, meses_entre, prorratear_por_mes
from apps.core.choices import (
    EstadoAprobacion,
    EstadoTarea,
    OrigenRegistro,
    Periodicidad,
    TipoEvento,
)
from apps.core.exceptions import ErrorConflicto, ErrorReglaNegocio
from apps.core.periodos import normalizar_periodo
from apps.core.roles import codigos_roles_de
from apps.core.services import registrar_evento
from apps.recursos.services import valor_hora_vigente
from apps.tareas.models import Tarea

from .models import ConfiguracionImportacionJira, RegistroEjecucion

CERO = Decimal("0")
logger = logging.getLogger("apps.ejecucion.importacion_jira")


def _detalle_legible(exc):
    """`exc.detail` de un `ValidationError`/`ErrorReglaNegocio`/`ErrorConflicto`
    es un dict o una lista de `ErrorDetail` (no un string): mostrarlo tal
    cual en el frontend se ve como `[object Object]`. Lo aplana a texto
    legible; si `exc` no tiene `.detail` (una excepción cualquiera), usa
    `str(exc)`."""
    detalle = getattr(exc, "detail", None)
    if detalle is None:
        return str(exc)
    if isinstance(detalle, dict):
        return "; ".join(
            f"{campo}: {', '.join(str(m) for m in mensajes)}" for campo, mensajes in detalle.items()
        )
    if isinstance(detalle, list):
        return ", ".join(str(m) for m in detalle)
    return str(detalle)


def preparar_registro(registro):
    """Normaliza `periodo_inicio`/`periodo_fin` según `periodicidad` y, si no
    vino dado explícitamente, resuelve `valor_hora_aplicado` con la tarifa
    vigente del recurso a `periodo_inicio` (congelada desde ese momento:
    cambios posteriores de tarifa no alteran registros ya creados). Muta
    `registro` (sin guardar; `costo` lo recalcula `RegistroEjecucion.save()`)
    y lo devuelve."""
    registro.periodo_inicio, registro.periodo_fin = normalizar_periodo(
        registro.periodicidad, registro.periodo_inicio
    )
    if not registro.valor_hora_aplicado:
        registro.valor_hora_aplicado = valor_hora_vigente(registro.recurso, registro.periodo_inicio)
    return registro


def validar_solapamiento(registro):
    """Ningún otro registro activo (de cualquier periodicidad, en estado
    distinto de `RECHAZADO`) del mismo recurso y proyecto puede intersecar
    `[periodo_inicio, periodo_fin]`: un mensual y un diario del mismo mes
    contarían las mismas horas dos veces."""
    conflictivos = RegistroEjecucion.objects.filter(
        activo=True,
        recurso=registro.recurso,
        proyecto=registro.proyecto,
        periodo_inicio__lte=registro.periodo_fin,
        periodo_fin__gte=registro.periodo_inicio,
    ).exclude(estado_aprobacion=EstadoAprobacion.RECHAZADO)
    if registro.pk:
        conflictivos = conflictivos.exclude(pk=registro.pk)
    conflictivos = list(conflictivos)

    for conflicto in conflictivos:
        if (
            conflicto.tarea_id == registro.tarea_id
            and conflicto.periodicidad == registro.periodicidad
            and conflicto.periodo_inicio == registro.periodo_inicio
        ):
            # Coincide exactamente en las columnas de `registroejecucion_unico`. DRF no genera
            # un validador automático para ese `UniqueConstraint` porque `tarea` es nullable
            # (NULL no es "igual" a NULL en SQL, así que DRF no puede garantizar la unicidad por
            # sí solo); por eso el duplicado exacto se trata aquí, con 400 en vez del 422 de un
            # solapamiento genuino entre periodos distintos.
            raise ValidationError(
                {
                    "periodo_inicio": [
                        "Ya existe un registro idéntico (mismo recurso, proyecto, tarea, "
                        "periodicidad y periodo)."
                    ]
                }
            )

    if conflictivos:
        raise ErrorReglaNegocio(
            {
                "periodo_inicio": [
                    "El periodo se solapa con registros existentes del mismo recurso y "
                    "proyecto; cuentan las mismas horas dos veces."
                ],
                "conflictos": [
                    {
                        "id": str(c.id),
                        "periodicidad": c.periodicidad,
                        "periodo_inicio": c.periodo_inicio.isoformat(),
                        "periodo_fin": c.periodo_fin.isoformat(),
                        "horas": str(c.horas),
                    }
                    for c in conflictivos
                ],
            }
        )


def validar_topes(registro):
    """Advertencias (nunca bloquean) por exceder el tope de horas de la
    periodicidad del registro."""
    advertencias = []
    if registro.periodicidad == Periodicidad.DIARIA and registro.horas > 24:
        advertencias.append(f"{registro.horas} horas supera el tope diario de 24 horas.")
    elif registro.periodicidad == Periodicidad.SEMANAL and registro.horas > 60:
        advertencias.append(f"{registro.horas} horas supera el tope semanal de 60 horas.")
    elif registro.periodicidad == Periodicidad.MENSUAL:
        tope = registro.recurso.capacidad_horas_mes * Decimal("1.5")
        if registro.horas > tope:
            advertencias.append(f"{registro.horas} horas supera el tope mensual de {tope} horas.")
    return advertencias


def validar_rango_proyecto(registro):
    """El periodo debe intersecar el rango del proyecto, tomando el más
    amplio entre fechas plan y reales (si el proyecto arrancó o cerró fuera
    de lo planeado, ese rango real también es válido para registrar)."""
    proyecto = registro.proyecto
    inicio = min(
        proyecto.fecha_inicio_plan, proyecto.fecha_inicio_real or proyecto.fecha_inicio_plan
    )
    fin = max(proyecto.fecha_fin_plan, proyecto.fecha_fin_real or proyecto.fecha_fin_plan)
    if registro.periodo_fin < inicio or registro.periodo_inicio > fin:
        raise ValidationError(
            {"periodo_inicio": ["El periodo debe intersecar las fechas del proyecto."]}
        )


def validar_tarea(registro):
    if registro.tarea is None:
        return
    if registro.tarea.proyecto_id != registro.proyecto_id:
        raise ValidationError({"tarea": ["La tarea debe pertenecer al proyecto del registro."]})
    if registro.tarea.estado == EstadoTarea.CANCELADA:
        raise ValidationError(
            {"tarea": ["No se puede registrar ejecución sobre una tarea cancelada."]}
        )


def _suma_horas_aprobadas_tarea(tarea):
    return (
        tarea.registros_ejecucion.filter(
            activo=True, estado_aprobacion=EstadoAprobacion.APROBADO
        ).aggregate(total=Sum("horas"))["total"]
        or CERO
    )


def recalcular_tarea(registro):
    """`Tarea.horas_ejecutadas` = suma de sus registros `APROBADO`. Se
    invoca después de aprobar, rechazar o reabrir, dentro de la misma
    transacción."""
    if registro.tarea_id is None:
        return
    total = _suma_horas_aprobadas_tarea(registro.tarea)
    Tarea.objects.filter(pk=registro.tarea_id).update(horas_ejecutadas=total)


def _validar_no_autoaprobacion(registro, usuario):
    if registro.registrado_por_id == usuario.id and "ADMIN" not in codigos_roles_de(usuario):
        raise PermissionDenied("No puede aprobar ni rechazar un registro que usted mismo registró.")


@transaction.atomic
def enviar(registro, usuario):
    if registro.estado_aprobacion not in (EstadoAprobacion.BORRADOR, EstadoAprobacion.RECHAZADO):
        raise ErrorConflicto("Solo se puede enviar un registro en borrador o rechazado.")

    estado_anterior = registro.estado_aprobacion
    registro.estado_aprobacion = EstadoAprobacion.ENVIADO
    registro.motivo_rechazo = ""
    registro.save(update_fields=["estado_aprobacion", "motivo_rechazo", "actualizado_en"])
    registrar_evento(
        tipo_evento=TipoEvento.CAMBIO_ESTADO,
        entidad="RegistroEjecucion",
        entidad_id=registro.id,
        descripcion=f"Registro de {registro.recurso.nombre} enviado a aprobación.",
        proyecto=registro.proyecto,
        antes={"estado_aprobacion": estado_anterior},
        despues={"estado_aprobacion": EstadoAprobacion.ENVIADO},
        usuario=usuario,
    )
    return registro


@transaction.atomic
def aprobar(registro, usuario):
    _validar_no_autoaprobacion(registro, usuario)
    if registro.estado_aprobacion != EstadoAprobacion.ENVIADO:
        raise ErrorConflicto("Solo se puede aprobar un registro enviado.")

    registro.estado_aprobacion = EstadoAprobacion.APROBADO
    registro.aprobado_por = usuario
    registro.aprobado_en = timezone.now()
    registro.save(
        update_fields=["estado_aprobacion", "aprobado_por", "aprobado_en", "actualizado_en"]
    )
    recalcular_tarea(registro)
    registrar_evento(
        tipo_evento=TipoEvento.APROBACION,
        entidad="RegistroEjecucion",
        entidad_id=registro.id,
        descripcion=f"Registro de {registro.recurso.nombre} aprobado.",
        proyecto=registro.proyecto,
        antes={"estado_aprobacion": EstadoAprobacion.ENVIADO},
        despues={"estado_aprobacion": EstadoAprobacion.APROBADO},
        usuario=usuario,
    )
    return registro


@transaction.atomic
def rechazar(registro, motivo, usuario):
    _validar_no_autoaprobacion(registro, usuario)
    if not motivo:
        raise ValidationError({"motivo_rechazo": ["Debe indicar el motivo del rechazo."]})
    if registro.estado_aprobacion != EstadoAprobacion.ENVIADO:
        raise ErrorConflicto("Solo se puede rechazar un registro enviado.")

    registro.estado_aprobacion = EstadoAprobacion.RECHAZADO
    registro.motivo_rechazo = motivo
    registro.save(
        update_fields=["estado_aprobacion", "motivo_rechazo", "actualizado_en"]
    )
    registrar_evento(
        tipo_evento=TipoEvento.RECHAZO,
        entidad="RegistroEjecucion",
        entidad_id=registro.id,
        descripcion=f"Registro de {registro.recurso.nombre} rechazado: {motivo}",
        proyecto=registro.proyecto,
        antes={"estado_aprobacion": EstadoAprobacion.ENVIADO},
        despues={"estado_aprobacion": EstadoAprobacion.RECHAZADO, "motivo_rechazo": motivo},
        usuario=usuario,
    )
    return registro


@transaction.atomic
def reabrir(registro, usuario):
    if registro.estado_aprobacion != EstadoAprobacion.APROBADO:
        raise ErrorConflicto("Solo se puede reabrir un registro aprobado.")

    registro.estado_aprobacion = EstadoAprobacion.ENVIADO
    registro.aprobado_por = None
    registro.aprobado_en = None
    registro.save(
        update_fields=["estado_aprobacion", "aprobado_por", "aprobado_en", "actualizado_en"]
    )
    recalcular_tarea(registro)
    registrar_evento(
        tipo_evento=TipoEvento.CAMBIO_ESTADO,
        entidad="RegistroEjecucion",
        entidad_id=registro.id,
        descripcion=f"Registro de {registro.recurso.nombre} reabierto para corrección.",
        proyecto=registro.proyecto,
        antes={"estado_aprobacion": EstadoAprobacion.APROBADO},
        despues={"estado_aprobacion": EstadoAprobacion.ENVIADO},
        usuario=usuario,
    )
    return registro


def carga_lote(lista_datos, contexto):
    """Procesa cada elemento de `lista_datos` de forma independiente contra
    `RegistroEjecucionSerializer`, en su propio `transaction.atomic()`
    (savepoint): un error en uno no afecta a los demás. Devuelve
    `(creados, errores)` con `errores` como `[{indice, detalle}]`."""
    from .serializers import RegistroEjecucionSerializer

    creados = []
    errores = []
    for indice, datos in enumerate(lista_datos):
        try:
            with transaction.atomic():
                serializer = RegistroEjecucionSerializer(data=datos, context=contexto)
                serializer.is_valid(raise_exception=True)
                creados.append(serializer.save())
        except Exception as exc:  # noqa: BLE001 - se reporta tal cual, no se interrumpe el lote
            errores.append({"indice": indice, "detalle": getattr(exc, "detail", str(exc))})
    return creados, errores


# --- Gasto ejecutado (mismo ciclo de aprobación, sin autor ni autoaprobación
# porque `GastoEjecutado` no tiene un campo `registrado_por`) -----------------


def validar_rubro(gasto):
    if gasto.rubro.proyecto_id != gasto.proyecto_id:
        raise ValidationError({"rubro": ["El rubro debe pertenecer al proyecto del gasto."]})


def _suma_gastos_aprobados_rubro(rubro):
    return (
        rubro.gastos_ejecutados.filter(
            activo=True, estado_aprobacion=EstadoAprobacion.APROBADO
        ).aggregate(total=Sum("monto"))["total"]
        or CERO
    )


def recalcular_rubro(gasto):
    from apps.proyectos.models import RubroPresupuesto

    total = _suma_gastos_aprobados_rubro(gasto.rubro)
    RubroPresupuesto.objects.filter(pk=gasto.rubro_id).update(monto_ejecutado=total)


@transaction.atomic
def enviar_gasto(gasto, usuario):
    if gasto.estado_aprobacion not in (EstadoAprobacion.BORRADOR, EstadoAprobacion.RECHAZADO):
        raise ErrorConflicto("Solo se puede enviar un gasto en borrador o rechazado.")
    estado_anterior = gasto.estado_aprobacion
    gasto.estado_aprobacion = EstadoAprobacion.ENVIADO
    gasto.save(update_fields=["estado_aprobacion", "actualizado_en"])
    registrar_evento(
        tipo_evento=TipoEvento.CAMBIO_ESTADO,
        entidad="GastoEjecutado",
        entidad_id=gasto.id,
        descripcion=f"Gasto de {gasto.rubro.descripcion} enviado a aprobación.",
        proyecto=gasto.proyecto,
        antes={"estado_aprobacion": estado_anterior},
        despues={"estado_aprobacion": EstadoAprobacion.ENVIADO},
        usuario=usuario,
    )
    return gasto


@transaction.atomic
def aprobar_gasto(gasto, usuario):
    if gasto.estado_aprobacion != EstadoAprobacion.ENVIADO:
        raise ErrorConflicto("Solo se puede aprobar un gasto enviado.")
    gasto.estado_aprobacion = EstadoAprobacion.APROBADO
    gasto.aprobado_por = usuario
    gasto.aprobado_en = timezone.now()
    gasto.save(update_fields=["estado_aprobacion", "aprobado_por", "aprobado_en", "actualizado_en"])
    recalcular_rubro(gasto)
    registrar_evento(
        tipo_evento=TipoEvento.APROBACION,
        entidad="GastoEjecutado",
        entidad_id=gasto.id,
        descripcion=f"Gasto de {gasto.rubro.descripcion} aprobado.",
        proyecto=gasto.proyecto,
        antes={"estado_aprobacion": EstadoAprobacion.ENVIADO},
        despues={"estado_aprobacion": EstadoAprobacion.APROBADO},
        usuario=usuario,
    )
    return gasto


@transaction.atomic
def rechazar_gasto(gasto, motivo, usuario):
    if not motivo:
        raise ValidationError({"motivo_rechazo": ["Debe indicar el motivo del rechazo."]})
    if gasto.estado_aprobacion != EstadoAprobacion.ENVIADO:
        raise ErrorConflicto("Solo se puede rechazar un gasto enviado.")
    gasto.estado_aprobacion = EstadoAprobacion.RECHAZADO
    gasto.save(update_fields=["estado_aprobacion", "actualizado_en"])
    registrar_evento(
        tipo_evento=TipoEvento.RECHAZO,
        entidad="GastoEjecutado",
        entidad_id=gasto.id,
        descripcion=f"Gasto de {gasto.rubro.descripcion} rechazado: {motivo}",
        proyecto=gasto.proyecto,
        antes={"estado_aprobacion": EstadoAprobacion.ENVIADO},
        despues={"estado_aprobacion": EstadoAprobacion.RECHAZADO, "motivo_rechazo": motivo},
        usuario=usuario,
    )
    return gasto


@transaction.atomic
def reabrir_gasto(gasto, usuario):
    if gasto.estado_aprobacion != EstadoAprobacion.APROBADO:
        raise ErrorConflicto("Solo se puede reabrir un gasto aprobado.")
    gasto.estado_aprobacion = EstadoAprobacion.ENVIADO
    gasto.aprobado_por = None
    gasto.aprobado_en = None
    gasto.save(update_fields=["estado_aprobacion", "aprobado_por", "aprobado_en", "actualizado_en"])
    recalcular_rubro(gasto)
    registrar_evento(
        tipo_evento=TipoEvento.CAMBIO_ESTADO,
        entidad="GastoEjecutado",
        entidad_id=gasto.id,
        descripcion=f"Gasto de {gasto.rubro.descripcion} reabierto para corrección.",
        proyecto=gasto.proyecto,
        antes={"estado_aprobacion": EstadoAprobacion.APROBADO},
        despues={"estado_aprobacion": EstadoAprobacion.ENVIADO},
        usuario=usuario,
    )
    return gasto


# --- Comparativo plan vs. ejecutado del proyecto (fase 08 §8.2.4) ------------


def comparativo_por_recurso(proyecto):
    """`[{recurso, recurso_nombre, horas_plan, horas_ejec, costo_plan,
    costo_ejec, pct_horas, pct_dinero}]` por cada recurso con asignación o
    ejecución aprobada en el proyecto."""
    from apps.recursos.models import Recurso

    planeado = {
        fila["recurso"]: fila
        for fila in proyecto.asignaciones.filter(activo=True)
        .values("recurso")
        .annotate(horas=Sum("horas_planeadas"), costo=Sum("costo_planeado"))
    }
    ejecutado = {
        fila["recurso"]: fila
        for fila in proyecto.registros_ejecucion.filter(
            activo=True, estado_aprobacion=EstadoAprobacion.APROBADO
        )
        .values("recurso")
        .annotate(horas=Sum("horas"), costo=Sum("costo"))
    }
    ids_recursos = set(planeado) | set(ejecutado)
    nombres = dict(Recurso.objects.filter(pk__in=ids_recursos).values_list("id", "nombre"))

    resultado = []
    for recurso_id in ids_recursos:
        horas_plan = planeado.get(recurso_id, {}).get("horas") or CERO
        costo_plan = planeado.get(recurso_id, {}).get("costo") or CERO
        horas_ejec = ejecutado.get(recurso_id, {}).get("horas") or CERO
        costo_ejec = ejecutado.get(recurso_id, {}).get("costo") or CERO
        pct_horas = division_segura(horas_ejec, horas_plan)
        pct_dinero = division_segura(costo_ejec, costo_plan)
        resultado.append(
            {
                "recurso": str(recurso_id),
                "recurso_nombre": nombres.get(recurso_id, ""),
                "horas_plan": horas_plan,
                "horas_ejec": horas_ejec,
                "costo_plan": costo_plan,
                "costo_ejec": costo_ejec,
                "pct_horas": float(pct_horas) * 100 if pct_horas is not None else None,
                "pct_dinero": float(pct_dinero) * 100 if pct_dinero is not None else None,
            }
        )
    return sorted(resultado, key=lambda fila: fila["recurso_nombre"])


# --- Importación de horas desde Jira/Tempo (fase 12) -------------------------


def _resolver_recurso_por_worklog(cliente, worklog, resumen):
    """Devuelve `(recurso, info_jira)`: `recurso` es `None` si no hubo forma
    de encontrarlo, pero `info_jira` (`{"correo", "nombre"}`, cuando Jira
    los pudo resolver) siempre se devuelve para que el omitido sea
    identificable por una persona, no solo por un id de worklog.

    Primero intenta por correo (`Recurso.email`); la mayoría de las cuentas
    de Jira no expone el correo por la API (depende de la visibilidad de
    cuenta de cada persona en Jira, no hay forma de forzarlo desde acá), así
    que si no hay correo o no coincide con ningún `Recurso` se cae a
    `Recurso.jira_account_id`, el mapeo manual que el admin deja en
    `/admin/integraciones` para esos casos."""
    account_id = worklog["author"]["accountId"]
    try:
        info_jira = cliente.resolver_correo_usuario(account_id)
    except Exception as exc:  # noqa: BLE001 - se reporta, no se interrumpe el lote
        resumen["errores"].append(
            {"motivo": f"no se pudo resolver el usuario {account_id}", "detalle": str(exc)}
        )
        return None, None

    from apps.recursos.models import Recurso

    correo = info_jira.get("correo") if info_jira else None
    if correo:
        recurso = Recurso.objects.filter(email__iexact=correo).first()
        if recurso is not None:
            return recurso, info_jira

    return Recurso.objects.filter(jira_account_id=account_id).first(), info_jira


def personas_jira_sin_mapear(desde, hasta):
    """Cuentas de Jira con worklogs entre `desde` y `hasta` que no resuelven
    a ningún `Recurso` (ni por correo ni por `jira_account_id` ya mapeado),
    para que `/admin/integraciones` las liste y el admin las asocie a mano
    una sola vez (fase 12, adenda: la mayoría de las cuentas de Jira no
    expone su correo por la API)."""
    from apps.recursos.models import Recurso

    from .integraciones.jira_tempo import ClienteJiraTempo, ErrorIntegracionJira

    cliente = ClienteJiraTempo()
    try:
        worklogs = cliente.obtener_worklogs(desde, hasta)
    except ErrorIntegracionJira:
        return []

    conteo_por_cuenta = {}
    for worklog in worklogs:
        account_id = worklog["author"]["accountId"]
        conteo_por_cuenta[account_id] = conteo_por_cuenta.get(account_id, 0) + 1

    mapeadas = set(
        Recurso.objects.filter(jira_account_id__in=conteo_por_cuenta).values_list(
            "jira_account_id", flat=True
        )
    )

    resultado = []
    for account_id, cantidad in conteo_por_cuenta.items():
        if account_id in mapeadas:
            continue
        try:
            info_jira = cliente.resolver_correo_usuario(account_id)
        except Exception:  # noqa: BLE001 - una cuenta rara no debe tumbar el listado
            info_jira = None
        correo = info_jira.get("correo") if info_jira else None
        if correo and Recurso.objects.filter(email__iexact=correo).exists():
            continue
        resultado.append(
            {
                "jira_account_id": account_id,
                "nombre": (info_jira.get("nombre") if info_jira else None) or account_id,
                "worklogs": cantidad,
            }
        )
    return sorted(resultado, key=lambda fila: fila["nombre"])


@transaction.atomic
def importar_horas_jira(desde, hasta, *, dry_run=False, auto_aprobar=None):
    """Trae los worklogs de Tempo entre `desde` y `hasta` (fechas) y los
    deja como `RegistroEjecucion` con `origen=JIRA` (docs/modelo-datos.md §6
    y docs/plan/fase-12-integracion-jira.md). Nunca llama a la red fuera de
    `ClienteJiraTempo`, para que los tests puedan mockearlo por completo.
    `auto_aprobar`: si se indica explícitamente (True/False), decide la
    aprobación solo para esta corrida, sin tocar el interruptor global; si
    se omite (`None`, el caso del comando de gestión), se usa
    `ConfiguracionImportacionJira.auto_aprobar_importados`.
    Devuelve `{creados, actualizados, detalle: [...], omitidos: [...],
    errores: [...]}`; `detalle` trae una fila por cada registro creado o
    actualizado (`fecha`, `recurso_nombre`, `proyecto_codigo`,
    `proyecto_nombre`, `horas`, `accion`), para mostrarla en una tabla."""
    from apps.proyectos.models import Proyecto

    from .integraciones.jira_tempo import ClienteJiraTempo, ErrorIntegracionJira

    resumen = {"creados": 0, "actualizados": 0, "detalle": [], "omitidos": [], "errores": []}
    cliente = ClienteJiraTempo()

    try:
        worklogs = cliente.obtener_worklogs(desde, hasta)
    except ErrorIntegracionJira as exc:
        resumen["errores"].append(
            {"motivo": "no se pudieron obtener los worklogs", "detalle": str(exc)}
        )
        return resumen
    if not worklogs:
        return resumen

    issue_ids = {worklog["issue"]["id"] for worklog in worklogs}
    try:
        claves_por_issue = cliente.resolver_claves_issue(issue_ids)
    except ErrorIntegracionJira as exc:
        resumen["errores"].append(
            {"motivo": "no se pudieron resolver las claves de los issues", "detalle": str(exc)}
        )
        return resumen

    if auto_aprobar is None:
        auto_aprobar = ConfiguracionImportacionJira.obtener().auto_aprobar_importados
    estado_inicial = EstadoAprobacion.APROBADO if auto_aprobar else EstadoAprobacion.ENVIADO
    proyectos_afectados = {}

    grupos = {}
    for worklog in worklogs:
        id_externo = str(worklog["tempoWorklogId"])
        issue_id = str(worklog["issue"]["id"])
        clave_issue = claves_por_issue.get(issue_id)
        if not clave_issue:
            resumen["omitidos"].append(
                {"id_externo": id_externo, "motivo": "no se pudo resolver la clave del issue"}
            )
            continue

        clave_proyecto = clave_issue.rsplit("-", 1)[0]
        proyecto = Proyecto.objects.filter(clave_jira=clave_proyecto).first()
        if proyecto is None:
            resumen["omitidos"].append(
                {
                    "id_externo": id_externo,
                    "motivo": f"proyecto de Jira «{clave_proyecto}» no está mapeado",
                }
            )
            continue

        recurso, info_jira = _resolver_recurso_por_worklog(cliente, worklog, resumen)
        if recurso is None:
            if info_jira and info_jira.get("correo"):
                quien = f"{info_jira.get('nombre') or ''} <{info_jira['correo']}>".strip()
                motivo = f"no hay un recurso con el correo de «{quien}»"
            elif info_jira and info_jira.get("nombre"):
                motivo = f"«{info_jira['nombre']}» no tiene correo visible en Jira"
            else:
                motivo = "no se pudo identificar a la persona en Jira"
            resumen["omitidos"].append({"id_externo": id_externo, "motivo": motivo})
            continue

        tarea = Tarea.objects.filter(clave_jira=clave_issue).first()
        clave_grupo = (recurso.id, proyecto.id, tarea.id if tarea else None, worklog["startDate"])
        grupo = grupos.setdefault(
            clave_grupo,
            {
                "recurso": recurso,
                "proyecto": proyecto,
                "tarea": tarea,
                "fecha": worklog["startDate"],
                "ids_externos": [],
                "horas": CERO,
                "descripciones": [],
            },
        )
        grupo["ids_externos"].append(id_externo)
        grupo["horas"] += Decimal(str(worklog["timeSpentSeconds"])) / Decimal(3600)
        descripcion = worklog.get("description") or ""
        if descripcion:
            grupo["descripciones"].append(descripcion)

    # Varios worklogs de Jira pueden caer el mismo día en la misma tarea (p.
    # ej. una entrada en la mañana y otra en la tarde): acá se agrupan y
    # suman en un solo `RegistroEjecucion`, porque el modelo guarda un
    # registro por día/tarea/recurso, no uno por worklog. El `id_externo`
    # del registro queda como la lista ordenada de los worklogs que lo
    # componen, así que una corrida posterior que vea exactamente el mismo
    # grupo lo reconoce como "existente" por sus datos (recurso/proyecto/
    # tarea/fecha), no por ese id_externo, y recalcula las horas desde cero
    # en vez de sumarlas de nuevo (evita contar doble si se reimporta).
    for grupo in grupos.values():
        recurso = grupo["recurso"]
        proyecto = grupo["proyecto"]
        tarea = grupo["tarea"]
        ids_externos = sorted(grupo["ids_externos"], key=int)
        id_externo = ",".join(ids_externos)

        es_creacion = True
        try:
            with transaction.atomic():
                existente = RegistroEjecucion.objects.filter(
                    recurso=recurso,
                    proyecto=proyecto,
                    tarea=tarea,
                    periodicidad=Periodicidad.DIARIA,
                    periodo_inicio=grupo["fecha"],
                ).first()
                if existente is not None and existente.origen != OrigenRegistro.JIRA:
                    raise ValidationError(
                        {
                            "periodo_inicio": [
                                "Ya existe un registro de otro origen para este recurso, "
                                "proyecto, tarea y día."
                            ]
                        }
                    )
                if (
                    existente is not None
                    and existente.estado_aprobacion == EstadoAprobacion.APROBADO
                ):
                    resumen["omitidos"].append(
                        {"id_externo": id_externo, "motivo": "ya aprobado, no se modifica"}
                    )
                    continue

                es_creacion = existente is None
                registro = existente or RegistroEjecucion(origen=OrigenRegistro.JIRA)
                # `objects` incluye los borrados lógicos: si el registro del día había
                # sido eliminado, se reactiva en vez de quedar "actualizado" e invisible.
                registro.activo = True
                registro.id_externo = id_externo
                registro.proyecto = proyecto
                registro.tarea = tarea
                registro.recurso = recurso
                registro.periodicidad = Periodicidad.DIARIA
                registro.periodo_inicio = datetime.date.fromisoformat(grupo["fecha"])
                registro.periodo_fin = registro.periodo_inicio
                registro.horas = grupo["horas"]
                registro.descripcion = "; ".join(grupo["descripciones"])
                if es_creacion:
                    registro.estado_aprobacion = estado_inicial
                    if estado_inicial == EstadoAprobacion.APROBADO:
                        registro.aprobado_en = timezone.now()
                else:
                    registro.estado_aprobacion = EstadoAprobacion.ENVIADO
                    registro.motivo_rechazo = ""

                preparar_registro(registro)
                validar_rango_proyecto(registro)
                validar_tarea(registro)
                validar_solapamiento(registro)
                registro.save()
                if registro.estado_aprobacion == EstadoAprobacion.APROBADO:
                    recalcular_tarea(registro)
        except Exception as exc:  # noqa: BLE001 - se reporta, no se interrumpe el lote
            logger.exception("Error guardando RegistroEjecucion de Jira id_externo=%s", id_externo)
            resumen["errores"].append(
                {
                    "id_externo": id_externo,
                    "motivo": "no se pudo guardar el registro",
                    "detalle": _detalle_legible(exc),
                }
            )
            continue

        if es_creacion:
            resumen["creados"] += 1
        else:
            resumen["actualizados"] += 1
        resumen["detalle"].append(
            {
                "fecha": registro.periodo_inicio.isoformat(),
                "recurso_nombre": recurso.nombre,
                "proyecto_codigo": proyecto.codigo,
                "proyecto_nombre": proyecto.nombre,
                "horas": registro.horas,
                "accion": "creado" if es_creacion else "actualizado",
            }
        )
        proyectos_afectados[proyecto.id] = proyecto

    resumen_bitacora = {
        "creados": resumen["creados"],
        "actualizados": resumen["actualizados"],
        "omitidos": len(resumen["omitidos"]),
        "errores": len(resumen["errores"]),
    }
    for proyecto in proyectos_afectados.values():
        registrar_evento(
            tipo_evento=TipoEvento.IMPORTACION,
            entidad="Proyecto",
            entidad_id=proyecto.id,
            descripcion=(
                f"Importación de horas desde Jira/Tempo para {proyecto.codigo} "
                f"({desde} a {hasta})."
            ),
            proyecto=proyecto,
            despues=resumen_bitacora,
        )

    if dry_run:
        transaction.set_rollback(True)
    return resumen


def comparativo_por_mes(proyecto):
    """Igual que `comparativo_por_recurso`, agregado por mes calendario.
    Lo planeado se prorratea por intersección de días calendario con cada
    asignación (misma convención que `apps.recursos.services.carga_recurso`);
    lo ejecutado se asigna completo al mes de `periodo_inicio` del registro
    (un `SEMANAL` que cruza fin de mes no se fracciona: es una simplificación
    documentada, no una fórmula de §10)."""
    asignaciones = list(proyecto.asignaciones.filter(activo=True))
    registros = list(
        proyecto.registros_ejecucion.filter(
            activo=True, estado_aprobacion=EstadoAprobacion.APROBADO
        )
    )
    fechas = [a.fecha_desde for a in asignaciones] + [a.fecha_hasta for a in asignaciones]
    fechas += [r.periodo_inicio for r in registros] + [r.periodo_fin for r in registros]
    if not fechas:
        return []

    resultado = []
    for anio, mes in meses_entre(min(fechas), max(fechas)):
        horas_plan = CERO
        costo_plan = CERO
        for asignacion in asignaciones:
            horas_plan += prorratear_por_mes(
                asignacion.fecha_desde,
                asignacion.fecha_hasta,
                asignacion.horas_planeadas,
                anio,
                mes,
            )
            costo_plan += prorratear_por_mes(
                asignacion.fecha_desde,
                asignacion.fecha_hasta,
                asignacion.costo_planeado,
                anio,
                mes,
            )

        horas_ejec = CERO
        costo_ejec = CERO
        for registro in registros:
            if registro.periodo_inicio.year == anio and registro.periodo_inicio.month == mes:
                horas_ejec += registro.horas
                costo_ejec += registro.costo

        pct_horas = division_segura(horas_ejec, horas_plan)
        pct_dinero = division_segura(costo_ejec, costo_plan)
        resultado.append(
            {
                "anio": anio,
                "mes": mes,
                "horas_plan": horas_plan,
                "horas_ejec": horas_ejec,
                "costo_plan": costo_plan,
                "costo_ejec": costo_ejec,
                "pct_horas": float(pct_horas) * 100 if pct_horas is not None else None,
                "pct_dinero": float(pct_dinero) * 100 if pct_dinero is not None else None,
            }
        )
    return resultado
