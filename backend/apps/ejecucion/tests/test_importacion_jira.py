import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.core.choices import EstadoAprobacion, OrigenRegistro
from apps.ejecucion.models import ConfiguracionImportacionJira, RegistroEjecucion
from apps.ejecucion.services import importar_horas_jira
from apps.ejecucion.tests.factories import RegistroEjecucionFactory
from apps.proyectos.tests.factories import ProyectoFactory
from apps.recursos.tests.factories import RecursoFactory, TarifaRecursoFactory
from apps.tareas.tests.factories import TareaFactory

pytestmark = pytest.mark.django_db

RUTA_CLIENTE = "apps.ejecucion.integraciones.jira_tempo.ClienteJiraTempo"


def _worklog(**overrides):
    base = {
        "tempoWorklogId": 555,
        "issue": {"id": "10001"},
        "startDate": "2026-03-10",
        "timeSpentSeconds": 28800,  # 8 horas
        "description": "Trabajo en Jira",
        "author": {"accountId": "acc-1"},
    }
    base.update(overrides)
    return base


def _cliente_mock(worklogs, *, claves=None, correo="ana@empresa.com", nombre="Ana Pérez"):
    cliente = MagicMock()
    cliente.obtener_worklogs.return_value = worklogs
    cliente.resolver_claves_issue.return_value = claves or {"10001": "PROY-1"}
    cliente.resolver_correo_usuario.return_value = {"correo": correo, "nombre": nombre}
    return cliente


def _preparar_proyecto_recurso_tarea():
    proyecto = ProyectoFactory(clave_jira="PROY")
    recurso = RecursoFactory(email="ana@empresa.com")
    TarifaRecursoFactory(recurso=recurso, valor_hora=70000, vigente_desde=datetime.date(2026, 1, 1))
    tarea = TareaFactory(proyecto=proyecto, clave_jira="PROY-1")
    return proyecto, recurso, tarea


def test_worklog_nuevo_crea_registro_enviado_con_tarifa_congelada():
    proyecto, recurso, tarea = _preparar_proyecto_recurso_tarea()
    cliente = _cliente_mock([_worklog()])

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["creados"] == 1
    registro = RegistroEjecucion.objects.get(origen=OrigenRegistro.JIRA, id_externo="555")
    assert registro.proyecto_id == proyecto.id
    assert registro.tarea_id == tarea.id
    assert registro.recurso_id == recurso.id
    assert registro.estado_aprobacion == EstadoAprobacion.ENVIADO
    assert registro.horas == Decimal("8")
    assert registro.valor_hora_aplicado == Decimal("70000.00")
    assert registro.periodo_inicio == datetime.date(2026, 3, 10)
    assert resumen["detalle"] == [
        {
            "fecha": "2026-03-10",
            "recurso_nombre": recurso.nombre,
            "proyecto_codigo": proyecto.codigo,
            "proyecto_nombre": proyecto.nombre,
            "horas": Decimal("8"),
            "accion": "creado",
        }
    ]


def test_omitido_por_recurso_identifica_a_la_persona_por_nombre_y_correo():
    ProyectoFactory(clave_jira="PROY")
    cliente = _cliente_mock(
        [_worklog()], correo="nadie@empresa.com", nombre="Pedro Pérez"
    )

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    motivo = resumen["omitidos"][0]["motivo"]
    assert "Pedro Pérez" in motivo
    assert "nadie@empresa.com" in motivo


def test_con_auto_aprobar_activado_crea_directo_aprobado():
    proyecto, recurso, tarea = _preparar_proyecto_recurso_tarea()
    config = ConfiguracionImportacionJira.obtener()
    config.auto_aprobar_importados = True
    config.save()
    cliente = _cliente_mock([_worklog()])

    with patch(RUTA_CLIENTE, return_value=cliente):
        importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    registro = RegistroEjecucion.objects.get(origen=OrigenRegistro.JIRA, id_externo="555")
    assert registro.estado_aprobacion == EstadoAprobacion.APROBADO
    assert registro.aprobado_por is None
    assert registro.aprobado_en is not None
    tarea.refresh_from_db()
    assert tarea.horas_ejecutadas == Decimal("8.00")


def test_auto_aprobar_por_corrida_anula_el_interruptor_global():
    """`ConfiguracionImportacionJira` sigue en `False`: el botón de
    /admin/integraciones puede decidir la aprobación solo para esta corrida,
    sin tocar el valor global."""
    _preparar_proyecto_recurso_tarea()
    cliente = _cliente_mock([_worklog()])

    with patch(RUTA_CLIENTE, return_value=cliente):
        importar_horas_jira(
            datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), auto_aprobar=True
        )

    registro = RegistroEjecucion.objects.get(origen=OrigenRegistro.JIRA, id_externo="555")
    assert registro.estado_aprobacion == EstadoAprobacion.APROBADO
    assert ConfiguracionImportacionJira.obtener().auto_aprobar_importados is False


def test_reimportar_mismo_worklog_actualiza_no_duplica():
    _preparar_proyecto_recurso_tarea()
    cliente = _cliente_mock([_worklog(timeSpentSeconds=14400)])  # 4 horas

    with patch(RUTA_CLIENTE, return_value=cliente):
        importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    cliente2 = _cliente_mock([_worklog(timeSpentSeconds=28800)])  # 8 horas
    with patch(RUTA_CLIENTE, return_value=cliente2):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["actualizados"] == 1
    filtro = RegistroEjecucion.objects.filter(origen=OrigenRegistro.JIRA, id_externo="555")
    assert filtro.count() == 1
    registro = filtro.get()
    assert registro.horas == Decimal("8")


def test_dos_worklogs_mismo_dia_y_tarea_suman_horas_en_un_registro():
    """Tempo permite varias entradas de tiempo el mismo día sobre la misma
    tarea (p. ej. mañana y tarde); el modelo guarda un registro por día/
    tarea/recurso, así que deben sumarse en uno solo en vez de chocar contra
    `registroejecucion_unico`."""
    _preparar_proyecto_recurso_tarea()
    cliente = _cliente_mock(
        [
            _worklog(tempoWorklogId=555, timeSpentSeconds=14400),  # 4 horas
            _worklog(tempoWorklogId=556, timeSpentSeconds=10800),  # 3 horas
        ]
    )

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["creados"] == 1
    assert resumen["errores"] == []
    registro = RegistroEjecucion.objects.get(origen=OrigenRegistro.JIRA, id_externo="555,556")
    assert registro.horas == Decimal("7")
    assert resumen["detalle"] == [
        {
            "fecha": "2026-03-10",
            "recurso_nombre": registro.recurso.nombre,
            "proyecto_codigo": registro.proyecto.codigo,
            "proyecto_nombre": registro.proyecto.nombre,
            "horas": Decimal("7"),
            "accion": "creado",
        }
    ]


def test_reimportar_grupo_de_dos_worklogs_no_duplica_horas():
    """Una segunda corrida sobre el mismo par de worklogs recalcula la suma
    desde cero (no la acumula de nuevo) y actualiza el registro existente en
    vez de duplicarlo."""
    _preparar_proyecto_recurso_tarea()
    worklogs = [
        _worklog(tempoWorklogId=555, timeSpentSeconds=14400),  # 4 horas
        _worklog(tempoWorklogId=556, timeSpentSeconds=10800),  # 3 horas
    ]

    with patch(RUTA_CLIENTE, return_value=_cliente_mock(worklogs)):
        importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))
    with patch(RUTA_CLIENTE, return_value=_cliente_mock(worklogs)):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["actualizados"] == 1
    assert RegistroEjecucion.objects.filter(origen=OrigenRegistro.JIRA).count() == 1
    registro = RegistroEjecucion.objects.get(origen=OrigenRegistro.JIRA)
    assert registro.horas == Decimal("7")


def test_reimportar_worklog_ya_aprobado_no_lo_modifica():
    proyecto, recurso, tarea = _preparar_proyecto_recurso_tarea()
    RegistroEjecucionFactory(
        proyecto=proyecto,
        recurso=recurso,
        tarea=tarea,
        periodicidad="DIARIA",
        periodo_inicio=datetime.date(2026, 3, 10),
        periodo_fin=datetime.date(2026, 3, 10),
        horas=5,
        valor_hora_aplicado=70000,
        origen=OrigenRegistro.JIRA,
        id_externo="555",
        estado_aprobacion=EstadoAprobacion.APROBADO,
    )
    cliente = _cliente_mock([_worklog(timeSpentSeconds=28800)])

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["creados"] == 0
    assert resumen["actualizados"] == 0
    assert len(resumen["omitidos"]) == 1
    registro = RegistroEjecucion.objects.get(origen=OrigenRegistro.JIRA, id_externo="555")
    assert registro.horas == Decimal("5")


def test_worklog_de_proyecto_no_mapeado_se_omite():
    RecursoFactory(email="ana@empresa.com")
    cliente = _cliente_mock([_worklog()])

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["creados"] == 0
    assert len(resumen["omitidos"]) == 1
    assert "no está mapeado" in resumen["omitidos"][0]["motivo"]
    assert not RegistroEjecucion.objects.exists()


def test_worklog_resuelve_por_jira_account_id_si_no_hay_correo_visible():
    """La mayoría de las cuentas de Jira no expone `emailAddress` por la API
    (visibilidad de cuenta de cada persona); para esos casos el admin deja
    un mapeo manual en `Recurso.jira_account_id` desde /admin/integraciones,
    y la importación debe usarlo como respaldo."""
    proyecto = ProyectoFactory(clave_jira="PROY")
    recurso = RecursoFactory(email=None, jira_account_id="acc-1")
    TarifaRecursoFactory(recurso=recurso, valor_hora=70000, vigente_desde=datetime.date(2026, 1, 1))
    TareaFactory(proyecto=proyecto, clave_jira="PROY-1")
    cliente = _cliente_mock([_worklog()], correo=None, nombre="Alguien Oculto")

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["creados"] == 1
    registro = RegistroEjecucion.objects.get(origen=OrigenRegistro.JIRA)
    assert registro.recurso_id == recurso.id


def test_worklog_de_recurso_sin_correo_coincidente_se_omite():
    ProyectoFactory(clave_jira="PROY")
    cliente = _cliente_mock([_worklog()], correo="nadie@empresa.com")

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["creados"] == 0
    assert len(resumen["omitidos"]) == 1
    assert "recurso" in resumen["omitidos"][0]["motivo"]


def test_worklog_que_solapa_con_registro_manual_se_reporta_como_error():
    proyecto, recurso, _tarea = _preparar_proyecto_recurso_tarea()
    RegistroEjecucionFactory(
        proyecto=proyecto,
        recurso=recurso,
        tarea=None,
        periodicidad="DIARIA",
        periodo_inicio=datetime.date(2026, 3, 10),
        periodo_fin=datetime.date(2026, 3, 10),
        horas=3,
        valor_hora_aplicado=70000,
        estado_aprobacion=EstadoAprobacion.ENVIADO,
    )
    cliente = _cliente_mock([_worklog()])

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["creados"] == 0
    assert len(resumen["errores"]) == 1
    assert not RegistroEjecucion.objects.filter(origen=OrigenRegistro.JIRA).exists()


def test_dry_run_no_escribe_nada():
    _preparar_proyecto_recurso_tarea()
    cliente = _cliente_mock([_worklog()])

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(
            datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), dry_run=True
        )

    assert resumen["creados"] == 1
    assert not RegistroEjecucion.objects.exists()


def test_error_de_conexion_se_reporta_sin_interrumpir():
    from apps.ejecucion.integraciones.jira_tempo import ErrorIntegracionJira

    cliente = MagicMock()
    cliente.obtener_worklogs.side_effect = ErrorIntegracionJira("no se pudo conectar")

    with patch(RUTA_CLIENTE, return_value=cliente):
        resumen = importar_horas_jira(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))

    assert resumen["creados"] == 0
    assert len(resumen["errores"]) == 1
