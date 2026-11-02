import datetime

import pytest
from rest_framework.test import APIClient

from apps.core.choices import EstadoAprobacion, EstadoProyecto
from apps.ejecucion.tests.factories import RegistroEjecucionFactory
from apps.recursos.tests.factories import AsignacionRecursoFactory, RecursoFactory
from conftest import crear_usuario_con_rol

from .factories import FaseProyectoFactory, ProyectoFactory, RubroPresupuestoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


def _datos_proyecto(**overrides):
    datos = {
        "nombre": "Portal de autoservicio",
        "descripcion": "Portal web para autogestión de clientes.",
        "objetivo": "Reducir llamadas al call center en 20%.",
        "prioridad": "ALTA",
        "fecha_inicio_plan": "2026-01-01",
        "fecha_fin_plan": "2026-12-31",
        "moneda": "COP",
        "presupuesto_horas": "1000.00",
        "presupuesto_dinero": "100000000.00",
        "observaciones": "",
    }
    datos.update(overrides)
    return datos


# --- creación -----------------------------------------------------------


def test_pmo_crea_proyecto_y_el_codigo_se_genera_solo(roles, cliente):
    from apps.catalogos.tests.factories import AreaFactory

    anio = datetime.date.today().year
    area = AreaFactory()
    pmo = crear_usuario_con_rol("PMO")
    gerente = crear_usuario_con_rol("LIDER")
    cliente.force_authenticate(user=pmo)

    respuesta = cliente.post(
        "/api/v1/proyectos/",
        _datos_proyecto(area_solicitante=str(area.id), gerente=str(gerente.id)),
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["codigo"] == f"PRY-{anio}-001"
    # La respuesta de escritura no expone `estado` (no es editable aquí); se
    # confirma el valor por defecto consultando el detalle.
    detalle = cliente.get(f"/api/v1/proyectos/{respuesta.data['id']}/")
    assert detalle.data["estado"] == EstadoProyecto.BORRADOR


@pytest.mark.parametrize("codigo_rol", ["LIDER", "RECURSO", "CONSULTA"])
def test_roles_sin_permiso_no_crean_proyecto(roles, cliente, codigo_rol):
    from apps.catalogos.tests.factories import AreaFactory

    area = AreaFactory()
    usuario = crear_usuario_con_rol(codigo_rol)
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post(
        "/api/v1/proyectos/",
        _datos_proyecto(area_solicitante=str(area.id), gerente=str(usuario.id)),
        format="json",
    )

    assert respuesta.status_code == 403


def test_crear_proyecto_ignora_codigo_enviado_por_el_cliente(roles, cliente):
    from apps.catalogos.tests.factories import AreaFactory

    anio = datetime.date.today().year
    area = AreaFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/proyectos/",
        _datos_proyecto(
            area_solicitante=str(area.id), gerente=str(admin.id), codigo="LO-QUE-SEA"
        ),
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["codigo"] == f"PRY-{anio}-001"


# --- edición y permisos por objeto --------------------------------------


def test_lider_edita_su_proyecto(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    proyecto = ProyectoFactory(gerente=lider)
    cliente.force_authenticate(user=lider)

    respuesta = cliente.patch(
        f"/api/v1/proyectos/{proyecto.id}/", {"nombre": "Nuevo nombre"}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.data["nombre"] == "Nuevo nombre"


def test_lider_no_puede_editar_proyecto_ajeno(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    proyecto = ProyectoFactory()  # gerente distinto
    cliente.force_authenticate(user=lider)

    respuesta = cliente.patch(
        f"/api/v1/proyectos/{proyecto.id}/", {"nombre": "Nuevo nombre"}, format="json"
    )

    # El queryset de LIDER ya está acotado a sus propios proyectos
    # (apps/core/mixins.py), igual que para el resto de modelos de la app:
    # un proyecto ajeno es indistinguible de uno inexistente → 404, nunca 403
    # (ver la nota de apps/accounts/tests/test_permisos.py sobre esta misma
    # decisión para RegistroEjecucion).
    assert respuesta.status_code == 404


# --- transición de estado -------------------------------------------------


def test_cambiar_estado_transicion_invalida_devuelve_409_con_transiciones_validas(
    roles, cliente
):
    proyecto = ProyectoFactory(estado=EstadoProyecto.BORRADOR)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        f"/api/v1/proyectos/{proyecto.id}/cambiar-estado/",
        {"estado": EstadoProyecto.CERRADO, "observacion": "intento inválido"},
        format="json",
    )

    assert respuesta.status_code == 409
    assert set(respuesta.data["error"]["detalles"]["transiciones_validas"]) == {
        "PLANEACION",
        "CANCELADO",
    }


def test_cambiar_estado_a_ejecucion_sin_asignaciones_da_motivo_exacto(roles, cliente):
    proyecto = ProyectoFactory(
        estado=EstadoProyecto.PLANEACION, fecha_inicio_real=datetime.date(2026, 1, 1)
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        f"/api/v1/proyectos/{proyecto.id}/cambiar-estado/",
        {"estado": EstadoProyecto.EJECUCION, "observacion": "arranque"},
        format="json",
    )

    assert respuesta.status_code == 422
    assert "asignaciones" in respuesta.data["error"]["detalles"]


def test_cambiar_estado_valido_actualiza_el_proyecto(roles, cliente):
    proyecto = ProyectoFactory(estado=EstadoProyecto.BORRADOR)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        f"/api/v1/proyectos/{proyecto.id}/cambiar-estado/",
        {"estado": EstadoProyecto.PLANEACION, "observacion": "listo para planear"},
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.data["estado"] == EstadoProyecto.PLANEACION


# --- fases: suma de pesos --------------------------------------------------


def test_guardar_fase_que_deja_suma_en_90_falla_con_mensaje_de_cuanto_falta(roles, cliente):
    proyecto = ProyectoFactory()
    FaseProyectoFactory(proyecto=proyecto, orden=1, peso=100)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/fases-proyecto/",
        {
            "proyecto": str(proyecto.id),
            "nombre": "Cierre",
            "orden": 2,
            "peso": "0.00",
            "fecha_inicio_plan": "2026-01-01",
            "fecha_fin_plan": "2026-02-01",
        },
        format="json",
    )
    # Deja la fase 1 en 100 y agrega una fase 2 en 0: la suma total (100)
    # sigue siendo válida; ahora la bajamos para que falte.
    assert respuesta.status_code == 201

    respuesta = cliente.patch(
        f"/api/v1/fases-proyecto/{proyecto.fases.get(orden=1).id}/",
        {"peso": "90.00"},
        format="json",
    )

    assert respuesta.status_code == 422
    assert "faltan 10" in respuesta.data["error"]["detalles"]["peso"][0].lower()


# --- presupuesto vs rubros --------------------------------------------------


def test_presupuesto_menor_que_suma_de_rubros_se_rechaza(roles, cliente):
    proyecto = ProyectoFactory(presupuesto_dinero=10_000_000)
    RubroPresupuestoFactory(proyecto=proyecto, monto_planeado=8_000_000)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.patch(
        f"/api/v1/proyectos/{proyecto.id}/",
        {"presupuesto_dinero": "5000000.00"},
        format="json",
    )

    assert respuesta.status_code == 422
    assert "presupuesto_dinero" in respuesta.data["error"]["detalles"]
    proyecto.refresh_from_db()
    assert proyecto.presupuesto_dinero == 10_000_000


# --- mis_proyectos -----------------------------------------------------------


def test_mis_proyectos_filtra_por_gerente_lider_tecnico_o_asignacion(roles, cliente):
    gerente = crear_usuario_con_rol("LIDER")
    lider_tecnico = crear_usuario_con_rol("LIDER")
    recurso_usuario = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=recurso_usuario)

    propio_como_gerente = ProyectoFactory(gerente=gerente)
    ProyectoFactory()  # ajeno

    cliente.force_authenticate(user=gerente)
    respuesta = cliente.get("/api/v1/proyectos/?mis_proyectos=true")
    assert [p["id"] for p in respuesta.data["results"]] == [str(propio_como_gerente.id)]

    propio_como_lider_tecnico = ProyectoFactory(lider_tecnico=lider_tecnico)
    cliente.force_authenticate(user=lider_tecnico)
    respuesta = cliente.get("/api/v1/proyectos/?mis_proyectos=true")
    assert [p["id"] for p in respuesta.data["results"]] == [str(propio_como_lider_tecnico.id)]

    proyecto_asignado = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto_asignado, recurso=recurso)
    cliente.force_authenticate(user=recurso_usuario)
    respuesta = cliente.get("/api/v1/proyectos/?mis_proyectos=true")
    assert [p["id"] for p in respuesta.data["results"]] == [str(proyecto_asignado.id)]


# --- borrado lógico ----------------------------------------------------------


def test_borrar_proyecto_con_ejecucion_aprobada_se_rechaza(roles, cliente):
    proyecto = ProyectoFactory()
    RegistroEjecucionFactory(proyecto=proyecto, estado_aprobacion=EstadoAprobacion.APROBADO)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.delete(f"/api/v1/proyectos/{proyecto.id}/")

    assert respuesta.status_code == 409
    proyecto.refresh_from_db()
    assert proyecto.activo is True


def test_borrar_proyecto_sin_ejecucion_aprobada_funciona(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.delete(f"/api/v1/proyectos/{proyecto.id}/")

    assert respuesta.status_code == 204
    proyecto.refresh_from_db()
    assert proyecto.activo is False


def test_detalle_de_proyecto_incluye_resumen_ejecucion_sin_errores(roles, cliente):
    proyecto = ProyectoFactory()
    FaseProyectoFactory(proyecto=proyecto, orden=1, peso=100)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(f"/api/v1/proyectos/{proyecto.id}/")

    assert respuesta.status_code == 200
    resumen = respuesta.data["resumen_ejecucion"]
    assert resumen["semaforo"] in {"VERDE", "AMARILLO", "ROJO"}
    assert resumen["pct_horas"] is None  # sin asignaciones todavía


# --- cronograma (docs/plan/fase-07-tareas-programacion.md §7.2.6) ------------


def test_cronograma_ordena_por_fase_y_fecha_e_incluye_dependencias(roles, cliente):
    from apps.core.choices import TipoDependencia
    from apps.tareas.tests.factories import DependenciaTareaFactory, TareaFactory

    proyecto = ProyectoFactory()
    fase_2 = FaseProyectoFactory(proyecto=proyecto, orden=2, peso=50)
    fase_1 = FaseProyectoFactory(proyecto=proyecto, orden=1, peso=50)
    tarea_fase_2 = TareaFactory(
        proyecto=proyecto, fase=fase_2, fecha_inicio_plan=datetime.date(2026, 1, 1)
    )
    tarea_fase_1_tardia = TareaFactory(
        proyecto=proyecto, fase=fase_1, fecha_inicio_plan=datetime.date(2026, 2, 1)
    )
    tarea_fase_1_temprana = TareaFactory(
        proyecto=proyecto, fase=fase_1, fecha_inicio_plan=datetime.date(2026, 1, 15)
    )
    DependenciaTareaFactory(
        tarea_origen=tarea_fase_1_temprana,
        tarea_destino=tarea_fase_1_tardia,
        tipo=TipoDependencia.FI,
        dias_desfase=1,
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(f"/api/v1/proyectos/{proyecto.id}/cronograma/")

    assert respuesta.status_code == 200
    codigos = [fila["codigo"] for fila in respuesta.data]
    assert codigos == [
        tarea_fase_1_temprana.codigo,
        tarea_fase_1_tardia.codigo,
        tarea_fase_2.codigo,
    ]

    fila_tardia = respuesta.data[1]
    assert fila_tardia["dependencias"] == [
        {
            "tarea_id": str(tarea_fase_1_temprana.id),
            "tipo": "FI",
            "dias_desfase": 1,
        }
    ]


def test_cronograma_resuelve_en_menos_de_10_consultas_con_40_tareas(
    roles, cliente, django_assert_max_num_queries
):
    from apps.tareas.tests.factories import TareaFactory

    proyecto = ProyectoFactory()
    fase = FaseProyectoFactory(proyecto=proyecto, orden=1, peso=100)
    for n in range(40):
        TareaFactory(proyecto=proyecto, fase=fase, orden=n)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    with django_assert_max_num_queries(10):
        respuesta = cliente.get(f"/api/v1/proyectos/{proyecto.id}/cronograma/")

    assert respuesta.status_code == 200
    assert len(respuesta.data) == 40
