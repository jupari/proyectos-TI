import pytest
from rest_framework.test import APIClient

from conftest import crear_usuario_con_rol

from .factories import EntregableHitoFactory, HitoFactory, ProyectoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


def _cuerpo(hito, **extra):
    return {"proyecto": str(hito.proyecto_id), "hito": str(hito.id), "nombre": "Manual", **extra}


def test_admin_crea_entregable_y_el_hito_lo_anida(roles, cliente):
    cliente.force_authenticate(user=crear_usuario_con_rol("ADMIN"))
    hito = HitoFactory()

    respuesta = cliente.post("/api/v1/entregables-hito/", _cuerpo(hito), format="json")

    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "PENDIENTE"
    detalle = cliente.get(f"/api/v1/proyectos/{hito.proyecto_id}/hitos/").json()
    assert [e["nombre"] for e in detalle[0]["entregables"]] == ["Manual"]


def test_entregable_con_hito_de_otro_proyecto_da_400(roles, cliente):
    cliente.force_authenticate(user=crear_usuario_con_rol("ADMIN"))
    hito = HitoFactory()
    otro = ProyectoFactory()

    cuerpo = _cuerpo(hito)
    cuerpo["proyecto"] = str(otro.id)
    respuesta = cliente.post("/api/v1/entregables-hito/", cuerpo, format="json")

    assert respuesta.status_code == 400
    assert "hito" in respuesta.json()["error"]["detalles"]


def test_entregable_eliminado_no_aparece_en_el_hito(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)
    entregable = EntregableHitoFactory()

    assert cliente.delete(f"/api/v1/entregables-hito/{entregable.id}/").status_code == 204

    detalle = cliente.get(f"/api/v1/proyectos/{entregable.proyecto_id}/").json()
    assert detalle["hitos"][0]["entregables"] == []


def test_lider_gestiona_entregables_de_su_proyecto_y_no_de_uno_ajeno(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    propio = HitoFactory(proyecto=ProyectoFactory(gerente=lider))
    ajeno = HitoFactory(proyecto=ProyectoFactory())
    cliente.force_authenticate(user=lider)

    url = "/api/v1/entregables-hito/"
    assert cliente.post(url, _cuerpo(propio), format="json").status_code == 201
    assert cliente.post(url, _cuerpo(ajeno), format="json").status_code == 403


def test_recurso_puede_ver_pero_no_crear_entregables(roles, cliente):
    hito = HitoFactory()
    cliente.force_authenticate(user=crear_usuario_con_rol("RECURSO"))

    url = "/api/v1/entregables-hito/"
    assert cliente.get(url).status_code == 200
    assert cliente.post(url, _cuerpo(hito), format="json").status_code == 403
