from types import SimpleNamespace

import pytest

from apps.accounts.tests.factories import UsuarioFactory
from apps.catalogos.tests.factories import AreaFactory
from apps.core.choices import TipoEvento
from apps.core.middleware import MiddlewareUsuarioActual
from apps.expediente.models import EntradaBitacora
from apps.proyectos.models import Proyecto
from apps.tareas.tests.factories import TareaFactory

pytestmark = pytest.mark.django_db


def _ejecutar_dentro_de_peticion(usuario, accion):
    """Simula una petición autenticada: ejecuta `accion()` con el ContextVar
    de MiddlewareUsuarioActual activo, igual que pasaría dentro de una vista."""
    resultado = {}

    def get_response(request):
        resultado["valor"] = accion()
        return None

    MiddlewareUsuarioActual(get_response)(SimpleNamespace(user=usuario))
    return resultado["valor"]


def test_creacion_deja_entrada_de_bitacora_con_usuario():
    usuario = UsuarioFactory()

    area = _ejecutar_dentro_de_peticion(
        usuario, lambda: AreaFactory(codigo="AUD-01", nombre="Área de auditoría")
    )

    area.refresh_from_db()
    assert area.creado_por_id == usuario.id
    assert area.actualizado_por_id == usuario.id

    entrada = EntradaBitacora.objects.filter(
        entidad="Area", entidad_id=area.id, tipo_evento=TipoEvento.CREACION
    ).first()
    assert entrada is not None
    assert entrada.usuario_id == usuario.id
    assert entrada.datos_despues["nombre"] == "Área de auditoría"


def test_actualizacion_deja_diff_esperado():
    usuario = UsuarioFactory()
    area = _ejecutar_dentro_de_peticion(
        usuario, lambda: AreaFactory(codigo="AUD-02", nombre="Nombre original")
    )

    otro_usuario = UsuarioFactory()

    def renombrar():
        area.nombre = "Nombre actualizado"
        area.save()
        return area

    _ejecutar_dentro_de_peticion(otro_usuario, renombrar)

    area.refresh_from_db()
    assert area.actualizado_por_id == otro_usuario.id
    assert area.creado_por_id == usuario.id  # no cambia en la actualización

    entrada = EntradaBitacora.objects.filter(
        entidad="Area", entidad_id=area.id, tipo_evento=TipoEvento.ACTUALIZACION
    ).first()
    assert entrada is not None
    assert entrada.usuario_id == otro_usuario.id
    assert entrada.datos_antes == {"nombre": "Nombre original"}
    assert entrada.datos_despues == {"nombre": "Nombre actualizado"}


def test_sin_cambios_no_genera_entrada_de_actualizacion():
    usuario = UsuarioFactory()
    area = _ejecutar_dentro_de_peticion(
        usuario, lambda: AreaFactory(codigo="AUD-03", nombre="Sin cambios")
    )

    cantidad_antes = EntradaBitacora.objects.filter(entidad="Area", entidad_id=area.id).count()
    _ejecutar_dentro_de_peticion(usuario, lambda: area.save())
    cantidad_despues = EntradaBitacora.objects.filter(entidad="Area", entidad_id=area.id).count()

    assert cantidad_despues == cantidad_antes


def test_borrado_fisico_en_cascada_no_rompe_por_fk_de_bitacora():
    """Regresión: borrar un Proyecto borra en cascada sus tareas; el
    `post_delete` de cada tarea no debe intentar escribir una entrada de
    bitácora que referencie un `proyecto` que, en la misma transacción,
    también se está borrando (Postgres solo valida esa FK al COMMIT)."""
    tarea = TareaFactory()
    proyecto_id = tarea.proyecto_id

    Proyecto.objects.filter(pk=proyecto_id).delete()

    assert not Proyecto.objects.filter(pk=proyecto_id).exists()
    entrada = EntradaBitacora.objects.filter(entidad="Tarea", entidad_id=tarea.id).first()
    assert entrada is not None
    assert entrada.proyecto_id is None
