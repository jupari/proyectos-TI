"""Reglas de negocio del expediente digital (docs/plan/fase-09-seguimiento-expediente.md
§9.2 y docs/modelo-datos.md §8)."""

import hashlib
import re

from django.db import transaction
from django.db.models import Max, Sum

from apps.core.choices import EstadoAprobacion, EstadoSeguimiento, EstadoTarea, TipoEvento
from apps.core.exceptions import ErrorConflicto
from apps.core.services import registrar_evento

from .models import DocumentoExpediente

_CARACTERES_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def sanear_nombre_original(nombre):
    """Quita cualquier componente de ruta (`../../etc/passwd` → `passwd`) y
    caracteres de control antes de guardar `nombre_original`. La ruta real
    de almacenamiento (`ruta_archivo_expediente`) ya es segura por
    construcción porque usa un `uuid`, nunca este nombre; esto protege lo
    que se muestra y se manda en `Content-Disposition` al descargar."""
    base = nombre.replace("\\", "/").rsplit("/", 1)[-1]
    base = _CARACTERES_CONTROL.sub("", base).strip()
    return base[:250] or "archivo"


def calcular_hash_sha256(archivo):
    """Lee `archivo` por bloques (nunca entero en memoria) y deja el
    cursor al inicio para que el storage pueda leerlo de nuevo al guardar."""
    hasher = hashlib.sha256()
    for bloque in archivo.chunks():
        hasher.update(bloque)
    archivo.seek(0)
    return hasher.hexdigest()


def _buscar_duplicado(proyecto, hash_sha256):
    return DocumentoExpediente.objects.filter(
        activo=True, proyecto=proyecto, hash_sha256=hash_sha256
    ).first()


@transaction.atomic
def guardar_documento(datos, usuario):
    """`datos` ya pasó por `DocumentoExpedienteSerializer` (incluida la
    validación de extensión y tamaño); aquí se resuelve el hash, el
    duplicado exacto y el saneamiento del nombre."""
    archivo = datos["archivo"]
    hash_sha256 = calcular_hash_sha256(archivo)

    duplicado = _buscar_duplicado(datos["proyecto"], hash_sha256)
    if duplicado is not None:
        raise ErrorConflicto(
            {
                "documento_existente": str(duplicado.id),
                "nombre": duplicado.nombre,
                "mensaje": [f"Ya existe un documento idéntico: «{duplicado.nombre}»."],
            }
        )

    documento = DocumentoExpediente(
        **datos,
        nombre_original=sanear_nombre_original(archivo.name),
        mime=getattr(archivo, "content_type", "") or "",
        tamano_bytes=archivo.size,
        hash_sha256=hash_sha256,
        version=1,
        es_version_vigente=True,
    )
    documento.save()

    registrar_evento(
        tipo_evento=TipoEvento.CARGA_DOCUMENTO,
        entidad="DocumentoExpediente",
        entidad_id=documento.id,
        descripcion=f"Se cargó el documento «{documento.nombre}» ({documento.categoria}).",
        proyecto=documento.proyecto,
        usuario=usuario,
    )
    return documento


def _raiz_de(documento):
    return documento.documento_padre or documento


@transaction.atomic
def nueva_version(documento_actual, archivo, usuario):
    raiz = _raiz_de(documento_actual)
    ultima_version = raiz.versiones.aggregate(maximo=Max("version"))["maximo"] or raiz.version
    ultima_version = max(ultima_version, raiz.version, documento_actual.version)

    nueva = DocumentoExpediente(
        proyecto=documento_actual.proyecto,
        seguimiento=documento_actual.seguimiento,
        tarea=documento_actual.tarea,
        categoria=documento_actual.categoria,
        nombre=documento_actual.nombre,
        archivo=archivo,
        nombre_original=sanear_nombre_original(archivo.name),
        mime=getattr(archivo, "content_type", "") or "",
        tamano_bytes=archivo.size,
        hash_sha256=calcular_hash_sha256(archivo),
        version=ultima_version + 1,
        documento_padre=raiz,
        es_version_vigente=True,
        descripcion=documento_actual.descripcion,
    )
    nueva.save()

    DocumentoExpediente.objects.filter(pk=raiz.pk).update(es_version_vigente=False)
    raiz.versiones.exclude(pk=nueva.pk).update(es_version_vigente=False)

    registrar_evento(
        tipo_evento=TipoEvento.NUEVA_VERSION,
        entidad="DocumentoExpediente",
        entidad_id=nueva.id,
        descripcion=f"Nueva versión (v{nueva.version}) de «{nueva.nombre}».",
        proyecto=nueva.proyecto,
        antes={"version_anterior": documento_actual.version},
        despues={"version_nueva": nueva.version},
        usuario=usuario,
    )
    return nueva


def armar_expediente(proyecto, pagina=1, tamano_pagina=50):
    """`{documentos_por_categoria, linea_tiempo, totales}`. La bitácora ya
    registra (vía señales y `registrar_evento`) cambios de estado,
    aprobaciones, publicaciones y cargas de documentos, así que la línea de
    tiempo es directamente `EntradaBitacora` del proyecto: no hace falta
    volver a mezclar manualmente otras fuentes."""
    documentos = proyecto.documentos_expediente.filter(
        activo=True, es_version_vigente=True
    ).order_by("categoria", "-creado_en")
    por_categoria: dict = {}
    for documento in documentos:
        por_categoria.setdefault(documento.categoria, []).append(documento)

    bitacora_qs = proyecto.bitacora.filter(activo=True).select_related("usuario").order_by(
        "-ocurrido_en"
    )
    total_eventos = bitacora_qs.count()
    inicio = (pagina - 1) * tamano_pagina
    linea_tiempo = list(bitacora_qs[inicio : inicio + tamano_pagina])

    agregado_ejecucion = proyecto.registros_ejecucion.filter(
        activo=True, estado_aprobacion=EstadoAprobacion.APROBADO
    ).aggregate(horas=Sum("horas"), costo=Sum("costo"))
    horas_acumuladas = agregado_ejecucion["horas"]
    costo_acumulado = agregado_ejecucion["costo"]

    totales = {
        "documentos": documentos.count(),
        "seguimientos_publicados": proyecto.seguimientos.filter(
            activo=True, estado=EstadoSeguimiento.PUBLICADO
        ).count(),
        "horas_acumuladas": horas_acumuladas or 0,
        "costo_acumulado": costo_acumulado or 0,
        "tareas_cerradas": proyecto.tareas.filter(
            activo=True, estado=EstadoTarea.COMPLETADA
        ).count(),
    }

    return {
        "documentos_por_categoria": por_categoria,
        "linea_tiempo": linea_tiempo,
        "total_eventos_linea_tiempo": total_eventos,
        "totales": totales,
    }
