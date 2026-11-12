"""Prueba de concurrencia real (fase 11 §11.1.3): dos creaciones simultáneas
de proyecto no deben producir el mismo código. Se usa `transaction=True` para
que cada hilo vea una conexión y una transacción de verdad (con el
`django_db` normal, pytest-django envuelve todo en una sola transacción que
se revierte al final, y los hilos no verían los commits de los demás).

Esta prueba encontró un error real: `generar_codigo_proyecto` bloquea la
última fila con el prefijo del año —si existe alguna—, pero Postgres no
vuelve a evaluar ese `SELECT ... FOR UPDATE ... ORDER BY ... LIMIT 1` tras
desbloquearse, así que dos transacciones concurrentes pueden calcular el
mismo código aunque exista una fila que "bloquear". El arreglo (reintentar
en `ProyectoEscrituraSerializer.create` si `IntegrityError` por el código
duplicado) hace que todas las creaciones concurrentes terminen con éxito y
con códigos distintos, en vez de que solo una gane y las demás reciban un
500."""

import datetime
import threading

import pytest
from django.db import connection

from apps.catalogos.tests.factories import AreaFactory
from apps.proyectos.serializers import ProyectoEscrituraSerializer

from .factories import ProyectoFactory


def _datos_proyecto(area_id, gerente_id):
    return {
        "nombre": "Proyecto concurrente",
        "descripcion": "",
        "objetivo": "",
        "area_solicitante": area_id,
        "gerente": gerente_id,
        "prioridad": "MEDIA",
        "fecha_inicio_plan": "2026-01-01",
        "fecha_fin_plan": "2026-12-31",
        "moneda": "COP",
        "presupuesto_horas": "100.00",
        "presupuesto_dinero": "1000000.00",
        "observaciones": "",
    }


@pytest.mark.django_db(transaction=True)
def test_dos_creaciones_simultaneas_de_proyecto_no_duplican_codigo():
    anio = datetime.date.today().year
    # Un proyecto ya existente: `generar_codigo_proyecto` solo puede bloquear
    # una fila que exista (ver Evidencia de la fase sobre el límite real de
    # `select_for_update` cuando todavía no hay ninguna fila que bloquear).
    proyecto_previo = ProyectoFactory(codigo=f"PRY-{anio}-001")
    area = AreaFactory()
    gerente = proyecto_previo.gerente

    resultados = []
    errores = []
    bloqueo = threading.Lock()

    def crear():
        try:
            serializer = ProyectoEscrituraSerializer(data=_datos_proyecto(area.id, gerente.id))
            serializer.is_valid(raise_exception=True)
            instancia = serializer.save()
            with bloqueo:
                resultados.append(instancia.codigo)
        except Exception as exc:  # noqa: BLE001 - se reporta tal cual para el assert
            with bloqueo:
                errores.append(exc)
        finally:
            connection.close()

    hilos = [threading.Thread(target=crear) for _ in range(5)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert not errores, f"no se esperaban errores tras el reintento: {errores}"
    assert len(resultados) == 5
    assert len(resultados) == len(set(resultados)), (
        f"se generaron códigos duplicados: {resultados}"
    )
