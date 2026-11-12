"""Prueba de concurrencia real (fase 11 §11.1.3): varias creaciones
simultáneas de tarea sobre el mismo proyecto no deben producir el mismo
código. A diferencia de `generar_codigo_proyecto` (que bloquea la última fila
con ese prefijo, que puede no existir todavía), `generar_codigo_tarea`
bloquea la fila del proyecto —que siempre existe— así que esta prueba no
tiene la limitación de "primera fila" que sí tiene la de proyectos."""

import threading

import pytest
from django.db import connection

from apps.tareas.serializers import TareaEscrituraSerializer

from .factories import ProyectoFactory


def _datos_tarea(proyecto_id):
    return {
        "proyecto": proyecto_id,
        "nombre": "Tarea concurrente",
        "descripcion": "",
        "tipo": "TAREA",
        "prioridad": "MEDIA",
        "fecha_inicio_plan": "2026-01-01",
        "fecha_fin_plan": "2026-01-31",
        "horas_estimadas": "8.00",
        "orden": 0,
        "motivo_creacion": "",
    }


@pytest.mark.django_db(transaction=True)
def test_varias_creaciones_simultaneas_de_tarea_no_duplican_codigo():
    proyecto = ProyectoFactory()

    resultados = []
    errores = []
    bloqueo = threading.Lock()

    def crear():
        try:
            serializer = TareaEscrituraSerializer(data=_datos_tarea(proyecto.id))
            serializer.is_valid(raise_exception=True)
            instancia = serializer.save()
            with bloqueo:
                resultados.append(instancia.codigo)
        except Exception as exc:  # noqa: BLE001 - se reporta tal cual para el assert
            with bloqueo:
                errores.append(exc)
        finally:
            connection.close()

    hilos = [threading.Thread(target=crear) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    # El proyecto (que siempre existe) es lo que se bloquea, no la última
    # tarea (que podría no existir aún): las 8 creaciones deben tener éxito,
    # sin errores y sin códigos repetidos.
    assert not errores, f"no se esperaban errores: {errores}"
    assert len(resultados) == 8
    assert len(resultados) == len(set(resultados)), f"códigos duplicados: {resultados}"
