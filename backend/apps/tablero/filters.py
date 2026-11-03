"""Resuelve el queryset de `Proyecto` que usan los seis endpoints del
tablero: el mismo alcance por rol y los mismos filtros que `/proyectos/`
(docs/plan/fase-10-tablero-control.md §10.1.2), para que el tablero y la
lista de proyectos sean siempre coherentes."""

from apps.core.mixins import MixinAlcancePorRol
from apps.proyectos.filters import FiltroProyecto
from apps.proyectos.models import Proyecto


class _AlcancePorRol(MixinAlcancePorRol):
    """Adapta `MixinAlcancePorRol` (pensado para un `ViewSet`, que expone
    `self.request`) para poder invocar `filtrar_por_rol` desde una `APIView`
    cualquiera sin heredar de ella."""

    def __init__(self, request):
        self.request = request


def proyectos_del_tablero(request):
    """`Proyecto.objects.filter(activo=True)` acotado por el alcance del
    rol de `request.user` y por los filtros de query string que acepta
    `FiltroProyecto` (los mismos de `/proyectos/`)."""
    queryset = Proyecto.objects.filter(activo=True)
    queryset = _AlcancePorRol(request).filtrar_por_rol(queryset)
    queryset = FiltroProyecto(request.query_params, queryset=queryset, request=request).qs

    # `_alcance_lider`/`_alcance_recurso` (apps.core.mixins) dejan `distinct=True` en
    # el queryset (necesario para su propio `OR` con joins). Combinado después con
    # `.values(...).annotate(Count/Sum(...))` en `apps.tablero.services`, ese
    # `distinct` corrompe el `GROUP BY` (Django agrupa también por `id`, deshaciendo
    # la agregación: dos proyectos con el mismo estado salen como dos grupos en vez
    # de uno). Resolver por `pk` aquí devuelve un queryset limpio, sin ese rastro,
    # para que toda agregación posterior agrupe como se espera.
    return Proyecto.objects.filter(pk__in=list(queryset.values_list("pk", flat=True)))
