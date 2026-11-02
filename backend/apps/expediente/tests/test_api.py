
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.core.choices import EstadoSeguimiento
from apps.proyectos.tests.factories import ProyectoFactory, RubroPresupuestoFactory
from apps.recursos.tests.factories import AsignacionRecursoFactory, RecursoFactory
from conftest import crear_usuario_con_rol

from .factories import DocumentoExpedienteFactory, EntradaBitacoraFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


def _subir(cliente, proyecto, archivo, **extra):
    datos = {
        "proyecto": str(proyecto.id),
        "categoria": "INFORME",
        "nombre": "Documento de prueba",
        "archivo": archivo,
    }
    datos.update(extra)
    return cliente.post("/api/v1/documentos-expediente/", datos, format="multipart")


# --- subir documentos ----------------------------------------------------------------


def test_subir_extension_no_permitida_da_400(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    archivo = SimpleUploadedFile(
        "malware.exe", b"contenido", content_type="application/x-msdownload"
    )
    respuesta = _subir(cliente, proyecto, archivo)

    assert respuesta.status_code == 400


def test_subir_archivo_de_30mb_con_tope_25_da_413(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    contenido = b"0" * (30 * 1024 * 1024)
    archivo = SimpleUploadedFile("grande.pdf", contenido, content_type="application/pdf")
    respuesta = _subir(cliente, proyecto, archivo)

    assert respuesta.status_code == 413


def test_subir_mismo_archivo_dos_veces_da_409_con_el_existente(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta_1 = _subir(cliente, proyecto, SimpleUploadedFile("a.pdf", b"mismo contenido"))
    assert respuesta_1.status_code == 201
    id_existente = respuesta_1.data["id"]

    respuesta_2 = _subir(cliente, proyecto, SimpleUploadedFile("b.pdf", b"mismo contenido"))
    assert respuesta_2.status_code == 409
    assert respuesta_2.data["error"]["detalles"]["documento_existente"] == id_existente


def test_subir_archivo_con_nombre_de_recorrido_de_rutas_se_guarda_seguro(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)
    proyecto = ProyectoFactory()

    archivo = SimpleUploadedFile("../../etc/passwd.pdf", b"contenido")
    respuesta = _subir(cliente, proyecto, archivo)

    assert respuesta.status_code == 201
    assert respuesta.data["nombre_original"] == "passwd.pdf"
    assert "etc" not in respuesta.data["archivo"]


def test_recurso_sube_documento_solo_en_su_proyecto_asignado(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    propio = ProyectoFactory()
    ajeno = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=propio, recurso=recurso)
    cliente.force_authenticate(user=titular)

    respuesta = _subir(cliente, propio, SimpleUploadedFile("a.pdf", b"contenido propio"))
    assert respuesta.status_code == 201

    respuesta = _subir(cliente, ajeno, SimpleUploadedFile("b.pdf", b"contenido ajeno"))
    assert respuesta.status_code == 403


# --- nueva-version -----------------------------------------------------------------------


def test_nueva_version_via_api_encadena_y_deja_una_sola_vigente(roles, cliente):
    documento = DocumentoExpedienteFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        f"/api/v1/documentos-expediente/{documento.id}/nueva-version/",
        {"archivo": SimpleUploadedFile("v2.pdf", b"version 2")},
        format="multipart",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["version"] == 2
    assert respuesta.data["es_version_vigente"] is True

    original = cliente.get(f"/api/v1/documentos-expediente/{documento.id}/")
    assert original.status_code == 200
    assert original.data["es_version_vigente"] is False


# --- descarga ------------------------------------------------------------------------------


def test_recurso_no_puede_descargar_documento_de_proyecto_ajeno(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    propio = ProyectoFactory()
    ajeno = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=propio, recurso=recurso)
    DocumentoExpedienteFactory(proyecto=ajeno)
    documento_ajeno = DocumentoExpedienteFactory(proyecto=ajeno, nombre="otro")
    cliente.force_authenticate(user=titular)

    respuesta = cliente.get(f"/api/v1/documentos-expediente/{documento_ajeno.id}/descargar/")

    assert respuesta.status_code == 404


def test_descarga_devuelve_el_contenido_con_nombre_original(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)
    subida = _subir(cliente, proyecto, SimpleUploadedFile("mi-informe.pdf", b"contenido real"))
    documento_id = subida.data["id"]

    respuesta = cliente.get(f"/api/v1/documentos-expediente/{documento_id}/descargar/")

    assert respuesta.status_code == 200
    assert b"contenido real" in b"".join(respuesta.streaming_content)
    assert 'filename="mi-informe.pdf"' in respuesta["Content-Disposition"]


# --- borrado lógico (solo quien subió, para RECURSO) --------------------------------------


def test_recurso_borra_solo_lo_que_el_mismo_subio(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto, recurso=recurso)
    cliente.force_authenticate(user=titular)

    subida = _subir(cliente, proyecto, SimpleUploadedFile("mio.pdf", b"contenido propio"))
    propio_id = subida.data["id"]

    otro_titular = crear_usuario_con_rol("RECURSO")
    otro_recurso = RecursoFactory(usuario=otro_titular)
    AsignacionRecursoFactory(proyecto=proyecto, recurso=otro_recurso)
    cliente.force_authenticate(user=otro_titular)
    subida_otro = _subir(cliente, proyecto, SimpleUploadedFile("otro.pdf", b"contenido de otro"))
    ajeno_id = subida_otro.data["id"]

    cliente.force_authenticate(user=titular)
    respuesta = cliente.delete(f"/api/v1/documentos-expediente/{propio_id}/")
    assert respuesta.status_code == 204

    respuesta = cliente.delete(f"/api/v1/documentos-expediente/{ajeno_id}/")
    assert respuesta.status_code == 403


def test_pmo_no_puede_borrar_documentos(roles, cliente):
    documento = DocumentoExpedienteFactory()
    pmo = crear_usuario_con_rol("PMO")
    cliente.force_authenticate(user=pmo)

    respuesta = cliente.delete(f"/api/v1/documentos-expediente/{documento.id}/")

    assert respuesta.status_code == 403


# --- bitácora --------------------------------------------------------------------------------


def test_recurso_y_consulta_no_tienen_acceso_a_bitacora(roles, cliente):
    EntradaBitacoraFactory()
    recurso = crear_usuario_con_rol("RECURSO")
    consulta = crear_usuario_con_rol("CONSULTA")

    cliente.force_authenticate(user=recurso)
    assert cliente.get("/api/v1/bitacora/").status_code == 403

    cliente.force_authenticate(user=consulta)
    assert cliente.get("/api/v1/bitacora/").status_code == 403


def test_admin_y_pmo_ven_toda_la_bitacora(roles, cliente):
    EntradaBitacoraFactory()
    for codigo in ("ADMIN", "PMO"):
        usuario = crear_usuario_con_rol(codigo)
        cliente.force_authenticate(user=usuario)
        respuesta = cliente.get("/api/v1/bitacora/")
        assert respuesta.status_code == 200
        assert respuesta.data["count"] >= 1


def test_lider_solo_ve_bitacora_de_sus_proyectos(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    propio = ProyectoFactory(gerente=lider)
    ajeno = ProyectoFactory()
    EntradaBitacoraFactory(proyecto=propio, descripcion="evento propio")
    EntradaBitacoraFactory(proyecto=ajeno, descripcion="evento ajeno")
    cliente.force_authenticate(user=lider)

    respuesta = cliente.get("/api/v1/bitacora/")

    descripciones = {e["descripcion"] for e in respuesta.data["results"]}
    assert "evento propio" in descripciones
    assert "evento ajeno" not in descripciones


# --- expediente del proyecto y exportación ---------------------------------------------------


def test_expediente_del_proyecto(roles, cliente):
    proyecto = ProyectoFactory()
    DocumentoExpedienteFactory(proyecto=proyecto)
    RubroPresupuestoFactory(proyecto=proyecto)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(f"/api/v1/proyectos/{proyecto.id}/expediente/")

    assert respuesta.status_code == 200
    assert "documentos_por_categoria" in respuesta.data
    assert "linea_tiempo" in respuesta.data
    assert "totales" in respuesta.data
    assert respuesta.data["totales"]["documentos"] == 1


def test_exportar_expediente_devuelve_pdf(roles, cliente):
    proyecto = ProyectoFactory()
    DocumentoExpedienteFactory(proyecto=proyecto)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(f"/api/v1/proyectos/{proyecto.id}/expediente/exportar/")

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/pdf"
    assert respuesta.content[:5] == b"%PDF-"


def test_linea_tiempo_incluye_publicacion_y_carga(roles, cliente):
    proyecto = ProyectoFactory()
    from apps.seguimiento.services import publicar
    from apps.seguimiento.tests.factories import SeguimientoFactory

    seguimiento = SeguimientoFactory(
        proyecto=proyecto, estado=EstadoSeguimiento.BORRADOR, justificacion_semaforo="x"
    )
    admin = crear_usuario_con_rol("ADMIN")
    publicar(seguimiento, admin)
    cliente.force_authenticate(user=admin)
    _subir(cliente, proyecto, SimpleUploadedFile("acta.pdf", b"contenido"))

    respuesta = cliente.get(f"/api/v1/proyectos/{proyecto.id}/expediente/")

    tipos = {e["tipo_evento"] for e in respuesta.data["linea_tiempo"]}
    assert "PUBLICACION" in tipos
    assert "CARGA_DOCUMENTO" in tipos
