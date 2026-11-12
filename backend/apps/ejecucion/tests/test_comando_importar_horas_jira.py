import datetime
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.ejecucion.models import RegistroEjecucion
from apps.proyectos.tests.factories import ProyectoFactory
from apps.recursos.tests.factories import RecursoFactory, TarifaRecursoFactory
from apps.tareas.tests.factories import TareaFactory

pytestmark = pytest.mark.django_db

RUTA_CLIENTE = "apps.ejecucion.integraciones.jira_tempo.ClienteJiraTempo"


@pytest.fixture(autouse=True)
def _jira_configurado(settings):
    settings.JIRA_BASE_URL = "https://empresa.atlassian.net"
    settings.JIRA_EMAIL = "admin@empresa.com"
    settings.JIRA_API_TOKEN = "token-jira-de-prueba"  # noqa: S105 (valor de prueba)
    settings.TEMPO_API_TOKEN = "token-tempo-de-prueba"  # noqa: S105 (valor de prueba)


def _cliente_con_un_worklog():
    cliente = MagicMock()
    cliente.obtener_worklogs.return_value = [
        {
            "tempoWorklogId": 777,
            "issue": {"id": "10001"},
            "startDate": "2026-03-10",
            "timeSpentSeconds": 28800,
            "description": "Trabajo en Jira",
            "author": {"accountId": "acc-1"},
        }
    ]
    cliente.resolver_claves_issue.return_value = {"10001": "PROY-1"}
    cliente.resolver_correo_usuario.return_value = "ana@empresa.com"
    return cliente


def test_variables_de_entorno_faltantes_falla_de_entrada(settings):
    settings.JIRA_BASE_URL = ""
    settings.TEMPO_API_TOKEN = ""

    with pytest.raises(CommandError, match="JIRA_BASE_URL"):
        call_command("importar_horas_jira", desde="2026-03-01", hasta="2026-03-31")


def test_fecha_invalida_falla(settings):
    with pytest.raises(CommandError):
        call_command("importar_horas_jira", desde="no-es-una-fecha", hasta="2026-03-31")


def test_hasta_antes_de_desde_falla():
    with pytest.raises(CommandError, match="--hasta"):
        call_command("importar_horas_jira", desde="2026-03-31", hasta="2026-03-01")


def test_importa_y_reporta_el_resumen():
    proyecto = ProyectoFactory(clave_jira="PROY")
    recurso = RecursoFactory(email="ana@empresa.com")
    TarifaRecursoFactory(recurso=recurso, valor_hora=70000, vigente_desde=datetime.date(2026, 1, 1))
    TareaFactory(proyecto=proyecto, clave_jira="PROY-1")

    salida = StringIO()
    with patch(RUTA_CLIENTE, return_value=_cliente_con_un_worklog()):
        call_command(
            "importar_horas_jira", desde="2026-03-01", hasta="2026-03-31", stdout=salida
        )

    assert "Creados: 1" in salida.getvalue()
    assert RegistroEjecucion.objects.filter(id_externo="777").exists()


def test_dry_run_no_escribe_nada():
    proyecto = ProyectoFactory(clave_jira="PROY")
    recurso = RecursoFactory(email="ana@empresa.com")
    TarifaRecursoFactory(recurso=recurso, valor_hora=70000, vigente_desde=datetime.date(2026, 1, 1))
    TareaFactory(proyecto=proyecto, clave_jira="PROY-1")

    salida = StringIO()
    with patch(RUTA_CLIENTE, return_value=_cliente_con_un_worklog()):
        call_command(
            "importar_horas_jira",
            desde="2026-03-01",
            hasta="2026-03-31",
            dry_run=True,
            stdout=salida,
        )

    assert "no se escribió nada" in salida.getvalue()
    assert not RegistroEjecucion.objects.exists()
