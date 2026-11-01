import logging
import re
import uuid

from django.db import IntegrityError
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("apps.core.exceptions")


class ErrorApi(drf_exceptions.APIException):
    codigo = "ERROR_INTERNO"

    def __init__(self, detail=None, codigo=None):
        super().__init__(detail)
        if codigo is not None:
            self.codigo = codigo


class ErrorReglaNegocio(ErrorApi):
    status_code = 422
    codigo = "REGLA_NEGOCIO"
    default_detail = "No se cumple una regla de negocio."


class ErrorConflicto(ErrorApi):
    status_code = 409
    codigo = "CONFLICTO"
    default_detail = "La operación entra en conflicto con el estado actual del recurso."


class ErrorArchivo(ErrorApi):
    status_code = 413
    codigo = "ARCHIVO_GRANDE"
    default_detail = "El archivo supera el tamaño máximo permitido."


STATUS_A_CODIGO = {
    400: "VALIDACION",
    401: "NO_AUTENTICADO",
    403: "SIN_PERMISO",
    404: "NO_ENCONTRADO",
    405: "NO_ENCONTRADO",
    409: "CONFLICTO",
    413: "ARCHIVO_GRANDE",
    422: "REGLA_NEGOCIO",
    429: "DEMASIADAS_PETICIONES",
}

MENSAJES_POR_CODIGO = {
    "VALIDACION": "Los datos enviados no son válidos.",
    "NO_AUTENTICADO": "Debe iniciar sesión para continuar.",
    "SIN_PERMISO": "No tiene permiso para realizar esta acción.",
    "NO_ENCONTRADO": "El recurso solicitado no existe.",
    "CONFLICTO": "La operación entra en conflicto con el estado actual del recurso.",
    "ARCHIVO_GRANDE": "El archivo supera el tamaño máximo permitido.",
    "REGLA_NEGOCIO": "No se cumple una regla de negocio.",
    "DEMASIADAS_PETICIONES": "Demasiadas peticiones; intente de nuevo más tarde.",
    "ERROR_INTERNO": "Ocurrió un error interno. Contacte al administrador.",
}

# Nombres de los constraints definidos en la fase 01 (ver docs/modelo-datos.md §11),
# traducidos a un mensaje legible. Un constraint que no esté aquí cae al genérico.
MENSAJES_CONSTRAINT = {
    "proyecto_codigo_unico": "Ya existe un proyecto con ese código.",
    "proyecto_fin_despues_de_inicio": (
        "La fecha de fin plan debe ser igual o posterior a la de inicio plan."
    ),
    "faseproyecto_orden_unico": "Ya existe una fase con ese orden en el proyecto.",
    "tarifarecurso_vigencia_unica": "Ya existe una tarifa vigente desde esa fecha para el recurso.",
    "asignacionrecurso_unica": "Ya existe una asignación para ese recurso, fase y fecha de inicio.",
    "asignacionrecurso_fin_despues_de_inicio": (
        "La fecha hasta debe ser igual o posterior a la fecha desde."
    ),
    "tarea_codigo_unico": "Ya existe una tarea con ese código en el proyecto.",
    "dependenciatarea_par_unico": "Ya existe esa dependencia entre las dos tareas.",
    "dependenciatarea_no_autodependencia": "Una tarea no puede depender de sí misma.",
    "registroejecucion_unico": (
        "Ya existe un registro de ejecución para ese recurso, proyecto, tarea y periodo."
    ),
    "registroejecucion_horas_positivas": "Las horas deben ser mayores que cero.",
    "registroejecucion_fin_despues_de_inicio": (
        "El fin del periodo debe ser igual o posterior al inicio."
    ),
    "seguimiento_unico": "Ya existe un seguimiento para ese proyecto, periodicidad y periodo.",
    "rolmeta_codigo_unico": "Ya existe un rol con ese código.",
    "area_codigo_unico": "Ya existe un área con ese código.",
    "portafolio_codigo_unico": "Ya existe un portafolio con ese código.",
    "perfilrecurso_codigo_unico": "Ya existe un perfil de recurso con ese código.",
}

MENSAJE_CONSTRAINT_GENERICO = "El registro no cumple una restricción de la base de datos."

_PATRON_NOMBRE_CONSTRAINT = re.compile(r'"([a-zA-Z0-9_]+)"')


def _traducir_integrity_error(exc):
    coincidencia = _PATRON_NOMBRE_CONSTRAINT.search(str(exc))
    nombre = coincidencia.group(1) if coincidencia else None
    return MENSAJES_CONSTRAINT.get(nombre, MENSAJE_CONSTRAINT_GENERICO)


def _sobre_error(codigo, mensaje, detalles, traza_id):
    return {
        "error": {
            "codigo": codigo,
            "mensaje": mensaje,
            "detalles": detalles,
            "traza_id": traza_id,
        }
    }


def _usuario_de(context):
    request = context.get("request") if context else None
    usuario = getattr(request, "user", None)
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        return "anonimo"
    return usuario.email


def manejador_excepciones(exc, context):
    """Exception handler único: toda respuesta de error usa el sobre de
    docs/api-contrato.md §9, incluidas ValidationError de DRF e IntegrityError
    de la base de datos (que DRF no maneja por defecto)."""
    traza_id = uuid.uuid4().hex[:12]

    if isinstance(exc, IntegrityError):
        codigo = "CONFLICTO"
        mensaje = _traducir_integrity_error(exc)
        detalles = None
        status_code = 409
    else:
        respuesta_drf = drf_exception_handler(exc, context)
        if respuesta_drf is None:
            codigo = "ERROR_INTERNO"
            mensaje = MENSAJES_POR_CODIGO[codigo]
            detalles = None
            status_code = 500
        else:
            status_code = respuesta_drf.status_code
            codigo = getattr(exc, "codigo", None) or STATUS_A_CODIGO.get(
                status_code, "ERROR_INTERNO"
            )
            detalle = getattr(exc, "detail", respuesta_drf.data)
            if isinstance(detalle, (list, dict)):
                detalles = detalle
                mensaje = MENSAJES_POR_CODIGO.get(codigo, "No se pudo completar la operación.")
            else:
                detalles = None
                mensaje = str(detalle)

    logger.error(
        "error %s traza_id=%s usuario=%s: %s",
        codigo,
        traza_id,
        _usuario_de(context),
        exc,
        exc_info=True,
    )

    return Response(_sobre_error(codigo, mensaje, detalles, traza_id), status=status_code)
