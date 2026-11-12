"""`PERMISOS_POR_ROL` es la única fuente de verdad de los `permisos_ui` que
viajan en la respuesta de `/auth/login/` y `/auth/yo/`. El frontend solo los
muestra/oculta; nunca los reconstruye ni los usa como control de acceso real.
"""

PERMISOS_POR_ROL = {
    "ADMIN": [
        "admin.usuarios",
        "admin.roles",
        "admin.integraciones",
        "catalogos.crear",
        "catalogos.editar",
        "catalogos.borrar",
        "proyectos.ver",
        "proyectos.crear",
        "proyectos.editar",
        "proyectos.borrar",
        "recursos.ver",
        "recursos.crear",
        "recursos.editar",
        "recursos.borrar",
        "tareas.ver",
        "tareas.crear",
        "tareas.editar",
        "tareas.borrar",
        "ejecucion.ver",
        "ejecucion.registrar",
        "ejecucion.editar",
        "ejecucion.aprobar",
        "ejecucion.borrar",
        "seguimientos.ver",
        "seguimientos.crear",
        "seguimientos.editar",
        "seguimientos.publicar",
        "seguimientos.borrar",
        "expediente.ver",
        "expediente.crear",
        "expediente.editar",
        "expediente.borrar",
        "bitacora.ver",
        "tablero.ver",
    ],
    "PMO": [
        "catalogos.crear",
        "catalogos.editar",
        "proyectos.ver",
        "proyectos.crear",
        "proyectos.editar",
        "recursos.ver",
        "recursos.crear",
        "recursos.editar",
        "tareas.ver",
        "tareas.crear",
        "tareas.editar",
        "ejecucion.ver",
        "ejecucion.registrar",
        "ejecucion.editar",
        "ejecucion.aprobar",
        "seguimientos.ver",
        "seguimientos.crear",
        "seguimientos.editar",
        "seguimientos.publicar",
        "expediente.ver",
        "expediente.crear",
        "expediente.editar",
        "bitacora.ver",
        "tablero.ver",
    ],
    "LIDER": [
        "proyectos.ver",
        "proyectos.editar",
        "fases.crear",
        "fases.editar",
        "asignaciones.crear",
        "asignaciones.editar",
        "tareas.ver",
        "tareas.crear",
        "tareas.editar",
        "ejecucion.ver",
        "ejecucion.registrar",
        "ejecucion.editar",
        "ejecucion.aprobar",
        "gastos.crear",
        "seguimientos.ver",
        "seguimientos.crear",
        "seguimientos.editar",
        "seguimientos.publicar",
        "expediente.ver",
        "expediente.crear",
        "expediente.editar",
        "bitacora.ver",
        "tablero.ver",
    ],
    "RECURSO": [
        "proyectos.ver",
        "tareas.ver",
        "tareas.crear",
        "tareas.editar",
        "ejecucion.ver",
        "ejecucion.registrar",
        "ejecucion.editar",
        "expediente.ver",
        "expediente.crear",
        "tablero.ver",
    ],
    "CONSULTA": [
        "proyectos.ver",
        "recursos.ver",
        "tareas.ver",
        "ejecucion.ver",
        "seguimientos.ver",
        "expediente.ver",
        "tablero.ver",
    ],
}


def permisos_de(usuario):
    """Une los `permisos_ui` de todos los roles del usuario."""
    if not usuario or not getattr(usuario, "is_authenticated", False):
        return []

    codigos_roles = usuario.groups.filter(rol_meta__isnull=False).values_list(
        "rol_meta__codigo", flat=True
    )
    permisos = set()
    for codigo in codigos_roles:
        permisos.update(PERMISOS_POR_ROL.get(codigo, []))
    return sorted(permisos)
