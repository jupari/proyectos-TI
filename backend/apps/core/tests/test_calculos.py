import datetime
from decimal import Decimal

import pytest

from apps.core.calculos import division_segura, meses_entre, prorratear_por_mes


@pytest.mark.parametrize(
    ("numerador", "denominador"),
    [(10, 0), (10, None), (None, 5), (None, 0)],
)
def test_division_segura_devuelve_none(numerador, denominador):
    assert division_segura(numerador, denominador) is None


def test_division_segura_calcula_normal():
    assert division_segura(50, 200) == 0.25


# --- meses_entre (única implementación: antes de la fase 10 había tres) -----------


def test_meses_entre_mismo_mes():
    assert meses_entre(datetime.date(2026, 3, 5), datetime.date(2026, 3, 20)) == [(2026, 3)]


def test_meses_entre_cruza_anio():
    assert meses_entre(datetime.date(2025, 12, 15), datetime.date(2026, 2, 10)) == [
        (2025, 12),
        (2026, 1),
        (2026, 2),
    ]


# --- prorratear_por_mes -------------------------------------------------------------


def test_prorratear_por_mes_reparte_proporcional_a_los_dias():
    # 01/02 a 31/03: 28 días de febrero + 31 de marzo = 59 días totales, 590 horas.
    desde, hasta = datetime.date(2026, 2, 1), datetime.date(2026, 3, 31)
    febrero = prorratear_por_mes(desde, hasta, Decimal("590"), 2026, 2)
    marzo = prorratear_por_mes(desde, hasta, Decimal("590"), 2026, 3)
    assert febrero == Decimal("280")
    assert marzo == Decimal("310")
    assert febrero + marzo == Decimal("590")


def test_prorratear_por_mes_fuera_de_rango_devuelve_cero_del_mismo_tipo():
    desde, hasta = datetime.date(2026, 2, 1), datetime.date(2026, 2, 28)
    resultado = prorratear_por_mes(desde, hasta, Decimal("100"), 2026, 5)
    assert resultado == Decimal("0")
    assert isinstance(resultado, Decimal)


def test_prorratear_por_mes_totalmente_dentro_de_un_mes_devuelve_el_total():
    desde, hasta = datetime.date(2026, 2, 5), datetime.date(2026, 2, 20)
    assert prorratear_por_mes(desde, hasta, Decimal("160"), 2026, 2) == Decimal("160")
