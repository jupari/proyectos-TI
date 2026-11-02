import pytest
from rest_framework.test import APIClient

from apps.proyectos.tests.factories import ProyectoFactory
from conftest import crear_usuario_con_rol

from .factories import AreaFactory, PerfilRecursoFactory, PortafolioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


@pytest.mark.parametrize("codigo_rol", ["ADMIN", "PMO", "LIDER", "RECURSO", "CONSULTA"])
def test_cualquier_autenticado_lista_areas(roles, cliente, codigo_rol):
    AreaFactory()
    usuario = crear_usuario_con_rol(codigo_rol)
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.get("/api/v1/areas/")

    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1


@pytest.mark.parametrize(
    ("codigo_rol", "esperado"),
    [("ADMIN", 201), ("PMO", 201), ("LIDER", 403), ("RECURSO", 403), ("CONSULTA", 403)],
)
def test_solo_admin_y_pmo_crean_area(roles, cliente, codigo_rol, esperado):
    usuario = crear_usuario_con_rol(codigo_rol)
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post(
        "/api/v1/areas/", {"codigo": "AREA-TI", "nombre": "Tecnología"}, format="json"
    )

    assert respuesta.status_code == esperado


def test_buscar_area_por_codigo_o_nombre(roles, cliente):
    AreaFactory(codigo="AREA-FIN", nombre="Finanzas")
    AreaFactory(codigo="AREA-TI", nombre="Tecnología")
    usuario = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.get("/api/v1/areas/?search=Tecnolog")

    assert respuesta.data["count"] == 1
    assert respuesta.data["results"][0]["codigo"] == "AREA-TI"


def test_desactivar_area_con_proyectos_activos_devuelve_409_con_conteo(roles, cliente):
    area = AreaFactory()
    ProyectoFactory.create_batch(2, area_solicitante=area)
    usuario = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.delete(f"/api/v1/areas/{area.id}/")

    assert respuesta.status_code == 409
    assert respuesta.data["error"]["codigo"] == "CONFLICTO"
    # DRF convierte recursivamente el `detail` de la excepción a `ErrorDetail`
    # (subclase de `str`), así que el conteo llega como texto, no como int.
    assert respuesta.data["error"]["detalles"]["referencias"]["proyectos"] == "2"
    area.refresh_from_db()
    assert area.activo is True


def test_desactivar_area_sin_uso_funciona(roles, cliente):
    area = AreaFactory()
    usuario = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.delete(f"/api/v1/areas/{area.id}/")

    assert respuesta.status_code == 204
    area.refresh_from_db()
    assert area.activo is False


def test_desactivar_perfil_recurso_en_uso_devuelve_409(roles, cliente):
    from apps.recursos.tests.factories import RecursoFactory

    perfil = PerfilRecursoFactory()
    RecursoFactory(perfil=perfil)
    usuario = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.delete(f"/api/v1/perfiles-recurso/{perfil.id}/")

    assert respuesta.status_code == 409
    assert respuesta.data["error"]["detalles"]["referencias"]["recursos"] == "1"


def test_portafolio_crud_basico(roles, cliente):
    usuario = crear_usuario_con_rol("PMO")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post(
        "/api/v1/portafolios/",
        {"codigo": "PORT-01", "nombre": "Transformación digital", "descripcion": ""},
        format="json",
    )
    assert respuesta.status_code == 201

    portafolio_id = respuesta.data["id"]
    respuesta = cliente.patch(
        f"/api/v1/portafolios/{portafolio_id}/", {"nombre": "Transformación"}, format="json"
    )
    assert respuesta.status_code == 200
    assert respuesta.data["nombre"] == "Transformación"


def test_portafolio_sin_uso_se_puede_desactivar(roles, cliente):
    portafolio = PortafolioFactory()
    usuario = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.delete(f"/api/v1/portafolios/{portafolio.id}/")

    assert respuesta.status_code == 204
