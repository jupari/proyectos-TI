"""Regla de negocio de los catálogos (docs/plan/fase-05 §5.1.2): no se puede
desactivar un catálogo que todavía está en uso por registros activos."""

from apps.core.exceptions import ErrorConflicto


def _conteo_si_hay(relacion):
    if relacion is None:
        return 0
    return relacion.filter(activo=True).count()


def validar_desactivacion(instancia):
    """Lanza `ErrorConflicto` (409) con el conteo de referencias activas en
    `detalles` si el catálogo está en uso. No hace nada si puede desactivarse."""
    referencias = {}

    conteo_proyectos = _conteo_si_hay(getattr(instancia, "proyectos", None))
    if conteo_proyectos:
        referencias["proyectos"] = conteo_proyectos

    conteo_recursos = _conteo_si_hay(getattr(instancia, "recursos", None))
    if conteo_recursos:
        referencias["recursos"] = conteo_recursos

    if referencias:
        raise ErrorConflicto({"referencias": referencias})
