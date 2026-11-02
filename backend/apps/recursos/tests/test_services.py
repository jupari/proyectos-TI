import datetime
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import ErrorReglaNegocio
from apps.proyectos.tests.factories import ProyectoFactory

from ..models import AsignacionRecurso, TarifaRecurso
from ..services import (
    calcular_costo_planeado,
    carga_recurso,
    validar_asignacion,
    validar_vigencias,
    valor_hora_vigente,
)
from .factories import AsignacionRecursoFactory, RecursoFactory, TarifaRecursoFactory

pytestmark = pytest.mark.django_db


# --- valor_hora_vigente ------------------------------------------------------


def test_valor_hora_vigente_usa_la_tarifa_cuyo_rango_contiene_la_fecha():
    recurso = RecursoFactory()
    TarifaRecursoFactory(
        recurso=recurso,
        valor_hora=50_000,
        vigente_desde=datetime.date(2026, 1, 1),
        vigente_hasta=datetime.date(2026, 3, 31),
    )

    assert valor_hora_vigente(recurso, datetime.date(2026, 2, 15)) == 50_000


def test_valor_hora_vigente_borde_exacto_vigente_desde_y_vigente_hasta():
    recurso = RecursoFactory()
    tarifa = TarifaRecursoFactory(
        recurso=recurso,
        valor_hora=60_000,
        vigente_desde=datetime.date(2026, 1, 1),
        vigente_hasta=datetime.date(2026, 3, 31),
    )

    assert valor_hora_vigente(recurso, tarifa.vigente_desde) == 60_000
    assert valor_hora_vigente(recurso, tarifa.vigente_hasta) == 60_000
    with pytest.raises(ErrorReglaNegocio):
        valor_hora_vigente(recurso, tarifa.vigente_hasta + datetime.timedelta(days=1))


def test_valor_hora_vigente_sin_fin_cubre_cualquier_fecha_posterior():
    recurso = RecursoFactory()
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=70_000, vigente_desde=datetime.date(2026, 1, 1)
    )

    assert valor_hora_vigente(recurso, datetime.date(2030, 1, 1)) == 70_000


def test_valor_hora_vigente_cae_al_perfil_si_no_hay_tarifa():
    from apps.catalogos.tests.factories import PerfilRecursoFactory

    perfil = PerfilRecursoFactory(tarifa_hora_referencia=45_000)
    recurso = RecursoFactory(perfil=perfil)

    assert valor_hora_vigente(recurso, datetime.date(2026, 1, 1)) == 45_000


def test_valor_hora_vigente_sin_tarifa_ni_perfil_lanza_error_accionable():
    recurso = RecursoFactory(perfil=None)

    with pytest.raises(ErrorReglaNegocio) as excinfo:
        valor_hora_vigente(recurso, datetime.date(2026, 1, 1))

    assert recurso.nombre in str(excinfo.value)


# --- validar_vigencias -------------------------------------------------------


def test_crear_tarifa_sin_fin_cierra_la_anterior_automaticamente():
    recurso = RecursoFactory()
    TarifaRecursoFactory(
        recurso=recurso, valor_hora=50_000, vigente_desde=datetime.date(2026, 1, 1)
    )
    nueva = TarifaRecurso(
        recurso=recurso, valor_hora=55_000, moneda="COP", vigente_desde=datetime.date(2026, 6, 1)
    )

    avisos = validar_vigencias(recurso, nueva)
    nueva.save()

    anterior = recurso.tarifas.get(valor_hora=50_000)
    assert anterior.vigente_hasta == datetime.date(2026, 5, 31)
    assert avisos  # trae el aviso de qué tarifa se cerró
    # no queda ningún hueco ni solapamiento tras el cierre automático
    assert not recurso.tarifas.filter(vigente_hasta__isnull=True).exclude(pk=nueva.pk).exists()


def test_tarifa_con_vigencia_que_solapa_otra_cerrada_lanza_error():
    recurso = RecursoFactory()
    TarifaRecursoFactory(
        recurso=recurso,
        valor_hora=50_000,
        vigente_desde=datetime.date(2026, 1, 1),
        vigente_hasta=datetime.date(2026, 6, 30),
    )
    nueva = TarifaRecurso(
        recurso=recurso,
        valor_hora=55_000,
        moneda="COP",
        vigente_desde=datetime.date(2026, 5, 1),
        vigente_hasta=datetime.date(2026, 12, 31),
    )

    with pytest.raises(ErrorReglaNegocio):
        validar_vigencias(recurso, nueva)


# --- calcular_costo_planeado -------------------------------------------------


def test_calcular_costo_planeado():
    asignacion = AsignacionRecursoFactory(horas_planeadas=100, valor_hora_plan=50_000)
    assert calcular_costo_planeado(asignacion) == Decimal("5000000")


# --- validar_asignacion ------------------------------------------------------


def test_asignacion_fuera_de_fechas_del_proyecto_lanza_validationerror_400():
    proyecto = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 6, 30)
    )
    recurso = RecursoFactory()
    asignacion = AsignacionRecurso(
        proyecto=proyecto,
        recurso=recurso,
        rol_en_proyecto="Analista",
        fecha_desde=datetime.date(2025, 12, 1),
        fecha_hasta=datetime.date(2026, 2, 1),
        porcentaje_dedicacion=50,
        horas_planeadas=100,
        valor_hora_plan=50_000,
    )

    with pytest.raises(ValidationError):
        validar_asignacion(asignacion)


def test_asignacion_de_recurso_inactivo_lanza_error():
    proyecto = ProyectoFactory()
    recurso = RecursoFactory(activo=False)
    asignacion = AsignacionRecurso(
        proyecto=proyecto,
        recurso=recurso,
        rol_en_proyecto="Analista",
        fecha_desde=proyecto.fecha_inicio_plan,
        fecha_hasta=proyecto.fecha_inicio_plan + datetime.timedelta(days=30),
        porcentaje_dedicacion=50,
        horas_planeadas=100,
        valor_hora_plan=50_000,
    )

    with pytest.raises(ErrorReglaNegocio):
        validar_asignacion(asignacion)


def test_asignacion_de_recurso_retirado_antes_de_fecha_hasta_lanza_error():
    proyecto = ProyectoFactory()
    recurso = RecursoFactory(fecha_retiro=proyecto.fecha_inicio_plan)
    asignacion = AsignacionRecurso(
        proyecto=proyecto,
        recurso=recurso,
        rol_en_proyecto="Analista",
        fecha_desde=proyecto.fecha_inicio_plan,
        fecha_hasta=proyecto.fecha_inicio_plan + datetime.timedelta(days=30),
        porcentaje_dedicacion=50,
        horas_planeadas=100,
        valor_hora_plan=50_000,
    )

    with pytest.raises(ErrorReglaNegocio):
        validar_asignacion(asignacion)


def test_sobreasignacion_en_el_mismo_mes_devuelve_advertencia_no_bloquea():
    recurso = RecursoFactory()
    proyecto_1 = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 12, 31)
    )
    proyecto_2 = ProyectoFactory(
        fecha_inicio_plan=datetime.date(2026, 1, 1), fecha_fin_plan=datetime.date(2026, 12, 31)
    )
    AsignacionRecursoFactory(
        proyecto=proyecto_1,
        recurso=recurso,
        fecha_desde=datetime.date(2026, 3, 1),
        fecha_hasta=datetime.date(2026, 3, 31),
        porcentaje_dedicacion=70,
    )
    nueva = AsignacionRecurso(
        proyecto=proyecto_2,
        recurso=recurso,
        rol_en_proyecto="Analista",
        fecha_desde=datetime.date(2026, 3, 1),
        fecha_hasta=datetime.date(2026, 3, 31),
        porcentaje_dedicacion=60,
        horas_planeadas=100,
        valor_hora_plan=50_000,
    )

    advertencias = validar_asignacion(nueva)

    assert advertencias
    assert "130" in advertencias[0] or "2026-03" in advertencias[0]


# --- carga_recurso ------------------------------------------------------------


def test_carga_recurso_reparte_las_horas_de_una_asignacion_que_cruza_meses():
    recurso = RecursoFactory(capacidad_horas_mes=160)
    # 01/02 a 31/03: 28 días de febrero + 31 de marzo = 59 días totales.
    AsignacionRecursoFactory(
        recurso=recurso,
        fecha_desde=datetime.date(2026, 2, 1),
        fecha_hasta=datetime.date(2026, 3, 31),
        horas_planeadas=590,
    )

    carga = carga_recurso(recurso, datetime.date(2026, 2, 1), datetime.date(2026, 3, 31))

    assert len(carga) == 2
    febrero, marzo = carga
    assert febrero["anio"] == 2026 and febrero["mes"] == 2
    assert febrero["horas_planeadas"] == Decimal("280")
    assert marzo["horas_planeadas"] == Decimal("310")
    assert febrero["horas_planeadas"] + marzo["horas_planeadas"] == Decimal("590")
