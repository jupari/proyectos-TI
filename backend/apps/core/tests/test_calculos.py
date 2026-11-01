import pytest

from apps.core.calculos import division_segura


@pytest.mark.parametrize(
    ("numerador", "denominador"),
    [(10, 0), (10, None), (None, 5), (None, 0)],
)
def test_division_segura_devuelve_none(numerador, denominador):
    assert division_segura(numerador, denominador) is None


def test_division_segura_calcula_normal():
    assert division_segura(50, 200) == 0.25
