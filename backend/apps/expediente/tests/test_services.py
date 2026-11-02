import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.choices import CategoriaDocumento, EstadoAprobacion, TipoEvento
from apps.core.exceptions import ErrorConflicto
from apps.ejecucion.tests.factories import RegistroEjecucionFactory
from apps.expediente.models import EntradaBitacora
from apps.expediente.services import (
    armar_expediente,
    calcular_hash_sha256,
    guardar_documento,
    nueva_version,
    sanear_nombre_original,
)
from apps.expediente.tests.factories import DocumentoExpedienteFactory
from apps.proyectos.tests.factories import ProyectoFactory
from apps.seguimiento.tests.factories import SeguimientoFactory

pytestmark = pytest.mark.django_db


# --- sanear_nombre_original --------------------------------------------------------


def test_sanear_nombre_quita_componentes_de_ruta():
    assert sanear_nombre_original("../../etc/passwd") == "passwd"


def test_sanear_nombre_quita_rutas_de_windows():
    assert sanear_nombre_original("C:\\Windows\\System32\\config.ini") == "config.ini"


def test_sanear_nombre_quita_caracteres_de_control():
    assert sanear_nombre_original("a\x00\x01\x1fb.txt") == "ab.txt"


def test_sanear_nombre_vacio_da_nombre_por_defecto():
    assert sanear_nombre_original("") == "archivo"


# --- calcular_hash_sha256 -----------------------------------------------------------


def test_calcular_hash_coincide_con_hashlib_directo():
    contenido = b"contenido de prueba" * 1000
    archivo = SimpleUploadedFile("x.txt", contenido)
    esperado = hashlib.sha256(contenido).hexdigest()
    assert calcular_hash_sha256(archivo) == esperado


def test_calcular_hash_deja_el_cursor_al_inicio():
    archivo = SimpleUploadedFile("x.txt", b"contenido")
    calcular_hash_sha256(archivo)
    assert archivo.read() == b"contenido"


# --- guardar_documento ---------------------------------------------------------------


def _datos_documento(proyecto, archivo, **extra):
    datos = {
        "proyecto": proyecto,
        "seguimiento": None,
        "tarea": None,
        "categoria": CategoriaDocumento.INFORME,
        "nombre": "Documento de prueba",
        "archivo": archivo,
        "descripcion": "",
    }
    datos.update(extra)
    return datos


def test_guardar_documento_sanea_el_nombre_original():
    proyecto = ProyectoFactory()
    archivo = SimpleUploadedFile("../../etc/passwd", b"contenido")

    documento = guardar_documento(_datos_documento(proyecto, archivo), None)

    assert documento.nombre_original == "passwd"
    assert "etc" not in documento.archivo.name


def test_guardar_documento_detecta_duplicado_exacto():
    proyecto = ProyectoFactory()
    archivo_1 = SimpleUploadedFile("a.txt", b"mismo contenido")
    guardar_documento(_datos_documento(proyecto, archivo_1), None)

    archivo_2 = SimpleUploadedFile("b.txt", b"mismo contenido")
    with pytest.raises(ErrorConflicto) as excinfo:
        guardar_documento(_datos_documento(proyecto, archivo_2), None)

    assert excinfo.value.status_code == 409
    assert "documento_existente" in excinfo.value.detail


def test_guardar_documento_mismo_hash_en_proyectos_distintos_no_es_duplicado():
    proyecto_1 = ProyectoFactory()
    proyecto_2 = ProyectoFactory()
    archivo_1 = SimpleUploadedFile("a.txt", b"mismo contenido")
    archivo_2 = SimpleUploadedFile("b.txt", b"mismo contenido")

    guardar_documento(_datos_documento(proyecto_1, archivo_1), None)
    documento_2 = guardar_documento(_datos_documento(proyecto_2, archivo_2), None)

    assert documento_2.id is not None


def test_guardar_documento_escribe_bitacora_de_carga():
    proyecto = ProyectoFactory()
    archivo = SimpleUploadedFile("a.txt", b"contenido")

    documento = guardar_documento(_datos_documento(proyecto, archivo), None)

    entrada = EntradaBitacora.objects.filter(
        entidad="DocumentoExpediente", entidad_id=documento.id
    ).first()
    assert entrada is not None
    assert entrada.tipo_evento == TipoEvento.CARGA_DOCUMENTO


# --- nueva_version ---------------------------------------------------------------------


def test_nueva_version_encadena_y_deja_una_sola_vigente():
    documento = DocumentoExpedienteFactory()
    archivo_v2 = SimpleUploadedFile("v2.txt", b"version 2")

    v2 = nueva_version(documento, archivo_v2, None)
    documento.refresh_from_db()

    assert v2.version == 2
    assert v2.documento_padre_id == documento.id
    assert v2.es_version_vigente is True
    assert documento.es_version_vigente is False


def test_nueva_version_tercera_version_apunta_a_la_raiz_no_a_la_segunda():
    documento = DocumentoExpedienteFactory()
    v2 = nueva_version(documento, SimpleUploadedFile("v2.txt", b"v2"), None)
    v3 = nueva_version(v2, SimpleUploadedFile("v3.txt", b"v3"), None)

    assert v3.version == 3
    assert v3.documento_padre_id == documento.id  # no v2.id

    v2.refresh_from_db()
    documento.refresh_from_db()
    assert v2.es_version_vigente is False
    assert documento.es_version_vigente is False
    assert v3.es_version_vigente is True


def test_nueva_version_escribe_bitacora():
    documento = DocumentoExpedienteFactory()
    v2 = nueva_version(documento, SimpleUploadedFile("v2.txt", b"v2"), None)

    entrada = EntradaBitacora.objects.filter(
        entidad="DocumentoExpediente", entidad_id=v2.id
    ).first()
    assert entrada is not None
    assert entrada.tipo_evento == TipoEvento.NUEVA_VERSION


# --- armar_expediente --------------------------------------------------------------------


def test_armar_expediente_agrupa_documentos_por_categoria_solo_vigentes():
    proyecto = ProyectoFactory()
    doc_informe = DocumentoExpedienteFactory(
        proyecto=proyecto, categoria=CategoriaDocumento.INFORME, nombre="Informe 1"
    )
    DocumentoExpedienteFactory(
        proyecto=proyecto, categoria=CategoriaDocumento.ACTA, nombre="Acta 1"
    )
    nueva_version(doc_informe, SimpleUploadedFile("v2.txt", b"v2"), None)

    datos = armar_expediente(proyecto)

    nombres_informe = [d.nombre for d in datos["documentos_por_categoria"].get("INFORME", [])]
    assert "Informe 1" in nombres_informe
    assert len(datos["documentos_por_categoria"]["INFORME"]) == 1  # solo la vigente (v2)
    assert "ACTA" in datos["documentos_por_categoria"]


def test_armar_expediente_totales_cuenta_solo_lo_aprobado():
    proyecto = ProyectoFactory()
    RegistroEjecucionFactory(
        proyecto=proyecto, horas=8, estado_aprobacion=EstadoAprobacion.APROBADO
    )
    RegistroEjecucionFactory(
        proyecto=proyecto, horas=4, estado_aprobacion=EstadoAprobacion.ENVIADO
    )
    SeguimientoFactory(proyecto=proyecto, estado="PUBLICADO")

    datos = armar_expediente(proyecto)

    assert datos["totales"]["horas_acumuladas"] == 8
    assert datos["totales"]["seguimientos_publicados"] == 1


def test_armar_expediente_linea_tiempo_incluye_carga_de_documentos():
    proyecto = ProyectoFactory()
    archivo = SimpleUploadedFile("a.txt", b"contenido")
    documento = guardar_documento(_datos_documento(proyecto, archivo), None)

    datos = armar_expediente(proyecto)

    tipos_evento = [e.tipo_evento for e in datos["linea_tiempo"]]
    assert TipoEvento.CARGA_DOCUMENTO in tipos_evento
    entidades_ids = [
        e.entidad_id for e in datos["linea_tiempo"] if e.tipo_evento == TipoEvento.CARGA_DOCUMENTO
    ]
    assert documento.id in entidades_ids
