"""Pruebas de la matriz de roles de docs/api-contrato.md §8.

Nota de alcance: los recursos de negocio (proyectos, tareas, registros de
ejecución, ...) todavía no tienen `ViewSet` ni URL — llegan en las fases 05
a 10 ("Fuera de alcance" de PLAN.md para esta fase). Lo que esta fase
realmente construye son las clases de permiso de `apps/core/permissions.py`
y `MixinAlcancePorRol`; estas pruebas las ejercitan directamente (y a los
modelos reales vía factories) en vez de inventar ViewSets de relleno.
Las fases 05+ solo tendrán que conectar estas piezas a sus ViewSets.
"""

from types import SimpleNamespace

import pytest

from apps.accounts.tests.conftest import crear_usuario_con_rol
from apps.accounts.tests.factories import UsuarioFactory
from apps.core.mixins import MixinAlcancePorRol
from apps.core.permissions import EsAdmin, EsDuenoDelRegistro, EsLiderDelProyecto, EsPmoOAdmin
from apps.ejecucion.models import RegistroEjecucion
from apps.ejecucion.tests.factories import RegistroEjecucionFactory
from apps.proyectos.models import Proyecto
from apps.proyectos.tests.factories import ProyectoFactory
from apps.recursos.tests.factories import AsignacionRecursoFactory, RecursoFactory
from apps.tareas.models import Tarea
from apps.tareas.tests.factories import DependenciaTareaFactory, TareaFactory

pytestmark = pytest.mark.django_db


class _VistaFalsa(MixinAlcancePorRol):
    def __init__(self, usuario):
        self.request = SimpleNamespace(user=usuario)


def _peticion(usuario, metodo="GET"):
    return SimpleNamespace(user=usuario, method=metodo)


# --- EsAdmin / EsPmoOAdmin ------------------------------------------------


@pytest.mark.parametrize(
    ("codigo_rol", "esperado"),
    [("ADMIN", True), ("PMO", False), ("LIDER", False), ("RECURSO", False), ("CONSULTA", False)],
)
def test_es_admin(roles, codigo_rol, esperado):
    usuario = crear_usuario_con_rol(codigo_rol)
    assert EsAdmin().has_permission(_peticion(usuario), None) is esperado


@pytest.mark.parametrize(
    ("codigo_rol", "esperado"),
    [("ADMIN", True), ("PMO", True), ("LIDER", False), ("RECURSO", False), ("CONSULTA", False)],
)
def test_es_pmo_o_admin(roles, codigo_rol, esperado):
    usuario = crear_usuario_con_rol(codigo_rol)
    assert EsPmoOAdmin().has_permission(_peticion(usuario), None) is esperado


# --- EsLiderDelProyecto ----------------------------------------------------


def test_es_lider_del_proyecto_autoriza_al_gerente_y_al_lider_tecnico(roles):
    gerente = crear_usuario_con_rol("LIDER")
    lider_tecnico = crear_usuario_con_rol("LIDER")
    otro_lider = crear_usuario_con_rol("LIDER")
    proyecto = ProyectoFactory(gerente=gerente, lider_tecnico=lider_tecnico)
    tarea = TareaFactory(proyecto=proyecto)

    permiso = EsLiderDelProyecto()
    assert permiso.has_object_permission(_peticion(gerente), None, tarea) is True
    assert permiso.has_object_permission(_peticion(lider_tecnico), None, tarea) is True
    assert permiso.has_object_permission(_peticion(otro_lider), None, tarea) is False


def test_es_lider_del_proyecto_admin_y_pmo_siempre_pasan(roles):
    admin = crear_usuario_con_rol("ADMIN")
    pmo = crear_usuario_con_rol("PMO")
    tarea = TareaFactory(proyecto=ProyectoFactory())

    permiso = EsLiderDelProyecto()
    assert permiso.has_object_permission(_peticion(admin), None, tarea) is True
    assert permiso.has_object_permission(_peticion(pmo), None, tarea) is True


def test_es_lider_del_proyecto_resuelve_ruta_indirecta(roles):
    lider = crear_usuario_con_rol("LIDER")
    proyecto = ProyectoFactory(gerente=lider)
    dependencia = DependenciaTareaFactory(
        tarea_origen=TareaFactory(proyecto=proyecto), tarea_destino=TareaFactory(proyecto=proyecto)
    )

    assert EsLiderDelProyecto().has_object_permission(_peticion(lider), None, dependencia) is True


# --- EsDuenoDelRegistro -----------------------------------------------------


def test_es_dueno_del_registro_compara_recurso_usuario(roles):
    propietario = crear_usuario_con_rol("RECURSO")
    otro = crear_usuario_con_rol("RECURSO")
    registro = RegistroEjecucionFactory(recurso=RecursoFactory(usuario=propietario))

    permiso = EsDuenoDelRegistro()
    assert permiso.has_object_permission(_peticion(propietario), None, registro) is True
    assert permiso.has_object_permission(_peticion(otro), None, registro) is False


def test_es_dueno_del_registro_compara_responsable_de_tarea(roles):
    propietario = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=propietario)
    tarea = TareaFactory(responsable=recurso)

    assert EsDuenoDelRegistro().has_object_permission(_peticion(propietario), None, tarea) is True


# --- MixinAlcancePorRol: fuga de datos --------------------------------------


def test_alcance_admin_pmo_consulta_ve_todo(roles):
    ProyectoFactory.create_batch(3)
    for codigo in ("ADMIN", "PMO", "CONSULTA"):
        vista = _VistaFalsa(crear_usuario_con_rol(codigo))
        assert vista.filtrar_por_rol(Proyecto.objects.all()).count() == Proyecto.objects.count()


def test_lider_no_ve_proyectos_ajenos(roles):
    lider = crear_usuario_con_rol("LIDER")
    propio = ProyectoFactory(gerente=lider)
    ProyectoFactory.create_batch(2)  # proyectos ajenos

    vista = _VistaFalsa(lider)
    proyectos = vista.filtrar_por_rol(Proyecto.objects.all())

    assert proyectos.count() == 1
    assert list(proyectos) == [propio]


def test_lider_solo_ve_las_tareas_de_sus_proyectos(roles):
    lider = crear_usuario_con_rol("LIDER")
    propio = ProyectoFactory(gerente=lider)
    ajeno = ProyectoFactory()
    tarea_propia = TareaFactory(proyecto=propio)
    tarea_ajena = TareaFactory(proyecto=ajeno)

    tareas = _VistaFalsa(lider).filtrar_por_rol(Tarea.objects.all())

    assert list(tareas) == [tarea_propia]
    assert tarea_ajena not in tareas


def test_recurso_solo_ve_proyectos_con_asignacion_activa(roles):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    proyecto_asignado = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto_asignado, recurso=recurso)
    proyecto_no_asignado = ProyectoFactory()

    vista = _VistaFalsa(titular)
    proyectos = vista.filtrar_por_rol(Proyecto.objects.all())

    assert list(proyectos) == [proyecto_asignado]
    assert proyecto_no_asignado not in proyectos


def test_recurso_ve_todas_las_tareas_de_su_proyecto_y_ninguna_de_otros(roles):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto, recurso=recurso)

    tarea_propia = TareaFactory(proyecto=proyecto, responsable=recurso)
    tarea_de_otro = TareaFactory(proyecto=proyecto)
    tarea_de_proyecto_ajeno = TareaFactory(proyecto=ProyectoFactory())

    tareas = _VistaFalsa(titular).filtrar_por_rol(Tarea.objects.all())

    assert set(tareas) == {tarea_propia, tarea_de_otro}
    assert tarea_de_proyecto_ajeno not in tareas


def test_recurso_ve_todos_los_registros_de_ejecucion_de_su_proyecto(roles):
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    otro_recurso = RecursoFactory()
    proyecto = ProyectoFactory()
    AsignacionRecursoFactory(proyecto=proyecto, recurso=recurso)
    AsignacionRecursoFactory(proyecto=proyecto, recurso=otro_recurso)

    registro_propio = RegistroEjecucionFactory(proyecto=proyecto, recurso=recurso)
    registro_de_otro = RegistroEjecucionFactory(proyecto=proyecto, recurso=otro_recurso)

    registros = _VistaFalsa(titular).filtrar_por_rol(RegistroEjecucion.objects.all())

    assert set(registros) == {registro_propio, registro_de_otro}


def test_recurso_pide_registro_de_proyecto_ajeno_por_id_da_doesnotexist(roles):
    """Equivale a que la API responda 404 y no 403: con el queryset ya
    filtrado por `filtrar_por_rol`, `get_object()` de DRF hace
    `get_queryset().get(pk=...)`, que para un registro de un proyecto donde no
    está asignado (que sí existe) lanza `DoesNotExist` → 404."""
    titular = crear_usuario_con_rol("RECURSO")
    recurso = RecursoFactory(usuario=titular)
    AsignacionRecursoFactory(proyecto=ProyectoFactory(), recurso=recurso)
    registro_ajeno = RegistroEjecucionFactory(proyecto=ProyectoFactory())

    queryset_filtrado = _VistaFalsa(titular).filtrar_por_rol(RegistroEjecucion.objects.all())

    assert RegistroEjecucion.objects.filter(pk=registro_ajeno.pk).exists()
    with pytest.raises(RegistroEjecucion.DoesNotExist):
        queryset_filtrado.get(pk=registro_ajeno.pk)


def test_usuario_sin_rol_recibe_listas_vacias_no_error(roles):
    ProyectoFactory()
    usuario_sin_rol = UsuarioFactory()

    resultado = _VistaFalsa(usuario_sin_rol).filtrar_por_rol(Proyecto.objects.all())

    assert list(resultado) == []


def test_usuario_no_autenticado_recibe_lista_vacia():
    ProyectoFactory()
    anonimo = SimpleNamespace(is_authenticated=False)

    resultado = _VistaFalsa(anonimo).filtrar_por_rol(Proyecto.objects.all())

    assert list(resultado) == []
