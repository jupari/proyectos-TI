import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.catalogos.models import Area
from apps.catalogos.tests.factories import AreaFactory
from apps.core.pagination import PaginacionEstandar

pytestmark = pytest.mark.django_db

_fabrica_peticiones = APIRequestFactory()


def _peticion(query_string=""):
    return Request(_fabrica_peticiones.get(f"/falso/{query_string}"))


def test_forma_de_la_respuesta_paginada():
    for i in range(5):
        AreaFactory(codigo=f"PAG-{i:02d}")
    queryset = Area.objects.order_by("codigo")

    paginador = PaginacionEstandar()
    pagina = paginador.paginate_queryset(queryset, _peticion())
    respuesta = paginador.get_paginated_response([obj.codigo for obj in pagina])

    assert set(respuesta.data.keys()) == {"count", "next", "previous", "results"}
    assert respuesta.data["count"] == Area.objects.count()


def test_page_size_personalizado_se_respeta():
    for i in range(5):
        AreaFactory(codigo=f"PGS-{i:02d}")
    queryset = Area.objects.order_by("codigo")

    paginador = PaginacionEstandar()
    pagina = paginador.paginate_queryset(queryset, _peticion("?page_size=2"))

    assert len(pagina) == 2


def test_page_size_tiene_tope_de_200():
    paginador = PaginacionEstandar()
    assert paginador.get_page_size(_peticion("?page_size=9999")) == 200
    assert paginador.get_page_size(_peticion("?page_size=50")) == 50
