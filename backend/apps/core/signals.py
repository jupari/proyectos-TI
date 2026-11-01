"""Auditoría automática: quién creó/modificó cada registro y qué cambió.

Las señales se conectan explícitamente en `CoreConfig.ready()` (no se usa el
decorador `@receiver` para que la conexión quede bajo control del AppConfig,
como pide la fase).
"""

import logging

from django.db import IntegrityError, transaction
from django.db.models import FileField

from apps.core.choices import TipoEvento
from apps.core.middleware import obtener_usuario_actual
from apps.core.models import ModeloBase

logger = logging.getLogger("apps.core.signals")

# Campos que nunca entran en el diff de auditoría: son metadatos de la
# propia auditoría, no cambios de negocio.
CAMPOS_EXCLUIDOS_DIFF = {"actualizado_en", "actualizado_por_id"}

# Modelos que no generan entradas de bitácora: EntradaBitacora (evitaría
# recursión infinita) y los de token_blacklist, que además ni heredan de
# ModeloBase (quedan excluidos solo por completitud/documentación).
NOMBRES_EXCLUIDOS_BITACORA = {"EntradaBitacora", "OutstandingToken", "BlacklistedToken"}

# Resuelve el proyecto de la entrada de bitácora cuando el modelo no tiene
# un campo `proyecto` directo.
RUTA_A_PROYECTO = {
    "CompromisoSeguimiento": "seguimiento.proyecto",
    "DependenciaTarea": "tarea_origen.proyecto",
}


def _campos_auditables(modelo):
    for campo in modelo._meta.concrete_fields:
        if campo.attname in CAMPOS_EXCLUIDOS_DIFF or isinstance(campo, FileField):
            continue
        yield campo


def _estado_campos(instancia):
    return {
        campo.attname: getattr(instancia, campo.attname)
        for campo in _campos_auditables(type(instancia))
    }


def _resolver_proyecto(instancia):
    """Resuelve el proyecto de la entrada de bitácora.

    En un borrado físico en cascada, el objeto al que apunta la FK (p. ej.
    `tarea_origen` de una `DependenciaTarea`, o el propio `proyecto`) puede
    ya haber sido borrado en la misma operación: cualquier fallo al resolver
    la ruta se trata como "sin proyecto" en vez de romper el borrado.
    """
    try:
        if hasattr(instancia, "proyecto_id"):
            return instancia.proyecto
        ruta = RUTA_A_PROYECTO.get(type(instancia).__name__)
        if not ruta:
            return None
        objeto = instancia
        for paso in ruta.split("."):
            objeto = getattr(objeto, paso, None)
            if objeto is None:
                return None
        return objeto
    except Exception:
        return None


def _aplica(sender, instance):
    return isinstance(instance, ModeloBase) and sender.__name__ not in NOMBRES_EXCLUIDOS_BITACORA


def auditar_pre_save(sender, instance, raw=False, **kwargs):
    if raw or not _aplica(sender, instance):
        return

    usuario = obtener_usuario_actual()
    existente = sender.objects.filter(pk=instance.pk).first() if instance.pk else None

    if existente is None:
        instance._auditoria_creando = True
        instance._auditoria_estado_antes = None
        if usuario is not None:
            instance.creado_por = usuario
    else:
        instance._auditoria_creando = False
        instance._auditoria_estado_antes = _estado_campos(existente)

    if usuario is not None:
        instance.actualizado_por = usuario


def auditar_post_save(sender, instance, created, raw=False, **kwargs):
    if raw or not _aplica(sender, instance):
        return

    from apps.core.services import registrar_evento

    usuario = obtener_usuario_actual()
    proyecto = _resolver_proyecto(instance)
    creando = getattr(instance, "_auditoria_creando", created)

    if creando:
        registrar_evento(
            proyecto=proyecto,
            tipo_evento=TipoEvento.CREACION,
            entidad=sender.__name__,
            entidad_id=instance.pk,
            descripcion=f"Se creó {sender._meta.verbose_name} «{instance}».",
            despues=_estado_campos(instance),
            usuario=usuario,
        )
        return

    antes = getattr(instance, "_auditoria_estado_antes", None) or {}
    despues = _estado_campos(instance)
    diff_antes = {clave: valor for clave, valor in antes.items() if despues.get(clave) != valor}
    if not diff_antes:
        return
    diff_despues = {clave: despues[clave] for clave in diff_antes}

    registrar_evento(
        proyecto=proyecto,
        tipo_evento=TipoEvento.ACTUALIZACION,
        entidad=sender.__name__,
        entidad_id=instance.pk,
        descripcion=f"Se actualizó {sender._meta.verbose_name} «{instance}».",
        antes=diff_antes,
        despues=diff_despues,
        usuario=usuario,
    )


def auditar_post_delete(sender, instance, **kwargs):
    if not _aplica(sender, instance):
        return

    from apps.core.services import registrar_evento

    # No se resuelve `proyecto` aquí a propósito: un borrado físico en
    # cascada puede estar borrando, en la misma transacción, el propio
    # proyecto al que apuntaría esta entrada. Postgres difiere la
    # comprobación de FK hasta el COMMIT final de todo el `Collector.delete()`
    # de Django (usa `SET CONSTRAINTS ALL DEFERRED`), así que ninguna
    # comprobación de existencia *en este momento* es confiable: el proyecto
    # puede existir ahora y haber sido borrado, en la misma operación, para
    # cuando se confirme la transacción. `proyecto` queda `None`; la entidad
    # y su id siguen identificando qué se borró.
    try:
        with transaction.atomic():
            registrar_evento(
                proyecto=None,
                tipo_evento=TipoEvento.ACTUALIZACION,
                entidad=sender.__name__,
                entidad_id=instance.pk,
                descripcion=f"Se borró físicamente {sender._meta.verbose_name} «{instance}».",
                antes=_estado_campos(instance),
                usuario=obtener_usuario_actual(),
            )
    except IntegrityError:
        # Última red de seguridad: la auditoría de un borrado físico nunca
        # debe impedir el borrado que está observando.
        logger.warning(
            "No se pudo registrar en bitácora el borrado de %s %s", sender.__name__, instance.pk
        )
