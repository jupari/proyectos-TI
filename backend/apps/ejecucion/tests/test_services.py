import datetime
from decimal import Decimal

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.tests.factories import UsuarioFactory
from apps.core.choices import EstadoAprobacion, EstadoTarea, Periodicidad
from apps.core.exceptions import ErrorConflicto, ErrorReglaNegocio
from apps.ejecucion.services import (
    aprobar,
    aprobar_gasto,
    comparativo_por_mes,
    comparativo_por_recurso,
    enviar,
    enviar_gasto,
    preparar_registro,
    reabrir,
    reabrir_gasto,
    recalcular_tarea,
    rechazar,
    rechazar_gasto,
    validar_rango_proyecto,
    validar_solapamiento,
    validar_tarea,
    validar_topes,
)
from apps.ejecucion.tests.factories import GastoEjecutadoFactory, RegistroEjecucionFactory
from apps.proyectos.tests.factories import ProyectoFactory, RubroPresupuestoFactory
from apps.recursos.tests.factories import (
    AsignacionRecursoFactory,
    RecursoFactory,
    TarifaRecursoFactory,
)
from apps.tareas.tests.factories import TareaFactory

pytestmark = pytest.mark.django_db


# --- preparar_registro (normalización + tarifa) -------------------------------


def test_preparar_registro_normaliza_semanal_desde_un_miercoles():
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=50_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    registro = RegistroEjecucionFactory.build(
        recurso=recurso,
        periodicidad=Periodicidad.SEMANAL,
        periodo_inicio=datetime.date(2026, 10, 28),  # miércoles
        valor_hora_aplicado=None,
    )

    preparar_registro(registro)

    assert registro.periodo_inicio == datetime.date(2026, 10, 26)  # lunes
    assert registro.periodo_fin == datetime.date(2026, 11, 1)  # domingo


def test_preparar_registro_resuelve_valor_hora_vigente_si_no_viene_dado():
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=80_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    registro = RegistroEjecucionFactory.build(
        recurso=recurso, periodicidad=Periodicidad.DIARIA, valor_hora_aplicado=None
    )

    preparar_registro(registro)

    assert registro.valor_hora_aplicado == Decimal("80000")


def test_preparar_registro_respeta_valor_hora_enviado_explicitamente():
    recurso = RecursoFactory(perfil=None)
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=80_000, vigente_desde=datetime.date(2020, 1, 1)
    )
    registro = RegistroEjecucionFactory.build(
        recurso=recurso, periodicidad=Periodicidad.DIARIA, valor_hora_aplicado=Decimal("95000")
    )

    preparar_registro(registro)

    assert registro.valor_hora_aplicado == Decimal("95000")


# --- validar_solapamiento ------------------------------------------------------


def test_validar_solapamiento_detecta_mensual_contra_diario_del_mismo_mes():
    proyecto = ProyectoFactory()
    recurso = RecursoFactory()
    RegistroEjecucionFactory(
        proyecto=proyecto,
        recurso=recurso,
        periodicidad=Periodicidad.MENSUAL,
        periodo_inicio=datetime.date(2026, 3, 1),
        periodo_fin=datetime.date(2026, 3, 31),
    )
    nuevo = RegistroEjecucionFactory.build(
        proyecto=proyecto,
        recurso=recurso,
        periodicidad=Periodicidad.DIARIA,
        periodo_inicio=datetime.date(2026, 3, 15),
        periodo_fin=datetime.date(2026, 3, 15),
    )

    with pytest.raises(ErrorReglaNegocio) as excinfo:
        validar_solapamiento(nuevo)

    assert len(excinfo.value.detail["conflictos"]) == 1


def test_validar_solapamiento_permite_mismo_recurso_en_proyectos_distintos():
    recurso = RecursoFactory()
    RegistroEjecucionFactory(
        recurso=recurso,
        proyecto=ProyectoFactory(),
        periodicidad=Periodicidad.DIARIA,
        periodo_inicio=datetime.date(2026, 3, 15),
        periodo_fin=datetime.date(2026, 3, 15),
    )
    nuevo = RegistroEjecucionFactory.build(
        recurso=recurso,
        proyecto=ProyectoFactory(),
        periodicidad=Periodicidad.DIARIA,
        periodo_inicio=datetime.date(2026, 3, 15),
        periodo_fin=datetime.date(2026, 3, 15),
    )

    validar_solapamiento(nuevo)  # no lanza


def test_validar_solapamiento_ignora_registros_rechazados():
    proyecto = ProyectoFactory()
    recurso = RecursoFactory()
    RegistroEjecucionFactory(
        proyecto=proyecto,
        recurso=recurso,
        periodicidad=Periodicidad.MENSUAL,
        periodo_inicio=datetime.date(2026, 3, 1),
        periodo_fin=datetime.date(2026, 3, 31),
        estado_aprobacion=EstadoAprobacion.RECHAZADO,
    )
    nuevo = RegistroEjecucionFactory.build(
        proyecto=proyecto,
        recurso=recurso,
        periodicidad=Periodicidad.DIARIA,
        periodo_inicio=datetime.date(2026, 3, 15),
        periodo_fin=datetime.date(2026, 3, 15),
    )

    validar_solapamiento(nuevo)  # no lanza


# --- validar_topes --------------------------------------------------------------


def test_validar_topes_diaria_excedida_da_advertencia():
    registro = RegistroEjecucionFactory.build(periodicidad=Periodicidad.DIARIA, horas=30)
    advertencias = validar_topes(registro)
    assert advertencias


def test_validar_topes_dentro_del_limite_no_da_advertencia():
    registro = RegistroEjecucionFactory.build(periodicidad=Periodicidad.DIARIA, horas=8)
    assert validar_topes(registro) == []


def test_validar_topes_mensual_dentro_de_1_5_veces_la_capacidad_no_advierte():
    recurso = RecursoFactory(capacidad_horas_mes=160)
    registro = RegistroEjecucionFactory.build(
        recurso=recurso, periodicidad=Periodicidad.MENSUAL, horas=200
    )
    assert validar_topes(registro) == []  # 200 <= 160 * 1.5 = 240


def test_validar_topes_mensual_por_encima_de_1_5_veces_la_capacidad_advierte():
    recurso = RecursoFactory(capacidad_horas_mes=160)
    registro = RegistroEjecucionFactory.build(
        recurso=recurso, periodicidad=Periodicidad.MENSUAL, horas=250
    )
    assert validar_topes(registro)  # 250 > 160 * 1.5 = 240


def test_validar_topes_semanal_excedida_da_advertencia():
    registro = RegistroEjecucionFactory.build(periodicidad=Periodicidad.SEMANAL, horas=65)
    assert validar_topes(registro)  # 65 > 60


def test_validar_topes_semanal_dentro_del_limite_no_advierte():
    registro = RegistroEjecucionFactory.build(periodicidad=Periodicidad.SEMANAL, horas=40)
    assert validar_topes(registro) == []


# --- validar_rango_proyecto ------------------------------------------------------


def test_validar_rango_proyecto_rechaza_periodo_fuera_de_rango():
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 6, 30)
    )
    registro = RegistroEjecucionFactory.build(
        proyecto=proyecto,
        periodicidad=Periodicidad.DIARIA,
        periodo_inicio=datetime.date(2025, 12, 1),
        periodo_fin=datetime.date(2025, 12, 1),
    )
    with pytest.raises(ValidationError):
        validar_rango_proyecto(registro)


def test_validar_rango_proyecto_acepta_dentro_de_fechas_reales_aunque_fuera_del_plan():
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1),
        fecha_fin_plan=datetime.date(2026, 6, 30),
        fecha_inicio_real=datetime.date(2026, 1, 1),
        fecha_fin_real=datetime.date(2026, 8, 31),
    )
    registro = RegistroEjecucionFactory.build(
        proyecto=proyecto,
        periodicidad=Periodicidad.DIARIA,
        periodo_inicio=datetime.date(2026, 8, 15),
        periodo_fin=datetime.date(2026, 8, 15),
    )
    validar_rango_proyecto(registro)  # no lanza: el cierre real se extendió


# --- validar_tarea -----------------------------------------------------------------


def test_validar_tarea_rechaza_tarea_de_otro_proyecto():
    proyecto = ProyectoFactory()
    tarea_ajena = TareaFactory()
    registro = RegistroEjecucionFactory.build(proyecto=proyecto, tarea=tarea_ajena)
    with pytest.raises(ValidationError):
        validar_tarea(registro)


def test_validar_tarea_rechaza_tarea_cancelada():
    proyecto = ProyectoFactory()
    tarea = TareaFactory(proyecto=proyecto, estado=EstadoTarea.CANCELADA)
    registro = RegistroEjecucionFactory.build(proyecto=proyecto, tarea=tarea)
    with pytest.raises(ValidationError):
        validar_tarea(registro)


def test_validar_tarea_sin_tarea_no_hace_nada():
    registro = RegistroEjecucionFactory.build(tarea=None)
    validar_tarea(registro)  # no lanza


# --- ciclo de aprobación ------------------------------------------------------------


def test_enviar_desde_borrador():
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.BORRADOR)
    usuario = UsuarioFactory()
    enviar(registro, usuario)
    registro.refresh_from_db()
    assert registro.estado_aprobacion == EstadoAprobacion.ENVIADO


def test_enviar_desde_aprobado_falla():
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.APROBADO)
    with pytest.raises(ErrorConflicto):
        enviar(registro, UsuarioFactory())


def test_aprobar_suma_a_tarea_horas_ejecutadas():
    tarea = TareaFactory(horas_estimadas=100)
    registro = RegistroEjecucionFactory(
        tarea=tarea, proyecto=tarea.proyecto, estado_aprobacion=EstadoAprobacion.ENVIADO, horas=8
    )
    aprobar(registro, UsuarioFactory())
    tarea.refresh_from_db()
    assert tarea.horas_ejecutadas == Decimal("8.00")


def test_rechazar_no_suma_a_tarea_horas_ejecutadas():
    tarea = TareaFactory(horas_estimadas=100)
    registro = RegistroEjecucionFactory(
        tarea=tarea, proyecto=tarea.proyecto, estado_aprobacion=EstadoAprobacion.ENVIADO, horas=8
    )
    rechazar(registro, "No corresponde a esta tarea.", UsuarioFactory())
    tarea.refresh_from_db()
    assert tarea.horas_ejecutadas == Decimal("0.00")
    registro.refresh_from_db()
    assert registro.motivo_rechazo == "No corresponde a esta tarea."


def test_rechazar_sin_motivo_falla():
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.ENVIADO)
    with pytest.raises(ValidationError):
        rechazar(registro, "", UsuarioFactory())


def test_aprobar_un_registro_no_enviado_falla():
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.BORRADOR)
    with pytest.raises(ErrorConflicto):
        aprobar(registro, UsuarioFactory())


def test_rechazar_un_registro_no_enviado_falla():
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.BORRADOR)
    with pytest.raises(ErrorConflicto):
        rechazar(registro, "No corresponde.", UsuarioFactory())


def test_reabrir_un_registro_no_aprobado_falla():
    registro = RegistroEjecucionFactory(estado_aprobacion=EstadoAprobacion.ENVIADO)
    with pytest.raises(ErrorConflicto):
        reabrir(registro, UsuarioFactory())


def test_reabrir_resta_de_tarea_horas_ejecutadas():
    tarea = TareaFactory(horas_estimadas=100)
    registro = RegistroEjecucionFactory(
        tarea=tarea, proyecto=tarea.proyecto, estado_aprobacion=EstadoAprobacion.ENVIADO, horas=8
    )
    aprobar(registro, UsuarioFactory())
    tarea.refresh_from_db()
    assert tarea.horas_ejecutadas == Decimal("8.00")

    reabrir(registro, UsuarioFactory())
    tarea.refresh_from_db()
    assert tarea.horas_ejecutadas == Decimal("0.00")
    registro.refresh_from_db()
    assert registro.estado_aprobacion == EstadoAprobacion.ENVIADO
    assert registro.aprobado_por is None


def test_autor_no_puede_aprobar_su_propio_registro():
    autor = UsuarioFactory()
    registro = RegistroEjecucionFactory(
        estado_aprobacion=EstadoAprobacion.ENVIADO, registrado_por=autor
    )
    with pytest.raises(PermissionDenied):
        aprobar(registro, autor)


def test_lider_del_proyecto_si_puede_aprobar_registro_de_otro():
    proyecto = ProyectoFactory()
    autor = UsuarioFactory()
    registro = RegistroEjecucionFactory(
        proyecto=proyecto, estado_aprobacion=EstadoAprobacion.ENVIADO, registrado_por=autor
    )
    aprobar(registro, proyecto.gerente)  # el gerente no es el autor: no debe lanzar
    registro.refresh_from_db()
    assert registro.estado_aprobacion == EstadoAprobacion.APROBADO


def test_admin_si_puede_aprobar_su_propio_registro(roles):
    admin = UsuarioFactory()
    from django.contrib.auth.models import Group

    Group.objects.get(rol_meta__codigo="ADMIN").user_set.add(admin)
    registro = RegistroEjecucionFactory(
        estado_aprobacion=EstadoAprobacion.ENVIADO, registrado_por=admin
    )
    aprobar(registro, admin)  # no lanza
    registro.refresh_from_db()
    assert registro.estado_aprobacion == EstadoAprobacion.APROBADO


# --- recalcular_tarea con subtareas / tareas sin tarea -----------------------------


def test_recalcular_tarea_sin_tarea_asociada_no_hace_nada():
    registro = RegistroEjecucionFactory.build(tarea=None)
    recalcular_tarea(registro)  # no lanza, no hace nada


def test_recalcular_tarea_suma_solo_lo_aprobado():
    tarea = TareaFactory(horas_estimadas=100)
    RegistroEjecucionFactory(
        tarea=tarea,
        proyecto=tarea.proyecto,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        horas=5,
        periodo_inicio=datetime.date(2026, 1, 1),
        periodo_fin=datetime.date(2026, 1, 1),
    )
    RegistroEjecucionFactory(
        tarea=tarea,
        proyecto=tarea.proyecto,
        estado_aprobacion=EstadoAprobacion.ENVIADO,
        horas=3,
        periodo_inicio=datetime.date(2026, 1, 2),
        periodo_fin=datetime.date(2026, 1, 2),
    )
    ultimo = RegistroEjecucionFactory(
        tarea=tarea,
        proyecto=tarea.proyecto,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        horas=2,
        periodo_inicio=datetime.date(2026, 1, 3),
        periodo_fin=datetime.date(2026, 1, 3),
    )
    recalcular_tarea(ultimo)
    tarea.refresh_from_db()
    assert tarea.horas_ejecutadas == Decimal("7.00")


# --- comparativo_por_recurso / comparativo_por_mes --------------------------------


def test_comparativo_por_recurso_calcula_pct_a_mano():
    proyecto = ProyectoFactory()
    recurso = RecursoFactory()
    AsignacionRecursoFactory(
        proyecto=proyecto, recurso=recurso, horas_planeadas=100, valor_hora_plan=50_000
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        recurso=recurso,
        horas=40,
        valor_hora_aplicado=50_000,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        periodo_inicio=datetime.date(2026, 1, 5),
        periodo_fin=datetime.date(2026, 1, 5),
    )

    resultado = comparativo_por_recurso(proyecto)

    assert len(resultado) == 1
    fila = resultado[0]
    assert fila["horas_plan"] == Decimal("100.00")
    assert fila["horas_ejec"] == Decimal("40.00")
    assert fila["costo_plan"] == Decimal("5000000.00")
    assert fila["costo_ejec"] == Decimal("2000000.00")
    assert fila["pct_horas"] == pytest.approx(40.0)
    assert fila["pct_dinero"] == pytest.approx(40.0)


def test_comparativo_por_mes_prorratea_el_plan_y_asigna_lo_ejecutado_a_su_mes():
    proyecto = ProyectoFactory()
    recurso = RecursoFactory()
    AsignacionRecursoFactory(
        proyecto=proyecto,
        recurso=recurso,
        fecha_desde=datetime.date(2026, 2, 1),
        fecha_hasta=datetime.date(2026, 3, 31),
        horas_planeadas=590,
        valor_hora_plan=10_000,
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        recurso=recurso,
        periodicidad=Periodicidad.DIARIA,
        periodo_inicio=datetime.date(2026, 2, 10),
        periodo_fin=datetime.date(2026, 2, 10),
        horas=8,
        valor_hora_aplicado=10_000,
        estado_aprobacion=EstadoAprobacion.APROBADO,
    )

    resultado = comparativo_por_mes(proyecto)

    assert [(f["anio"], f["mes"]) for f in resultado] == [(2026, 2), (2026, 3)]
    febrero = resultado[0]
    assert febrero["horas_plan"] == Decimal("280")  # 590 * 28/59
    assert febrero["horas_ejec"] == Decimal("8.00")
    marzo = resultado[1]
    assert marzo["horas_ejec"] == Decimal("0")


def test_comparativo_por_mes_sin_asignaciones_ni_ejecucion_devuelve_vacio():
    proyecto = ProyectoFactory()
    assert comparativo_por_mes(proyecto) == []


# --- ciclo de aprobación de GastoEjecutado (mismo ciclo que RegistroEjecucion,
# sin autor ni autoaprobación) -----------------------------------------------


def test_enviar_gasto_desde_borrador():
    gasto = GastoEjecutadoFactory(estado_aprobacion=EstadoAprobacion.BORRADOR)
    enviar_gasto(gasto, UsuarioFactory())
    gasto.refresh_from_db()
    assert gasto.estado_aprobacion == EstadoAprobacion.ENVIADO


def test_enviar_gasto_desde_aprobado_falla():
    gasto = GastoEjecutadoFactory(estado_aprobacion=EstadoAprobacion.APROBADO)
    with pytest.raises(ErrorConflicto):
        enviar_gasto(gasto, UsuarioFactory())


def test_aprobar_gasto_suma_a_monto_ejecutado_del_rubro():
    rubro = RubroPresupuestoFactory(monto_planeado=1_000_000)
    gasto = GastoEjecutadoFactory(
        rubro=rubro,
        proyecto=rubro.proyecto,
        monto=400_000,
        estado_aprobacion=EstadoAprobacion.ENVIADO,
    )
    aprobar_gasto(gasto, UsuarioFactory())
    rubro.refresh_from_db()
    assert rubro.monto_ejecutado == Decimal("400000.00")


def test_aprobar_gasto_no_enviado_falla():
    gasto = GastoEjecutadoFactory(estado_aprobacion=EstadoAprobacion.BORRADOR)
    with pytest.raises(ErrorConflicto):
        aprobar_gasto(gasto, UsuarioFactory())


def test_rechazar_gasto_sin_motivo_falla():
    gasto = GastoEjecutadoFactory(estado_aprobacion=EstadoAprobacion.ENVIADO)
    with pytest.raises(ValidationError):
        rechazar_gasto(gasto, "", UsuarioFactory())


def test_rechazar_gasto_no_enviado_falla():
    gasto = GastoEjecutadoFactory(estado_aprobacion=EstadoAprobacion.BORRADOR)
    with pytest.raises(ErrorConflicto):
        rechazar_gasto(gasto, "No corresponde.", UsuarioFactory())


def test_rechazar_gasto_enviado_lo_marca_rechazado():
    gasto = GastoEjecutadoFactory(estado_aprobacion=EstadoAprobacion.ENVIADO)
    rechazar_gasto(gasto, "Factura ilegible.", UsuarioFactory())
    gasto.refresh_from_db()
    assert gasto.estado_aprobacion == EstadoAprobacion.RECHAZADO


def test_reabrir_gasto_resta_del_monto_ejecutado_del_rubro():
    rubro = RubroPresupuestoFactory(monto_planeado=1_000_000)
    gasto = GastoEjecutadoFactory(
        rubro=rubro,
        proyecto=rubro.proyecto,
        monto=400_000,
        estado_aprobacion=EstadoAprobacion.APROBADO,
    )
    rubro.monto_ejecutado = Decimal("400000.00")
    rubro.save(update_fields=["monto_ejecutado"])

    reabrir_gasto(gasto, UsuarioFactory())

    gasto.refresh_from_db()
    rubro.refresh_from_db()
    assert gasto.estado_aprobacion == EstadoAprobacion.ENVIADO
    assert rubro.monto_ejecutado == Decimal("0.00")


def test_reabrir_gasto_no_aprobado_falla():
    gasto = GastoEjecutadoFactory(estado_aprobacion=EstadoAprobacion.ENVIADO)
    with pytest.raises(ErrorConflicto):
        reabrir_gasto(gasto, UsuarioFactory())
