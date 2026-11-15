import datetime
from decimal import Decimal

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.core.choices import EstadoAprobacion
from apps.ejecucion.tests.factories import RegistroEjecucionFactory
from apps.proyectos.tests.factories import ProyectoFactory, RubroPresupuestoFactory
from apps.recursos.tests.factories import AsignacionRecursoFactory
from conftest import crear_usuario_con_rol

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


@pytest.fixture(autouse=True)
def _limpiar_cache_tablero():
    cache.clear()
    yield
    cache.clear()


# --- Alcance por rol ----------------------------------------------------


def test_lider_ve_en_el_tablero_solo_sus_proyectos_y_sus_totales_cuadran(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    otro_gerente = crear_usuario_con_rol("LIDER")

    proyecto_propio = ProyectoFactory(gerente=lider)
    proyecto_ajeno = ProyectoFactory(gerente=otro_gerente)
    AsignacionRecursoFactory(proyecto=proyecto_propio, horas_planeadas=400, valor_hora_plan=70_000)
    AsignacionRecursoFactory(proyecto=proyecto_ajeno, horas_planeadas=900, valor_hora_plan=50_000)

    cliente.force_authenticate(user=lider)

    resumen = cliente.get("/api/v1/tablero/resumen/").data
    assert resumen["total_proyectos"] == 1
    assert resumen["horas_planeadas"] == Decimal("400.00")

    filas = cliente.get("/api/v1/tablero/proyectos/").data["filas"]
    assert [fila["codigo"] for fila in filas] == [proyecto_propio.codigo]


def test_recurso_sin_asignaciones_no_ve_ningun_proyecto_en_el_tablero(roles, cliente):
    ProyectoFactory()
    recurso_usuario = crear_usuario_con_rol("RECURSO")
    cliente.force_authenticate(user=recurso_usuario)

    resumen = cliente.get("/api/v1/tablero/resumen/").data
    assert resumen["total_proyectos"] == 0
    assert resumen["pct_horas"] is None


# --- /tablero/proyectos-por-periodo/ -------------------------------------


def test_proyectos_por_periodo_trae_filas_y_totales(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(
        proyecto=proyecto,
        fecha_desde=datetime.date(2026, 3, 1),
        fecha_hasta=datetime.date(2026, 3, 31),
        horas_planeadas=310,
        valor_hora_plan=50_000,
    )
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(
        "/api/v1/tablero/proyectos-por-periodo/",
        {"desde": "2026-03-01", "hasta": "2026-03-31"},
    )

    assert respuesta.status_code == 200
    assert respuesta.data["filas"] == [
        {
            "id": str(proyecto.id),
            "codigo": proyecto.codigo,
            "nombre": proyecto.nombre,
            "horas_plan": Decimal("310.00"),
            "horas_ejec": Decimal("0"),
            "pct_horas": 0.0,
        }
    ]
    assert respuesta.data["totales"]["horas_plan"] == Decimal("310.00")
    assert "calculado_en" in respuesta.data


def test_proyectos_por_periodo_sin_fechas_da_400(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get("/api/v1/tablero/proyectos-por-periodo/")

    assert respuesta.status_code == 400


def test_lider_en_proyectos_por_periodo_solo_ve_sus_proyectos(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    otro_gerente = crear_usuario_con_rol("LIDER")
    proyecto_propio = ProyectoFactory(gerente=lider)
    ProyectoFactory(gerente=otro_gerente)
    cliente.force_authenticate(user=lider)

    respuesta = cliente.get(
        "/api/v1/tablero/proyectos-por-periodo/",
        {"desde": "2026-03-01", "hasta": "2026-03-31"},
    )

    assert [fila["codigo"] for fila in respuesta.data["filas"]] == [proyecto_propio.codigo]


# --- Exportación CSV -----------------------------------------------------


def test_exportar_csv_proyectos_tiene_bom_separador_y_encabezados_en_espanol(roles, cliente):
    proyecto = ProyectoFactory(codigo="PRY-2026-900")
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get("/api/v1/tablero/exportar/?formato=csv&vista=proyectos")
    contenido = b"".join(respuesta.streaming_content).decode("utf-8")

    assert contenido.startswith("﻿")
    primera_linea = contenido.splitlines()[0].lstrip("﻿")
    assert primera_linea == (
        "Código;Nombre;Gerente;Estado;% horas;% dinero;SPI;CPI;Desviación presupuestal;Semáforo"
    )
    assert proyecto.codigo in contenido


def test_exportar_csv_respeta_los_filtros_de_proyectos(roles, cliente):
    ProyectoFactory(codigo="PRY-2026-901", estado="EJECUCION")
    ProyectoFactory(codigo="PRY-2026-902", estado="CERRADO")
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get("/api/v1/tablero/exportar/?formato=csv&vista=proyectos&estado=CERRADO")
    contenido = b"".join(respuesta.streaming_content).decode("utf-8")

    assert "PRY-2026-902" in contenido
    assert "PRY-2026-901" not in contenido


def test_exportar_vista_invalida_devuelve_400(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get("/api/v1/tablero/exportar/?formato=csv&vista=no-existe")

    assert respuesta.status_code == 400


# --- Caché ----------------------------------------------------------------


def test_aprobar_un_registro_invalida_la_cache_y_el_siguiente_llamado_refleja_el_cambio(
    roles, cliente
):
    proyecto = ProyectoFactory()
    registro = RegistroEjecucionFactory(
        proyecto=proyecto,
        horas=10,
        estado_aprobacion=EstadoAprobacion.ENVIADO,
        periodo_inicio=datetime.date(2026, 2, 1),
        periodo_fin=datetime.date(2026, 2, 1),
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    primero = cliente.get("/api/v1/tablero/resumen/").data
    assert primero["horas_ejecutadas"] == Decimal("0")

    respuesta_aprobar = cliente.post(f"/api/v1/registros-ejecucion/{registro.id}/aprobar/")
    assert respuesta_aprobar.status_code == 200

    segundo = cliente.get("/api/v1/tablero/resumen/").data
    assert segundo["horas_ejecutadas"] == Decimal("10.00")


def test_refrescar_true_salta_la_cache_sin_necesidad_de_invalidacion(roles, cliente):
    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto, horas_planeadas=100, valor_hora_plan=50_000)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    primero = cliente.get("/api/v1/tablero/resumen/").data
    assert primero["horas_planeadas"] == Decimal("100.00")

    AsignacionRecursoFactory(proyecto=proyecto, horas_planeadas=50, valor_hora_plan=50_000)
    # Sin `refrescar`, la caché de 60s todavía sirve el valor anterior (no hay
    # señal: crear una asignación no aprueba ni publica nada).
    segundo = cliente.get("/api/v1/tablero/resumen/").data
    assert segundo["horas_planeadas"] == Decimal("100.00")

    tercero = cliente.get("/api/v1/tablero/resumen/?refrescar=true").data
    assert tercero["horas_planeadas"] == Decimal("150.00")


# --- /tablero/plan-costos/ ------------------------------------------------


def test_plan_costos_sin_proyecto_da_400(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get("/api/v1/tablero/plan-costos/")

    assert respuesta.status_code == 400


def test_plan_costos_de_proyecto_inexistente_da_404(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(
        "/api/v1/tablero/plan-costos/", {"proyecto": "00000000-0000-0000-0000-000000000000"}
    )

    assert respuesta.status_code == 404


def test_plan_costos_trae_bloques_y_meses(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 2, 28)
    )
    AsignacionRecursoFactory(
        proyecto=proyecto,
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 2, 28),
        horas_planeadas=200,
        valor_hora_plan=50_000,
    )
    RubroPresupuestoFactory(proyecto=proyecto, categoria="LICENCIAS", monto_planeado=1_000_000)
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get("/api/v1/tablero/plan-costos/", {"proyecto": str(proyecto.id)})

    assert respuesta.status_code == 200
    assert respuesta.data["meses"] == ["2026-01", "2026-02"]
    categorias = [b["categoria"] for b in respuesta.data["bloques"]]
    assert categorias == ["PERSONAL", "LICENCIAS"]
    assert "calculado_en" in respuesta.data


def test_lider_no_ve_plan_costos_de_un_proyecto_ajeno(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    otro_gerente = crear_usuario_con_rol("LIDER")
    proyecto_ajeno = ProyectoFactory(gerente=otro_gerente)
    cliente.force_authenticate(user=lider)

    respuesta = cliente.get("/api/v1/tablero/plan-costos/", {"proyecto": str(proyecto_ajeno.id)})

    assert respuesta.status_code == 404


def test_exportar_csv_plan_costos(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 1, 31)
    )
    AsignacionRecursoFactory(
        proyecto=proyecto,
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 1, 31),
        horas_planeadas=100,
        valor_hora_plan=50_000,
    )
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(
        "/api/v1/tablero/exportar/",
        {"formato": "csv", "vista": "plan-costos", "proyecto": str(proyecto.id)},
    )

    assert respuesta.status_code == 200
    contenido = b"".join(respuesta.streaming_content).decode("utf-8")
    assert "Categoría;Concepto" in contenido
    assert "TOTAL GENERAL" in contenido
