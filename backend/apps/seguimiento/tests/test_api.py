import datetime

import pytest
from rest_framework.test import APIClient

from apps.core.choices import EstadoSeguimiento, Semaforo
from apps.proyectos.tests.factories import HitoFactory, ProyectoFactory
from conftest import crear_usuario_con_rol

from .factories import CompromisoSeguimientoFactory, SeguimientoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


# --- precargar -------------------------------------------------------------------


def test_precargar_via_api(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/seguimientos/precargar/",
        {"proyecto": str(proyecto.id), "periodicidad": "MENSUAL", "periodo_inicio": "2026-03-15"},
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.data["periodo_inicio"] == "2026-03-01"
    assert respuesta.data["periodo_fin"] == "2026-03-31"
    assert "tareas_vencidas" in respuesta.data


def test_precargar_sin_datos_obligatorios_da_400(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post("/api/v1/seguimientos/precargar/", {}, format="json")

    assert respuesta.status_code == 400


def test_lider_precarga_en_su_proyecto_y_recibe_403_en_uno_ajeno(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    propio = ProyectoFactory(gerente=lider)
    ajeno = ProyectoFactory()
    cliente.force_authenticate(user=lider)

    respuesta = cliente.post(
        "/api/v1/seguimientos/precargar/",
        {"proyecto": str(propio.id), "periodicidad": "MENSUAL", "periodo_inicio": "2026-03-15"},
        format="json",
    )
    assert respuesta.status_code == 200

    respuesta = cliente.post(
        "/api/v1/seguimientos/precargar/",
        {"proyecto": str(ajeno.id), "periodicidad": "MENSUAL", "periodo_inicio": "2026-03-15"},
        format="json",
    )
    assert respuesta.status_code == 403


# --- publicar ----------------------------------------------------------------------


def test_publicar_con_semaforo_distinto_sin_justificacion_da_400(roles, cliente):
    proyecto = ProyectoFactory()
    HitoFactory(proyecto=proyecto, estado="INCUMPLIDO")
    seguimiento = SeguimientoFactory(
        proyecto=proyecto, semaforo=Semaforo.VERDE, justificacion_semaforo=""
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(f"/api/v1/seguimientos/{seguimiento.id}/publicar/")

    assert respuesta.status_code == 400


def test_publicar_funciona_y_devuelve_el_seguimiento_publicado(roles, cliente):
    seguimiento = SeguimientoFactory(justificacion_semaforo="Justificación de prueba.")
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(f"/api/v1/seguimientos/{seguimiento.id}/publicar/")

    assert respuesta.status_code == 200
    assert respuesta.data["estado"] == "PUBLICADO"


# --- inmutabilidad y reabrir ---------------------------------------------------------


def test_patch_sobre_publicado_da_409(roles, cliente):
    seguimiento = SeguimientoFactory(estado=EstadoSeguimiento.PUBLICADO)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.patch(
        f"/api/v1/seguimientos/{seguimiento.id}/", {"logros": "nuevo texto"}, format="json"
    )

    assert respuesta.status_code == 409


def test_reabrir_solo_admin_no_pmo(roles, cliente):
    seguimiento = SeguimientoFactory(estado=EstadoSeguimiento.PUBLICADO)
    pmo = crear_usuario_con_rol("PMO")
    cliente.force_authenticate(user=pmo)

    respuesta = cliente.post(f"/api/v1/seguimientos/{seguimiento.id}/reabrir/")
    assert respuesta.status_code == 403

    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)
    respuesta = cliente.post(f"/api/v1/seguimientos/{seguimiento.id}/reabrir/")
    assert respuesta.status_code == 200
    assert respuesta.data["estado"] == "BORRADOR"


def test_reabierto_se_puede_editar_de_nuevo(roles, cliente):
    seguimiento = SeguimientoFactory(estado=EstadoSeguimiento.PUBLICADO)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)
    cliente.post(f"/api/v1/seguimientos/{seguimiento.id}/reabrir/")

    respuesta = cliente.patch(
        f"/api/v1/seguimientos/{seguimiento.id}/", {"logros": "corregido"}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.data["logros"] == "corregido"


# --- unicidad ----------------------------------------------------------------------


def test_unicidad_proyecto_periodicidad_periodo_inicio(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    datos = {
        "proyecto": str(proyecto.id),
        "periodicidad": "MENSUAL",
        "periodo_inicio": "2026-04-01",
        "avance_reportado": "10.00",
        "semaforo": "VERDE",
    }
    primero = cliente.post("/api/v1/seguimientos/", datos, format="json")
    assert primero.status_code == 201

    segundo = cliente.post("/api/v1/seguimientos/", datos, format="json")
    assert segundo.status_code == 400


# --- compromisos -------------------------------------------------------------------


def test_compromiso_hereda_permiso_del_proyecto_del_seguimiento(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    propio = ProyectoFactory(gerente=lider)
    ajeno = ProyectoFactory()
    seguimiento_propio = SeguimientoFactory(proyecto=propio)
    seguimiento_ajeno = SeguimientoFactory(proyecto=ajeno)
    cliente.force_authenticate(user=lider)

    datos_base = {
        "descripcion": "Entregar informe",
        "responsable": str(lider.id),
        "fecha_compromiso": "2026-05-01",
    }
    respuesta = cliente.post(
        "/api/v1/compromisos-seguimiento/",
        {**datos_base, "seguimiento": str(seguimiento_propio.id)},
        format="json",
    )
    assert respuesta.status_code == 201

    respuesta = cliente.post(
        "/api/v1/compromisos-seguimiento/",
        {**datos_base, "seguimiento": str(seguimiento_ajeno.id)},
        format="json",
    )
    assert respuesta.status_code == 403


def test_filtro_vencidos_de_compromisos(roles, cliente):
    ayer = datetime.date.today() - datetime.timedelta(days=1)
    manana = datetime.date.today() + datetime.timedelta(days=1)
    vencido = CompromisoSeguimientoFactory(fecha_compromiso=ayer, estado="ABIERTO")
    CompromisoSeguimientoFactory(fecha_compromiso=manana, estado="ABIERTO")
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get("/api/v1/compromisos-seguimiento/?vencidos=true")

    ids = {c["id"] for c in respuesta.data["results"]}
    assert str(vencido.id) in ids
    assert len(ids) == 1
