"""Caché ligera de los seis endpoints del tablero (fase 10 §10.1.3): 60
segundos por usuario y combinación de filtros, con un contador de versión
global que las aprobaciones de ejecución y las publicaciones de seguimiento
incrementan (`apps/tablero/signals.py`) para invalidar todo de una vez.

Se invalida TODO el tablero, no solo "el proyecto afectado": una versión por
proyecto obligaría a saber de antemano qué proyectos entran en cada
combinación de filtros para poder construir la clave, lo que anula la
ganancia de cachear. Una versión global es más simple, nunca deja ver un
dato obsoleto (en el peor caso invalida de más) y cumple el criterio real
de la fase: "aprobar un registro y refrescar el tablero muestra el nuevo
valor"."""

from django.core.cache import cache
from django.utils import timezone

_CLAVE_VERSION = "tablero:version"
TTL_SEGUNDOS = 60


def _version_actual():
    return cache.get(_CLAVE_VERSION, 0)


def invalidar():
    cache.set(_CLAVE_VERSION, _version_actual() + 1, None)


def _clave(request, nombre_vista):
    usuario_id = request.user.id
    version = _version_actual()
    filtros = "&".join(f"{clave}={valor}" for clave, valor in sorted(request.query_params.items()))
    return f"tablero:{nombre_vista}:{usuario_id}:{version}:{filtros}"


def desde_cache_o_calcular(request, nombre_vista, calcular):
    """Devuelve `(datos, calculado_en)`. `calcular` es una función sin
    argumentos que solo se invoca si no hay caché vigente o si
    `?refrescar=true` la salta."""
    clave = _clave(request, nombre_vista)
    refrescar = request.query_params.get("refrescar") == "true"

    if not refrescar:
        cacheado = cache.get(clave)
        if cacheado is not None:
            return cacheado

    datos = calcular()
    ahora = timezone.now()
    cache.set(clave, (datos, ahora), TTL_SEGUNDOS)
    return datos, ahora
