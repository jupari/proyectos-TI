import datetime
from unittest.mock import MagicMock, patch

import pytest

from apps.ejecucion.services import personas_jira_sin_mapear
from apps.recursos.tests.factories import RecursoFactory

pytestmark = pytest.mark.django_db

RUTA_CLIENTE = "apps.ejecucion.integraciones.jira_tempo.ClienteJiraTempo"


def _worklog(account_id):
    return {"author": {"accountId": account_id}}


def _cliente_mock(worklogs, correos_por_cuenta):
    cliente = MagicMock()
    cliente.obtener_worklogs.return_value = worklogs
    cliente.resolver_correo_usuario.side_effect = lambda account_id: correos_por_cuenta[account_id]
    return cliente


def test_cuenta_sin_correo_ni_mapeo_aparece_en_la_lista():
    cliente = _cliente_mock(
        [_worklog("acc-1"), _worklog("acc-1")],
        {"acc-1": {"correo": None, "nombre": "Alguien Oculto"}},
    )

    with patch(RUTA_CLIENTE, return_value=cliente):
        resultado = personas_jira_sin_mapear(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resultado == [{"jira_account_id": "acc-1", "nombre": "Alguien Oculto", "worklogs": 2}]


def test_cuenta_ya_mapeada_no_aparece():
    RecursoFactory(jira_account_id="acc-1")
    cliente = _cliente_mock(
        [_worklog("acc-1")], {"acc-1": {"correo": None, "nombre": "Alguien Oculto"}}
    )

    with patch(RUTA_CLIENTE, return_value=cliente):
        resultado = personas_jira_sin_mapear(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resultado == []


def test_cuenta_con_correo_que_coincide_con_un_recurso_no_aparece():
    RecursoFactory(email="ana@empresa.com")
    cliente = _cliente_mock(
        [_worklog("acc-1")], {"acc-1": {"correo": "ana@empresa.com", "nombre": "Ana"}}
    )

    with patch(RUTA_CLIENTE, return_value=cliente):
        resultado = personas_jira_sin_mapear(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resultado == []


def test_sin_worklogs_devuelve_lista_vacia():
    cliente = _cliente_mock([], {})

    with patch(RUTA_CLIENTE, return_value=cliente):
        resultado = personas_jira_sin_mapear(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resultado == []


def test_error_de_conexion_devuelve_lista_vacia_sin_lanzar():
    from apps.ejecucion.integraciones.jira_tempo import ErrorIntegracionJira

    cliente = MagicMock()
    cliente.obtener_worklogs.side_effect = ErrorIntegracionJira("no se pudo conectar")

    with patch(RUTA_CLIENTE, return_value=cliente):
        resultado = personas_jira_sin_mapear(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resultado == []
