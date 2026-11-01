import pytest
from django.db import IntegrityError
from rest_framework import exceptions as drf_exceptions

from apps.core.exceptions import (
    ErrorArchivo,
    ErrorConflicto,
    ErrorReglaNegocio,
    manejador_excepciones,
)

CONTEXTO = {"request": None}


@pytest.mark.parametrize(
    ("excepcion", "status_esperado", "codigo_esperado"),
    [
        (
            drf_exceptions.ValidationError({"horas": ["Las horas deben ser mayores que cero."]}),
            400,
            "VALIDACION",
        ),
        (drf_exceptions.NotAuthenticated(), 401, "NO_AUTENTICADO"),
        (drf_exceptions.PermissionDenied(), 403, "SIN_PERMISO"),
        (drf_exceptions.NotFound(), 404, "NO_ENCONTRADO"),
        (ErrorConflicto(), 409, "CONFLICTO"),
        (ErrorArchivo(), 413, "ARCHIVO_GRANDE"),
        (ErrorReglaNegocio(), 422, "REGLA_NEGOCIO"),
    ],
)
def test_sobre_error_por_codigo(excepcion, status_esperado, codigo_esperado):
    respuesta = manejador_excepciones(excepcion, CONTEXTO)

    assert respuesta.status_code == status_esperado
    sobre = respuesta.data["error"]
    assert sobre["codigo"] == codigo_esperado
    assert sobre["mensaje"]
    assert "traza_id" in sobre and len(sobre["traza_id"]) == 12


def test_validacion_expone_detalles_por_campo():
    excepcion = drf_exceptions.ValidationError({"horas": ["Las horas deben ser mayores que cero."]})
    respuesta = manejador_excepciones(excepcion, CONTEXTO)
    assert respuesta.data["error"]["detalles"] == {
        "horas": ["Las horas deben ser mayores que cero."]
    }


def test_integrity_error_se_traduce_al_espanol():
    exc = IntegrityError('duplicate key value violates unique constraint "proyecto_codigo_unico"')
    respuesta = manejador_excepciones(exc, CONTEXTO)

    assert respuesta.status_code == 409
    sobre = respuesta.data["error"]
    assert sobre["codigo"] == "CONFLICTO"
    assert sobre["mensaje"] == "Ya existe un proyecto con ese código."
    assert "constraint" not in sobre["mensaje"].lower()


def test_integrity_error_sin_traduccion_cae_a_mensaje_generico():
    exc = IntegrityError('violates check constraint "algo_que_no_esta_mapeado"')
    respuesta = manejador_excepciones(exc, CONTEXTO)
    assert respuesta.data["error"]["mensaje"] == (
        "El registro no cumple una restricción de la base de datos."
    )


def test_excepcion_no_reconocida_cae_a_error_interno_generico():
    respuesta = manejador_excepciones(ValueError("detalle sensible que no debe salir"), CONTEXTO)

    assert respuesta.status_code == 500
    sobre = respuesta.data["error"]
    assert sobre["codigo"] == "ERROR_INTERNO"
    assert "detalle sensible" not in sobre["mensaje"]
