import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.core.choices import EstadoAprobacion, Periodicidad
from apps.proyectos.tests.factories import ProyectoFactory, RubroPresupuestoFactory
from apps.recursos.tests.factories import RecursoFactory, TarifaRecursoFactory
from apps.tareas.tests.factories import TareaFactory
from conftest import crear_usuario_con_rol

from .factories import GastoEjecutadoFactory, RegistroEjecucionFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


def _datos_registro(proyecto, recurso, **extra):
    datos = {
        "proyecto": str(proyecto.id),
        "recurso": str(recurso.id),
        "periodicidad": "DIARIA",
        "periodo_inicio": str(proyecto.fecha_inicio_plan),
        "horas": "8.00",
        "descripcion": "Trabajo de desarrollo",
    }
    datos.update(extra)
    return datos


# --- creación y normalización ----------------------------------------------------


def test_crear_registro_diario_resuelve_tarifa_y_costo(roles, cliente):
    proyecto = ProyectoFactory()
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/registros-ejecucion/", _datos_registro(proyecto, recurso), format="json"
    )

    assert respuesta.status_code == 201
    assert respuesta.data["valor_hora_aplicado"] == "70000.00"
    assert respuesta.data["costo"] == "560000.00"
    assert str(respuesta.data["registrado_por"]) == str(admin.id)


def test_registro_semanal_creado_desde_miercoles_se_normaliza(roles, cliente):
    proyecto = ProyectoFactory()
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/registros-ejecucion/",
        _datos_registro(
            proyecto, recurso, periodicidad="SEMANAL", periodo_inicio="2026-10-28", horas="40.00"
        ),
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["periodo_inicio"] == "2026-10-26"
    assert respuesta.data["periodo_fin"] == "2026-11-01"


def test_duplicado_exacto_da_400_por_restriccion_unica(roles, cliente):
    proyecto = ProyectoFactory()
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    datos = _datos_registro(proyecto, recurso)
    primero = cliente.post("/api/v1/registros-ejecucion/", datos, format="json")
    assert primero.status_code == 201

    segundo = cliente.post("/api/v1/registros-ejecucion/", datos, format="json")
    assert segundo.status_code == 400


def test_mensual_solapado_con_diario_da_422_con_conflictos(roles, cliente):
    proyecto = ProyectoFactory()
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        recurso=recurso,
        periodicidad=Periodicidad.DIARIA,
        periodo_inicio=datetime.date(2026, 3, 15),
        periodo_fin=datetime.date(2026, 3, 15),
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/registros-ejecucion/",
        _datos_registro(
            proyecto, recurso, periodicidad="MENSUAL", periodo_inicio="2026-03-01", horas="160.00"
        ),
        format="json",
    )

    assert respuesta.status_code == 422
    assert len(respuesta.data["error"]["detalles"]["conflictos"]) == 1


def test_dos_registros_mismo_recurso_en_proyectos_distintos_el_mismo_dia_se_permite(roles, cliente):
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    proyecto_1 = ProyectoFactory()
    proyecto_2 = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    r1 = cliente.post(
        "/api/v1/registros-ejecucion/", _datos_registro(proyecto_1, recurso), format="json"
    )
    r2 = cliente.post(
        "/api/v1/registros-ejecucion/", _datos_registro(proyecto_2, recurso), format="json"
    )

    assert r1.status_code == 201
    assert r2.status_code == 201


def test_tope_excedido_da_201_con_advertencia(roles, cliente):
    proyecto = ProyectoFactory()
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/registros-ejecucion/",
        _datos_registro(proyecto, recurso, horas="30.00"),
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["advertencias"]


# --- permisos de creación -----------------------------------------------------------


def test_recurso_no_puede_registrar_a_nombre_de_otro(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    RecursoFactory(usuario=titular)
    otro_recurso = RecursoFactory(perfil=None)
    proyecto = ProyectoFactory()
    cliente.force_authenticate(user=titular)

    respuesta = cliente.post(
        "/api/v1/registros-ejecucion/", _datos_registro(proyecto, otro_recurso), format="json"
    )

    assert respuesta.status_code == 403


def test_recurso_puede_registrar_a_su_propio_nombre(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular, perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    proyecto = ProyectoFactory()
    cliente.force_authenticate(user=titular)

    respuesta = cliente.post(
        "/api/v1/registros-ejecucion/", _datos_registro(proyecto, recurso), format="json"
    )

    assert respuesta.status_code == 201


# --- edición y estado inmutable ------------------------------------------------------


def test_patch_sobre_registro_aprobado_da_409(roles, cliente):
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.APROBADO)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.patch(
        f"/api/v1/registros-ejecucion/{registro.id}/", {"horas": "5.00"}, format="json"
    )

    assert respuesta.status_code == 409


def test_patch_sobre_borrador_funciona(roles, cliente):
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.BORRADOR)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.patch(
        f"/api/v1/registros-ejecucion/{registro.id}/", {"horas": "5.00"}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.data["horas"] == "5.00"


# --- ciclo de aprobación vía API -----------------------------------------------------


def test_ciclo_completo_enviar_aprobar(roles, cliente):
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.BORRADOR)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(f"/api/v1/registros-ejecucion/{registro.id}/enviar/")
    assert respuesta.status_code == 200
    assert respuesta.data["estado_aprobacion"] == "ENVIADO"

    respuesta = cliente.post(f"/api/v1/registros-ejecucion/{registro.id}/aprobar/")
    assert respuesta.status_code == 200
    assert respuesta.data["estado_aprobacion"] == "APROBADO"


def test_rechazar_sin_motivo_da_400(roles, cliente):
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.ENVIADO)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        f"/api/v1/registros-ejecucion/{registro.id}/rechazar/", {}, format="json"
    )

    assert respuesta.status_code == 400


def test_rechazar_con_motivo_lo_muestra_en_el_registro(roles, cliente):
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.ENVIADO)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        f"/api/v1/registros-ejecucion/{registro.id}/rechazar/",
        {"motivo_rechazo": "Horas no sustentadas."},
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.data["motivo_rechazo"] == "Horas no sustentadas."
    assert respuesta.data["estado_aprobacion"] == "RECHAZADO"


def test_autor_no_puede_aprobar_su_registro_via_api(roles, cliente):
    autor = crear_usuario_con_rol("PMO")
    registro = RegistroEjecucionFactory(
        estado_aprobacion=EstadoAprobacion.ENVIADO, registrado_por=autor
    )
    cliente.force_authenticate(user=autor)

    respuesta = cliente.post(f"/api/v1/registros-ejecucion/{registro.id}/aprobar/")

    assert respuesta.status_code == 403


def test_reabrir_solo_pmo_o_admin(roles, cliente):
    proyecto = ProyectoFactory()
    lider = crear_usuario_con_rol("LIDER")
    registro = RegistroEjecucionFactory(
        proyecto=proyecto, estado_aprobacion=EstadoAprobacion.APROBADO
    )
    cliente.force_authenticate(user=lider)

    respuesta = cliente.post(f"/api/v1/registros-ejecucion/{registro.id}/reabrir/")
    assert respuesta.status_code == 403

    pmo = crear_usuario_con_rol("PMO")
    cliente.force_authenticate(user=pmo)
    respuesta = cliente.post(f"/api/v1/registros-ejecucion/{registro.id}/reabrir/")
    assert respuesta.status_code == 200
    assert respuesta.data["estado_aprobacion"] == "ENVIADO"


# --- carga_lote --------------------------------------------------------------------


def test_carga_lote_crea_los_validos_y_reporta_los_invalidos(roles, cliente):
    proyecto = ProyectoFactory()
    recurso_1 = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso_1, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    recurso_2 = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso_2, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    registros = [
        _datos_registro(proyecto, recurso_1, periodo_inicio="2026-02-01"),
        _datos_registro(proyecto, recurso_1, periodo_inicio="2026-02-02"),
        {"proyecto": str(proyecto.id)},  # inválido: faltan campos obligatorios
        _datos_registro(proyecto, recurso_2, periodo_inicio="2026-02-01"),
        {"recurso": str(recurso_2.id)},  # inválido
    ]

    respuesta = cliente.post(
        "/api/v1/registros-ejecucion/lote/", {"registros": registros}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.data["creados"] == 3
    assert len(respuesta.data["errores"]) == 2
    assert {e["indice"] for e in respuesta.data["errores"]} == {2, 4}


# --- resumen ----------------------------------------------------------------------


def test_resumen_agrupado_por_recurso(roles, cliente):
    proyecto = ProyectoFactory()
    recurso = RecursoFactory(perfil=None)
    RegistroEjecucionFactory(
        proyecto=proyecto,
        recurso=recurso,
        horas=8,
        valor_hora_aplicado=70_000,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        periodo_inicio=datetime.date(2026, 1, 5),
        periodo_fin=datetime.date(2026, 1, 5),
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        recurso=recurso,
        horas=4,
        valor_hora_aplicado=70_000,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        periodo_inicio=datetime.date(2026, 1, 6),
        periodo_fin=datetime.date(2026, 1, 6),
    )
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get(
        f"/api/v1/registros-ejecucion/resumen/?proyecto={proyecto.id}&agrupar_por=recurso"
    )

    assert respuesta.status_code == 200
    assert len(respuesta.data) == 1
    assert respuesta.data[0]["horas"] == Decimal("12.00")


# --- gastos ejecutados --------------------------------------------------------------


def test_lider_crea_gasto_pero_no_puede_aprobarlo(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    proyecto = ProyectoFactory(gerente=lider)
    rubro = RubroPresupuestoFactory(proyecto=proyecto, monto_planeado=10_000_000)
    cliente.force_authenticate(user=lider)

    respuesta = cliente.post(
        "/api/v1/gastos-ejecutados/",
        {
            "proyecto": str(proyecto.id),
            "rubro": str(rubro.id),
            "fecha": "2026-02-01",
            "monto": "500000.00",
            "proveedor": "Proveedor X",
            "numero_documento": "FAC-001",
        },
        format="json",
    )
    assert respuesta.status_code == 201
    gasto_id = respuesta.data["id"]

    respuesta = cliente.post(f"/api/v1/gastos-ejecutados/{gasto_id}/enviar/")
    assert respuesta.status_code == 403


def test_recurso_no_tiene_ningun_acceso_a_gastos(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    RecursoFactory(usuario=titular)
    GastoEjecutadoFactory()
    cliente.force_authenticate(user=titular)

    respuesta = cliente.get("/api/v1/gastos-ejecutados/")

    assert respuesta.status_code == 403


def test_gasto_de_rubro_de_otro_proyecto_da_400(roles, cliente):
    proyecto = ProyectoFactory()
    rubro_ajeno = RubroPresupuestoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/gastos-ejecutados/",
        {
            "proyecto": str(proyecto.id),
            "rubro": str(rubro_ajeno.id),
            "fecha": "2026-02-01",
            "monto": "100000.00",
        },
        format="json",
    )

    assert respuesta.status_code == 400


def test_pmo_aprueba_gasto_y_suma_al_rubro(roles, cliente):
    proyecto = ProyectoFactory()
    rubro = RubroPresupuestoFactory(proyecto=proyecto, monto_planeado=10_000_000)
    gasto = GastoEjecutadoFactory(
        proyecto=proyecto, rubro=rubro, monto=500_000, estado_aprobacion=EstadoAprobacion.ENVIADO
    )
    pmo = crear_usuario_con_rol("PMO")
    cliente.force_authenticate(user=pmo)

    respuesta = cliente.post(f"/api/v1/gastos-ejecutados/{gasto.id}/aprobar/")

    assert respuesta.status_code == 200
    rubro.refresh_from_db()
    assert rubro.monto_ejecutado == 500_000


# --- tarea de otra tarea cancelada / proyecto ejecucion ----------------------------


def test_ejecucion_sobre_tarea_cancelada_da_400(roles, cliente):
    from apps.core.choices import EstadoTarea

    proyecto = ProyectoFactory()
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=70_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    tarea = TareaFactory(proyecto=proyecto, estado=EstadoTarea.CANCELADA)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/registros-ejecucion/",
        _datos_registro(proyecto, recurso, tarea=str(tarea.id)),
        format="json",
    )

    assert respuesta.status_code == 400
