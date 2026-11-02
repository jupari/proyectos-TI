import datetime

import pytest
from rest_framework.test import APIClient

from apps.catalogos.tests.factories import PerfilRecursoFactory
from apps.proyectos.tests.factories import ProyectoFactory
from conftest import crear_usuario_con_rol

from .factories import AsignacionRecursoFactory, RecursoFactory, TarifaRecursoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


# --- recursos ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("codigo_rol", "esperado"),
    [("ADMIN", 201), ("PMO", 201), ("LIDER", 403), ("RECURSO", 403), ("CONSULTA", 403)],
)
def test_solo_admin_y_pmo_crean_recursos(roles, cliente, codigo_rol, esperado):
    usuario = crear_usuario_con_rol(codigo_rol)
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post(
        "/api/v1/recursos/",
        {"tipo": "INTERNO", "nombre": "Nuevo recurso", "capacidad_horas_mes": "160.00"},
        format="json",
    )

    assert respuesta.status_code == esperado


def test_cualquier_autenticado_lista_recursos(roles, cliente):
    RecursoFactory()
    usuario = crear_usuario_con_rol("CONSULTA")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.get("/api/v1/recursos/")

    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1


def test_filtro_sin_asignacion(roles, cliente):
    con_asignacion = AsignacionRecursoFactory().recurso
    sin_asignacion = RecursoFactory()
    usuario = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.get("/api/v1/recursos/?sin_asignacion=true")

    ids = {r["id"] for r in respuesta.data["results"]}
    assert str(sin_asignacion.id) in ids
    assert str(con_asignacion.id) not in ids


def test_filtro_por_usuario_encuentra_el_propio_recurso(roles, cliente):
    """docs/plan/fase-08-ejecucion-ingesta.md: la pantalla "Mi registro de
    horas" necesita resolver el `Recurso` del usuario autenticado."""
    titular = crear_usuario_con_rol("RECURSO")
    mi_recurso = RecursoFactory(usuario=titular)
    RecursoFactory()  # de otro usuario, no debe aparecer
    cliente.force_authenticate(user=titular)

    respuesta = cliente.get(f"/api/v1/recursos/?usuario={titular.id}")

    ids = {r["id"] for r in respuesta.data["results"]}
    assert ids == {str(mi_recurso.id)}


# --- tarifas -------------------------------------------------------------


def test_crear_tarifa_que_solapa_la_anterior_la_cierra_sola(roles, cliente):
    recurso = RecursoFactory()
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=50_000, vigente_desde=datetime.date(2026, 1, 1)
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/tarifas-recurso/",
        {
            "recurso": str(recurso.id),
            "valor_hora": "55000.00",
            "moneda": "COP",
            "vigente_desde": "2026-06-01",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["avisos"]

    anterior = recurso.tarifas.get(valor_hora=50_000)
    assert str(anterior.vigente_hasta) == "2026-05-31"


def test_recurso_sin_tarifa_ni_perfil_da_error_accionable_al_asignar(roles, cliente):
    proyecto = ProyectoFactory()
    recurso = RecursoFactory(perfil=None)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/asignaciones/",
        {
            "proyecto": str(proyecto.id),
            "recurso": str(recurso.id),
            "rol_en_proyecto": "Analista",
            "fecha_desde": str(proyecto.fecha_inicio_plan),
            "fecha_hasta": str(proyecto.fecha_inicio_plan + datetime.timedelta(days=30)),
            "porcentaje_dedicacion": "50.00",
            "horas_planeadas": "100.00",
        },
        format="json",
    )

    assert respuesta.status_code == 422
    assert recurso.nombre in respuesta.data["error"]["mensaje"] or recurso.nombre in str(
        respuesta.data["error"]["detalles"]
    )


# --- asignaciones ----------------------------------------------------------


def test_asignacion_fuera_de_fechas_del_proyecto_se_rechaza(roles, cliente):
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 6, 30)
    )
    recurso = RecursoFactory(perfil=PerfilRecursoFactory())
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/asignaciones/",
        {
            "proyecto": str(proyecto.id),
            "recurso": str(recurso.id),
            "rol_en_proyecto": "Analista",
            "fecha_desde": "2025-12-01",
            "fecha_hasta": "2026-02-01",
            "porcentaje_dedicacion": "50.00",
            "horas_planeadas": "100.00",
        },
        format="json",
    )

    assert respuesta.status_code == 400


def test_sobreasignacion_devuelve_advertencia_y_guarda(roles, cliente):
    recurso = RecursoFactory(perfil=PerfilRecursoFactory())
    proyecto_1 = ProyectoFactory()
    proyecto_2 = ProyectoFactory()
    AsignacionRecursoFactory(
        proyecto=proyecto_1,
        recurso=recurso,
        fecha_desde=datetime.date(2026, 3, 1),
        fecha_hasta=datetime.date(2026, 3, 31),
        porcentaje_dedicacion=70,
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/asignaciones/",
        {
            "proyecto": str(proyecto_2.id),
            "recurso": str(recurso.id),
            "rol_en_proyecto": "Analista",
            "fecha_desde": "2026-03-01",
            "fecha_hasta": "2026-03-31",
            "porcentaje_dedicacion": "60.00",
            "horas_planeadas": "100.00",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["advertencias"]


def test_valor_hora_plan_se_precarga_con_la_tarifa_vigente(roles, cliente):
    proyecto = ProyectoFactory()
    recurso = RecursoFactory()
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=65_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/asignaciones/",
        {
            "proyecto": str(proyecto.id),
            "recurso": str(recurso.id),
            "rol_en_proyecto": "Analista",
            "fecha_desde": str(proyecto.fecha_inicio_plan),
            "fecha_hasta": str(proyecto.fecha_inicio_plan + datetime.timedelta(days=30)),
            "porcentaje_dedicacion": "50.00",
            "horas_planeadas": "100.00",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["valor_hora_plan"] == "65000.00"
    assert respuesta.data["costo_planeado"] == "6500000.00"


def test_lider_asigna_en_su_proyecto_y_recibe_403_en_uno_ajeno(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    propio = ProyectoFactory(gerente=lider)
    ajeno = ProyectoFactory()
    recurso = RecursoFactory(perfil=PerfilRecursoFactory())
    cliente.force_authenticate(user=lider)

    datos_base = {
        "recurso": str(recurso.id),
        "rol_en_proyecto": "Analista",
        "porcentaje_dedicacion": "50.00",
        "horas_planeadas": "100.00",
    }

    respuesta = cliente.post(
        "/api/v1/asignaciones/",
        {
            **datos_base,
            "proyecto": str(propio.id),
            "fecha_desde": str(propio.fecha_inicio_plan),
            "fecha_hasta": str(propio.fecha_inicio_plan + datetime.timedelta(days=30)),
        },
        format="json",
    )
    assert respuesta.status_code == 201

    respuesta = cliente.post(
        "/api/v1/asignaciones/",
        {
            **datos_base,
            "proyecto": str(ajeno.id),
            "fecha_desde": str(ajeno.fecha_inicio_plan),
            "fecha_hasta": str(ajeno.fecha_inicio_plan + datetime.timedelta(days=30)),
        },
        format="json",
    )
    assert respuesta.status_code == 403


# --- carga del recurso y resumen del proyecto -------------------------------


def test_carga_del_recurso_reparte_horas_entre_meses(roles, cliente):
    recurso = RecursoFactory(capacidad_horas_mes=160)
    AsignacionRecursoFactory(
        recurso=recurso,
        fecha_desde=datetime.date(2026, 2, 1),
        fecha_hasta=datetime.date(2026, 3, 31),
        horas_planeadas=590,
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(
        f"/api/v1/recursos/{recurso.id}/carga/?desde=2026-02-01&hasta=2026-03-31"
    )

    assert respuesta.status_code == 200
    assert len(respuesta.data) == 2
    assert respuesta.data[0]["mes"] == 2
    assert respuesta.data[1]["mes"] == 3


def test_resumen_de_proyecto_coincide_con_asignaciones_mas_rubros(roles, cliente):
    from apps.proyectos.tests.factories import RubroPresupuestoFactory

    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto, horas_planeadas=400, valor_hora_plan=70_000)
    RubroPresupuestoFactory(proyecto=proyecto, monto_planeado=3_000_000)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(f"/api/v1/proyectos/{proyecto.id}/resumen/")

    assert respuesta.status_code == 200
    assert respuesta.data["costo_planeado"] == 31_000_000.0
    assert respuesta.data["horas_planeadas"] == 400.0
