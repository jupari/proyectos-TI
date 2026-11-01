"""Utilidades compartidas para resolver roles y el alcance por proyecto.

`RUTA_A_PROYECTO` es la única fuente de verdad de cómo llegar de un modelo a
su `Proyecto` cuando no tiene un campo `proyecto` directo. La usan
`apps.core.signals` (bitácora), `apps.core.permissions` y `apps.core.mixins`
(alcance por rol), para no repetir esa correspondencia tres veces.
"""

RUTA_A_PROYECTO = {
    "CompromisoSeguimiento": "seguimiento.proyecto",
    "DependenciaTarea": "tarea_origen.proyecto",
}

# Roles que ven todo (sin filtrar por alcance).
ROLES_ALCANCE_TOTAL = {"ADMIN", "PMO", "CONSULTA"}


def codigos_roles_de(usuario):
    if not usuario or not getattr(usuario, "is_authenticated", False):
        return set()
    grupos = usuario.groups.filter(rol_meta__isnull=False)
    return set(grupos.values_list("rol_meta__codigo", flat=True))


def resolver_proyecto_de_instancia(obj):
    """Resuelve el `Proyecto` relacionado con una instancia de modelo.

    Cualquier fallo (p. ej. el objeto relacionado ya fue borrado en la misma
    transacción) se trata como "sin proyecto", nunca como una excepción.
    """
    try:
        if hasattr(obj, "proyecto_id"):
            return obj.proyecto
        ruta = RUTA_A_PROYECTO.get(type(obj).__name__)
        if not ruta:
            return None
        objeto = obj
        for paso in ruta.split("."):
            objeto = getattr(objeto, paso, None)
            if objeto is None:
                return None
        return objeto
    except Exception:
        return None


def prefijo_proyecto(modelo):
    """Prefijo de lookup ORM (`""`, `"proyecto__"`, `"tarea_origen__proyecto__"`, ...)
    para llegar al `Proyecto` relacionado con `modelo` desde un queryset, o
    `None` si el modelo no tiene relación con `Proyecto`."""
    nombre = modelo.__name__
    if nombre == "Proyecto":
        return ""
    if hasattr(modelo, "proyecto"):
        return "proyecto__"
    ruta = RUTA_A_PROYECTO.get(nombre)
    if ruta:
        return ruta.replace(".", "__") + "__"
    return None
