import datetime

import pytest

from apps.core.choices import Periodicidad
from apps.core.periodos import dias_habiles, normalizar_periodo, periodos_entre


def test_normalizar_diaria():
    inicio, fin = normalizar_periodo(Periodicidad.DIARIA, datetime.date(2026, 3, 15))
    assert inicio == fin == datetime.date(2026, 3, 15)


def test_normalizar_semanal_cruza_de_mes():
    # 2026-01-29 es jueves; la semana (lunes a domingo) cruza a febrero.
    inicio, fin = normalizar_periodo(Periodicidad.SEMANAL, datetime.date(2026, 1, 29))
    assert inicio == datetime.date(2026, 1, 26)
    assert fin == datetime.date(2026, 2, 1)


def test_normalizar_mensual_febrero_no_bisiesto():
    inicio, fin = normalizar_periodo(Periodicidad.MENSUAL, datetime.date(2026, 2, 10))
    assert inicio == datetime.date(2026, 2, 1)
    assert fin == datetime.date(2026, 2, 28)


def test_normalizar_semanal_cruza_fin_de_anio():
    # 2026-12-31 es jueves; la semana cruza a enero de 2027.
    inicio, fin = normalizar_periodo(Periodicidad.SEMANAL, datetime.date(2026, 12, 31))
    assert inicio == datetime.date(2026, 12, 28)
    assert fin == datetime.date(2027, 1, 3)


def test_periodicidad_desconocida_lanza_value_error():
    with pytest.raises(ValueError):
        normalizar_periodo("ANUAL", datetime.date(2026, 1, 1))


def test_periodos_entre_mensual_cruza_de_anio():
    periodos = periodos_entre(
        Periodicidad.MENSUAL, datetime.date(2026, 11, 15), datetime.date(2027, 1, 15)
    )
    assert periodos[0] == (datetime.date(2026, 11, 1), datetime.date(2026, 11, 30))
    assert periodos[-1] == (datetime.date(2027, 1, 1), datetime.date(2027, 1, 31))
    assert len(periodos) == 3


def test_periodos_entre_rango_invertido_da_lista_vacia():
    periodos = periodos_entre(
        Periodicidad.DIARIA, datetime.date(2026, 2, 1), datetime.date(2026, 1, 1)
    )
    assert periodos == []


def test_dias_habiles_una_semana_completa():
    assert dias_habiles(datetime.date(2026, 1, 26), datetime.date(2026, 2, 1)) == 5


def test_dias_habiles_rango_invertido_da_cero():
    assert dias_habiles(datetime.date(2026, 2, 1), datetime.date(2026, 1, 1)) == 0
