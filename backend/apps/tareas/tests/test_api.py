import datetime

import pytest
from rest_framework.test import APIClient

from apps.core.choices import EstadoProyecto, EstadoTarea, TipoDependencia
from apps.proyectos.tests.factories import ProyectoFactory
from apps.recursos.tests.factories import AsignacionRecursoFactory, RecursoFactory
from conftest import crear_usuario_con_rol

from .factories import DependenciaTareaFactory, TareaFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente():
    return APIClient()


def _datos_tarea(proyecto, **extra):
    datos = {
        "proyecto": str(proyecto.id),
        "nombre": "Analizar requerimientos",
        "tipo": "TAREA",
        "prioridad": "MEDIA",
        "fecha_inicio_plan": str(proyecto.fecha_inicio_plan),
        "fecha_fin_plan": str(proyecto.fecha_inicio_plan + datetime.timedelta(days=10)),
        "horas_estimadas": "40.00",
    }
    datos.update(extra)
    return datos


# --- permisos de creación ------------------------------------------------------


@pytest.mark.parametrize(
    ("codigo_rol", "esperado"),
    [("ADMIN", 201), ("PMO", 201), ("CONSULTA", 403)],
)
def test_crear_tarea_por_rol(roles, cliente, codigo_rol, esperado):
    proyecto = ProyectoFactory()
    usuario = crear_usuario_con_rol(codigo_rol)
    cliente.force_authenticate(user=usuario)

    respuesta = cliente.post("/api/v1/tareas/", _datos_tarea(proyecto), format="json")

    assert respuesta.status_code == esperado


def test_lider_crea_en_su_proyecto_y_recibe_403_en_uno_ajeno(roles, cliente):
    lider = crear_usuario_con_rol("LIDER")
    propio = ProyectoFactory(gerente=lider)
    ajeno = ProyectoFactory()
    cliente.force_authenticate(user=lider)

    respuesta = cliente.post("/api/v1/tareas/", _datos_tarea(propio), format="json")
    assert respuesta.status_code == 201

    respuesta = cliente.post("/api/v1/tareas/", _datos_tarea(ajeno), format="json")
    assert respuesta.status_code == 403


def test_recurso_crea_tarea_asignandose_a_si_mismo(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto, recurso=recurso)
    cliente.force_authenticate(user=titular)

    respuesta = cliente.post(
        "/api/v1/tareas/", _datos_tarea(proyecto, responsable=str(recurso.id)), format="json"
    )

    assert respuesta.status_code == 201


def test_recurso_no_puede_crear_tarea_asignada_a_otro(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    RecursoFactory(usuario=titular)
    otro_recurso = RecursoFactory()
    proyecto = ProyectoFactory()
    cliente.force_authenticate(user=titular)

    respuesta = cliente.post(
        "/api/v1/tareas/",
        _datos_tarea(proyecto, responsable=str(otro_recurso.id)),
        format="json",
    )

    assert respuesta.status_code == 400


def test_recurso_no_puede_reasignar_el_responsable_a_otro(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    otro_recurso = RecursoFactory()
    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto, recurso=recurso)
    tarea = TareaFactory(proyecto=proyecto, responsable=recurso)
    cliente.force_authenticate(user=titular)

    respuesta = cliente.patch(
        f"/api/v1/tareas/{tarea.id}/", {"responsable": str(otro_recurso.id)}, format="json"
    )

    assert respuesta.status_code == 400


def test_recurso_ve_pero_no_edita_la_tarea_de_otro_recurso_del_mismo_proyecto(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    otro_recurso = RecursoFactory()
    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto, recurso=recurso)
    AsignacionRecursoFactory(proyecto=proyecto, recurso=otro_recurso)
    tarea_ajena = TareaFactory(proyecto=proyecto, responsable=otro_recurso)
    cliente.force_authenticate(user=titular)

    assert cliente.get(f"/api/v1/tareas/{tarea_ajena.id}/").status_code == 200
    respuesta = cliente.patch(f"/api/v1/tareas/{tarea_ajena.id}/", {"nombre": "X"}, format="json")
    assert respuesta.status_code == 403


def test_recurso_no_ve_tareas_de_proyectos_donde_no_esta_asignado(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    AsignacionRecursoFactory(proyecto=ProyectoFactory(), recurso=RecursoFactory(usuario=titular))
    tarea_ajena = TareaFactory(proyecto=ProyectoFactory())
    cliente.force_authenticate(user=titular)

    assert cliente.get(f"/api/v1/tareas/{tarea_ajena.id}/").status_code == 404


# --- creación durante ejecución -------------------------------------------------


def test_crear_tarea_en_proyecto_en_ejecucion_sin_motivo_da_400(roles, cliente):
    proyecto = ProyectoFactory(estado=EstadoProyecto.EJECUCION)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post("/api/v1/tareas/", _datos_tarea(proyecto), format="json")

    assert respuesta.status_code == 400


def test_crear_tarea_en_proyecto_en_ejecucion_con_motivo_queda_marcada(roles, cliente):
    proyecto = ProyectoFactory(estado=EstadoProyecto.EJECUCION)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        "/api/v1/tareas/",
        _datos_tarea(proyecto, motivo_creacion="Cambio solicitado por el comité"),
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["creada_durante_ejecucion"] is True


# --- jerarquía -------------------------------------------------------------------


def test_crear_tarea_de_cuarto_nivel_da_400(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    nivel_1 = TareaFactory(proyecto=proyecto)
    nivel_2 = TareaFactory(proyecto=proyecto, tarea_padre=nivel_1)
    nivel_3 = TareaFactory(proyecto=proyecto, tarea_padre=nivel_2)

    respuesta = cliente.post(
        "/api/v1/tareas/",
        _datos_tarea(proyecto, tarea_padre=str(nivel_3.id)),
        format="json",
    )

    assert respuesta.status_code == 400


# --- dependencias ----------------------------------------------------------------


def test_crear_dependencia_circular_da_409_con_la_ruta(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    t1 = TareaFactory(proyecto=proyecto)
    t2 = TareaFactory(proyecto=proyecto)
    DependenciaTareaFactory(tarea_origen=t1, tarea_destino=t2, tipo=TipoDependencia.FI)

    respuesta = cliente.post(
        "/api/v1/dependencias-tarea/",
        {
            "tarea_origen": str(t2.id),
            "tarea_destino": str(t1.id),
            "tipo": "FI",
            "dias_desfase": 0,
        },
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["error"]["detalles"]["ciclo"] == [t2.codigo, t1.codigo, t2.codigo]


def test_crear_dependencia_entre_proyectos_distintos_da_400(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)
    t1 = TareaFactory()
    t2 = TareaFactory()

    respuesta = cliente.post(
        "/api/v1/dependencias-tarea/",
        {"tarea_origen": str(t1.id), "tarea_destino": str(t2.id), "tipo": "FI", "dias_desfase": 0},
        format="json",
    )

    assert respuesta.status_code == 400


# --- cambiar-estado --------------------------------------------------------------


def test_cambiar_estado_a_bloqueada_sin_nota_da_400(roles, cliente):
    tarea = TareaFactory(estado=EstadoTarea.EN_PROGRESO)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        f"/api/v1/tareas/{tarea.id}/cambiar-estado/", {"estado": "BLOQUEADA"}, format="json"
    )

    assert respuesta.status_code == 400


def test_completar_tarea_con_subtarea_abierta_da_409(roles, cliente):
    padre = TareaFactory(estado=EstadoTarea.EN_PROGRESO)
    TareaFactory(tarea_padre=padre, proyecto=padre.proyecto, estado=EstadoTarea.EN_PROGRESO)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        f"/api/v1/tareas/{padre.id}/cambiar-estado/", {"estado": "COMPLETADA"}, format="json"
    )

    assert respuesta.status_code == 409


def test_completar_tarea_fija_avance_100(roles, cliente):
    tarea = TareaFactory(estado=EstadoTarea.EN_PROGRESO, avance=40)
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.post(
        f"/api/v1/tareas/{tarea.id}/cambiar-estado/", {"estado": "COMPLETADA"}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.data["avance"] == "100.00"


# --- árbol y fechas sugeridas -----------------------------------------------------


def test_arbol_de_tareas_anida_subtareas(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    raiz = TareaFactory(proyecto=proyecto, orden=1)
    TareaFactory(proyecto=proyecto, tarea_padre=raiz, orden=1)

    respuesta = cliente.get(f"/api/v1/tareas/arbol/?proyecto={proyecto.id}")

    assert respuesta.status_code == 200
    assert len(respuesta.data) == 1
    assert respuesta.data[0]["codigo"] == raiz.codigo
    assert len(respuesta.data[0]["subtareas"]) == 1


def test_arbol_sin_proyecto_da_400(roles, cliente):
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    respuesta = cliente.get("/api/v1/tareas/arbol/")

    assert respuesta.status_code == 400


def test_fechas_sugeridas_endpoint(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    predecesora = TareaFactory(proyecto=proyecto, fecha_fin_plan=datetime.date(2026, 4, 1))
    destino = TareaFactory(proyecto=proyecto)
    DependenciaTareaFactory(
        tarea_origen=predecesora, tarea_destino=destino, tipo=TipoDependencia.FI, dias_desfase=0
    )

    respuesta = cliente.get(f"/api/v1/tareas/{destino.id}/fechas-sugeridas/")

    assert respuesta.status_code == 200
    assert respuesta.data["fecha_inicio_sugerida"] == "2026-04-02"


# --- filtros -----------------------------------------------------------------------


def test_filtro_vencidas(roles, cliente):
    proyecto = ProyectoFactory()
    admin = crear_usuario_con_rol("ADMIN")
    cliente.force_authenticate(user=admin)

    vencida = TareaFactory(
        proyecto=proyecto,
        fecha_fin_plan=datetime.date(2020, 1, 1),
        estado=EstadoTarea.EN_PROGRESO,
    )
    TareaFactory(
        proyecto=proyecto,
        fecha_fin_plan=datetime.date(2099, 1, 1),
        estado=EstadoTarea.EN_PROGRESO,
    )
    TareaFactory(
        proyecto=proyecto,
        fecha_fin_plan=datetime.date(2020, 1, 1),
        estado=EstadoTarea.COMPLETADA,
    )

    respuesta = cliente.get("/api/v1/tareas/?vencidas=true")

    ids = {fila["id"] for fila in respuesta.data["results"]}
    assert ids == {str(vencida.id)}


def test_filtro_mis_tareas(roles, cliente):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto, recurso=recurso)
    propia = TareaFactory(proyecto=proyecto, responsable=recurso)
    cliente.force_authenticate(user=titular)

    respuesta = cliente.get("/api/v1/tareas/?mis_tareas=true")

    ids = {fila["id"] for fila in respuesta.data["results"]}
    assert ids == {str(propia.id)}
