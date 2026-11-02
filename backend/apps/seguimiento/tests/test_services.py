import datetime
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.accounts.tests.factories import UsuarioFactory
from apps.core.choices import (
    EstadoAprobacion,
    EstadoCompromiso,
    EstadoHito,
    EstadoSeguimiento,
    Periodicidad,
    Semaforo,
)
from apps.core.exceptions import ErrorConflicto
from apps.ejecucion.tests.factories import RegistroEjecucionFactory
from apps.proyectos.tests.factories import HitoFactory, ProyectoFactory
from apps.seguimiento.models import CompromisoSeguimiento
from apps.seguimiento.services import marcar_compromisos_vencidos, precargar, publicar, reabrir
from apps.seguimiento.tests.factories import CompromisoSeguimientoFactory, SeguimientoFactory

pytestmark = pytest.mark.django_db


# --- precargar -----------------------------------------------------------------


def test_precargar_suma_solo_lo_aprobado_del_periodo():
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 12, 31)
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        horas=10,
        valor_hora_aplicado=50_000,
        periodo_inicio=datetime.date(2026, 3, 5),
        periodo_fin=datetime.date(2026, 3, 5),
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        estado_aprobacion=EstadoAprobacion.ENVIADO,
        horas=8,
        valor_hora_aplicado=50_000,
        periodo_inicio=datetime.date(2026, 3, 6),
        periodo_fin=datetime.date(2026, 3, 6),
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        horas=20,
        valor_hora_aplicado=50_000,
        periodo_inicio=datetime.date(2026, 2, 1),
        periodo_fin=datetime.date(2026, 2, 28),
    )

    datos = precargar(proyecto, Periodicidad.MENSUAL, datetime.date(2026, 3, 15))

    assert datos["periodo_inicio"] == datetime.date(2026, 3, 1)
    assert datos["periodo_fin"] == datetime.date(2026, 3, 31)
    assert datos["horas_periodo"] == Decimal("10.00")
    assert datos["costo_periodo"] == Decimal("500000.00")
    # acumulado: suma lo aprobado de marzo (10h) + febrero (20h) = 30h
    assert datos["horas_acumuladas"] == Decimal("30.00")


def test_precargar_toma_el_avance_del_seguimiento_anterior():
    proyecto = ProyectoFactory()
    SeguimientoFactory(
        proyecto=proyecto,
        periodicidad=Periodicidad.MENSUAL,
        periodo_inicio=datetime.date(2026, 1, 1),
        periodo_fin=datetime.date(2026, 1, 31),
        fecha_corte=datetime.date(2026, 1, 31),
        avance_reportado=35,
    )

    datos = precargar(proyecto, Periodicidad.MENSUAL, datetime.date(2026, 2, 10))

    assert datos["avance_reportado"] == Decimal("35.00")


def test_precargar_sin_seguimiento_anterior_devuelve_cero():
    proyecto = ProyectoFactory()
    datos = precargar(proyecto, Periodicidad.MENSUAL, datetime.date(2026, 1, 10))
    assert datos["avance_reportado"] == Decimal("0")


# --- publicar --------------------------------------------------------------------


def test_publicar_con_semaforo_distinto_del_calculado_sin_justificacion_falla():
    proyecto = ProyectoFactory()
    HitoFactory(proyecto=proyecto, estado=EstadoHito.INCUMPLIDO)  # fuerza calculado=ROJO
    seguimiento = SeguimientoFactory(
        proyecto=proyecto, semaforo=Semaforo.VERDE, justificacion_semaforo=""
    )
    with pytest.raises(ValidationError):
        publicar(seguimiento, UsuarioFactory())


def test_publicar_con_justificacion_funciona_aunque_el_semaforo_difiera():
    proyecto = ProyectoFactory()
    HitoFactory(proyecto=proyecto, estado=EstadoHito.INCUMPLIDO)  # fuerza calculado=ROJO
    seguimiento = SeguimientoFactory(
        proyecto=proyecto,
        semaforo=Semaforo.VERDE,
        justificacion_semaforo="El atraso es solo documental, el trabajo real va a tiempo.",
    )
    publicar(seguimiento, UsuarioFactory())
    seguimiento.refresh_from_db()
    assert seguimiento.estado == EstadoSeguimiento.PUBLICADO
    assert seguimiento.semaforo_calculado == Semaforo.ROJO


def test_publicar_actualiza_avance_y_semaforo_del_proyecto():
    proyecto = ProyectoFactory(avance_reportado=0)
    seguimiento = SeguimientoFactory(
        proyecto=proyecto,
        avance_reportado=42,
        semaforo=Semaforo.AMARILLO,
        justificacion_semaforo="Justificación de prueba.",
    )
    publicar(seguimiento, UsuarioFactory())
    proyecto.refresh_from_db()
    assert proyecto.avance_reportado == Decimal("42.00")
    assert proyecto.semaforo == Semaforo.AMARILLO


def test_publicar_congela_los_cuatro_campos_calculados():
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 12, 31)
    )
    RegistroEjecucionFactory(
        proyecto=proyecto,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        horas=10,
        valor_hora_aplicado=50_000,
        periodo_inicio=datetime.date(2026, 1, 5),
        periodo_fin=datetime.date(2026, 1, 5),
    )
    seguimiento = SeguimientoFactory(
        proyecto=proyecto,
        periodicidad=Periodicidad.MENSUAL,
        periodo_inicio=datetime.date(2026, 1, 1),
        periodo_fin=datetime.date(2026, 1, 31),
        fecha_corte=datetime.date(2026, 1, 31),
        justificacion_semaforo="Justificación de prueba.",
    )
    publicar(seguimiento, UsuarioFactory())
    seguimiento.refresh_from_db()
    assert seguimiento.horas_periodo == Decimal("10.00")
    assert seguimiento.costo_periodo == Decimal("500000.00")
    assert seguimiento.horas_acumuladas == Decimal("10.00")
    assert seguimiento.costo_acumulado == Decimal("500000.00")


def test_publicar_un_seguimiento_ya_publicado_falla():
    seguimiento = SeguimientoFactory(
        estado=EstadoSeguimiento.PUBLICADO, justificacion_semaforo="x"
    )
    with pytest.raises(ErrorConflicto):
        publicar(seguimiento, UsuarioFactory())


# --- reabrir ---------------------------------------------------------------------


def test_reabrir_un_publicado_lo_deja_en_borrador():
    seguimiento = SeguimientoFactory(
        estado=EstadoSeguimiento.PUBLICADO,
        publicado_en=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        publicado_por=UsuarioFactory(),
    )
    reabrir(seguimiento, UsuarioFactory())
    seguimiento.refresh_from_db()
    assert seguimiento.estado == EstadoSeguimiento.BORRADOR
    assert seguimiento.publicado_en is None
    assert seguimiento.publicado_por is None


def test_reabrir_un_borrador_falla():
    seguimiento = SeguimientoFactory(estado=EstadoSeguimiento.BORRADOR)
    with pytest.raises(ErrorConflicto):
        reabrir(seguimiento, UsuarioFactory())


# --- marcar_compromisos_vencidos --------------------------------------------------


def test_marcar_compromisos_vencidos_solo_afecta_abiertos_con_fecha_pasada():
    ayer = datetime.date.today() - datetime.timedelta(days=1)
    manana = datetime.date.today() + datetime.timedelta(days=1)

    vencido = CompromisoSeguimientoFactory(
        fecha_compromiso=ayer, estado=EstadoCompromiso.ABIERTO, descripcion="vencido"
    )
    vigente = CompromisoSeguimientoFactory(
        fecha_compromiso=manana, estado=EstadoCompromiso.ABIERTO, descripcion="vigente"
    )
    ya_cumplido = CompromisoSeguimientoFactory(
        fecha_compromiso=ayer, estado=EstadoCompromiso.CUMPLIDO, descripcion="cumplido"
    )

    total = marcar_compromisos_vencidos()

    vencido.refresh_from_db()
    vigente.refresh_from_db()
    ya_cumplido.refresh_from_db()
    assert total == 1
    assert vencido.estado == EstadoCompromiso.VENCIDO
    assert vigente.estado == EstadoCompromiso.ABIERTO
    assert ya_cumplido.estado == EstadoCompromiso.CUMPLIDO


def test_esta_vencido_property():
    ayer = datetime.date.today() - datetime.timedelta(days=1)
    compromiso = CompromisoSeguimiento(fecha_compromiso=ayer, estado=EstadoCompromiso.ABIERTO)
    assert compromiso.esta_vencido is True
