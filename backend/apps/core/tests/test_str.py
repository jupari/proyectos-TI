import pytest
from django.contrib.auth.models import Group

from apps.accounts.models import RolMeta
from apps.accounts.tests.factories import UsuarioFactory
from apps.catalogos.tests.factories import AreaFactory, PerfilRecursoFactory, PortafolioFactory
from apps.ejecucion.tests.factories import GastoEjecutadoFactory, RegistroEjecucionFactory
from apps.expediente.tests.factories import DocumentoExpedienteFactory, EntradaBitacoraFactory
from apps.proyectos.tests.factories import (
    FaseProyectoFactory,
    HitoFactory,
    ProyectoFactory,
    RubroPresupuestoFactory,
)
from apps.recursos.tests.factories import (
    AsignacionRecursoFactory,
    RecursoFactory,
    TarifaRecursoFactory,
)
from apps.seguimiento.tests.factories import CompromisoSeguimientoFactory, SeguimientoFactory
from apps.tareas.tests.factories import DependenciaTareaFactory, TareaFactory

FACTORIES = [
    UsuarioFactory,
    AreaFactory,
    PortafolioFactory,
    PerfilRecursoFactory,
    ProyectoFactory,
    FaseProyectoFactory,
    HitoFactory,
    RubroPresupuestoFactory,
    RecursoFactory,
    TarifaRecursoFactory,
    AsignacionRecursoFactory,
    TareaFactory,
    DependenciaTareaFactory,
    RegistroEjecucionFactory,
    GastoEjecutadoFactory,
    SeguimientoFactory,
    CompromisoSeguimientoFactory,
    DocumentoExpedienteFactory,
    EntradaBitacoraFactory,
]


@pytest.mark.django_db
@pytest.mark.parametrize("fabrica", FACTORIES, ids=[f.__name__ for f in FACTORIES])
def test_str_no_lanza_excepcion(fabrica):
    instancia = fabrica.create()
    assert isinstance(str(instancia), str)
    assert str(instancia) != ""


def test_str_rol_meta_no_lanza_excepcion():
    grupo = Group(name="Grupo de prueba")
    rol = RolMeta(grupo=grupo, codigo="PRUEBA", descripcion="Rol de prueba", orden=1)
    assert isinstance(str(rol), str)
    assert str(rol) != ""
