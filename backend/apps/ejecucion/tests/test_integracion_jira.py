import datetime

import pytest
import responses

from apps.ejecucion.integraciones.jira_tempo import ClienteJiraTempo, ErrorIntegracionJira

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _jira_configurado(settings):
    settings.JIRA_BASE_URL = "https://empresa.atlassian.net"
    settings.JIRA_EMAIL = "admin@empresa.com"
    settings.JIRA_API_TOKEN = "token-jira-de-prueba"  # noqa: S105 (valor de prueba)
    settings.TEMPO_API_TOKEN = "token-tempo-de-prueba"  # noqa: S105 (valor de prueba)


def test_variables_de_entorno_faltantes_da_error_claro(settings):
    settings.JIRA_BASE_URL = ""
    settings.TEMPO_API_TOKEN = ""

    with pytest.raises(ErrorIntegracionJira) as excinfo:
        ClienteJiraTempo().listar_proyectos()

    assert "JIRA_BASE_URL" in str(excinfo.value)
    assert "TEMPO_API_TOKEN" in str(excinfo.value)


@responses.activate
def test_listar_proyectos_pagina_correctamente():
    responses.add(
        responses.GET,
        "https://empresa.atlassian.net/rest/api/3/project/search",
        json={
            "values": [{"key": "PROY", "name": "Proyecto demo"}],
            "isLast": False,
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://empresa.atlassian.net/rest/api/3/project/search",
        json={
            "values": [{"key": "OTRO", "name": "Otro proyecto"}],
            "isLast": True,
        },
        status=200,
    )

    proyectos = ClienteJiraTempo().listar_proyectos()

    assert proyectos == [
        {"clave": "PROY", "nombre": "Proyecto demo"},
        {"clave": "OTRO", "nombre": "Otro proyecto"},
    ]


@responses.activate
def test_obtener_worklogs_pagina_por_metadata_next():
    responses.add(
        responses.GET,
        "https://api.tempo.io/4/worklogs",
        json={
            "results": [{"tempoWorklogId": 1}],
            "metadata": {"next": "https://api.tempo.io/4/worklogs?offset=50"},
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://api.tempo.io/4/worklogs",
        json={"results": [{"tempoWorklogId": 2}], "metadata": {}},
        status=200,
    )

    worklogs = ClienteJiraTempo().obtener_worklogs(
        datetime.date(2026, 1, 1), datetime.date(2026, 1, 31)
    )

    assert [w["tempoWorklogId"] for w in worklogs] == [1, 2]


@responses.activate
def test_resolver_claves_issue_un_solo_request_para_varios_ids():
    responses.add(
        responses.POST,
        "https://empresa.atlassian.net/rest/api/3/search/jql",
        json={"issues": [{"id": "10001", "key": "PROY-1"}, {"id": "10002", "key": "PROY-2"}]},
        status=200,
    )

    claves = ClienteJiraTempo().resolver_claves_issue(["10001", "10002"])

    assert claves == {"10001": "PROY-1", "10002": "PROY-2"}
    assert len(responses.calls) == 1


@responses.activate
def test_resolver_claves_issue_usa_post_y_pagina_por_lotes():
    """Un `GET` con muchos ids revienta el límite de longitud de URL de
    Jira (414, confirmado contra el Jira real); por eso debe ser `POST` y,
    si hay más de `TAMANO_LOTE_ISSUES`, en varias llamadas."""
    from apps.ejecucion.integraciones.jira_tempo import TAMANO_LOTE_ISSUES

    ids = [str(10000 + i) for i in range(TAMANO_LOTE_ISSUES + 1)]
    responses.add(
        responses.POST,
        "https://empresa.atlassian.net/rest/api/3/search/jql",
        json={"issues": [{"id": i, "key": f"PROY-{i}"} for i in ids[:TAMANO_LOTE_ISSUES]]},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://empresa.atlassian.net/rest/api/3/search/jql",
        json={"issues": [{"id": ids[-1], "key": f"PROY-{ids[-1]}"}]},
        status=200,
    )

    claves = ClienteJiraTempo().resolver_claves_issue(ids)

    assert len(claves) == len(ids)
    assert len(responses.calls) == 2


@responses.activate
def test_resolver_correo_usuario_cachea_en_memoria():
    responses.add(
        responses.GET,
        "https://empresa.atlassian.net/rest/api/3/user",
        json={"accountId": "abc", "emailAddress": "ana@empresa.com", "displayName": "Ana Ríos"},
        status=200,
    )

    cliente = ClienteJiraTempo()
    primero = cliente.resolver_correo_usuario("abc")
    segundo = cliente.resolver_correo_usuario("abc")

    esperado = {"correo": "ana@empresa.com", "nombre": "Ana Ríos"}
    assert primero == segundo == esperado
    assert len(responses.calls) == 1


@responses.activate
def test_error_http_se_traduce_a_error_integracion_jira():
    responses.add(
        responses.GET,
        "https://empresa.atlassian.net/rest/api/3/project/search",
        json={"errorMessages": ["No autorizado"]},
        status=401,
    )

    with pytest.raises(ErrorIntegracionJira):
        ClienteJiraTempo().listar_proyectos()
