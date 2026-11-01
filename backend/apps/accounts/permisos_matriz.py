"""Traduce la matriz de docs/api-contrato.md §8 a permisos de Django
(`add_x`/`change_x`/`delete_x`/`view_x`) para que `seed_roles` los asigne a
cada `Group`. Esto es un apoyo para el admin de Django; el control de acceso
real de la API lo hacen las clases de `apps/core/permissions.py` y
`MixinAlcancePorRol`, no este permiso de modelo.

`A` (aprobar/publicar) no tiene equivalente en los permisos estándar de
Django: se aplica en el código de negocio de las fases 08/09, no aquí.
"""

LETRA_A_ACCION = {"L": "view", "C": "add", "E": "change", "B": "delete"}

MODELOS_POR_RECURSO = {
    "usuarios_roles": ["accounts.Usuario", "accounts.RolMeta"],
    "catalogos": ["catalogos.Area", "catalogos.Portafolio", "catalogos.PerfilRecurso"],
    "proyectos": ["proyectos.Proyecto"],
    "fases_hitos_rubros": [
        "proyectos.FaseProyecto",
        "proyectos.Hito",
        "proyectos.RubroPresupuesto",
    ],
    "recursos_tarifas": ["recursos.Recurso", "recursos.TarifaRecurso"],
    "asignaciones": ["recursos.AsignacionRecurso"],
    "tareas": ["tareas.Tarea", "tareas.DependenciaTarea"],
    "registros_ejecucion": ["ejecucion.RegistroEjecucion"],
    "gastos_ejecutados": ["ejecucion.GastoEjecutado"],
    "seguimientos": ["seguimiento.Seguimiento", "seguimiento.CompromisoSeguimiento"],
    "documentos_expediente": ["expediente.DocumentoExpediente"],
    "bitacora": ["expediente.EntradaBitacora"],
}

# Letras por rol y recurso, copiadas tal cual de la tabla de docs/api-contrato.md §8.
MATRIZ_PERMISOS = {
    "usuarios_roles": {"ADMIN": "LCEB", "PMO": "L", "LIDER": "", "RECURSO": "", "CONSULTA": ""},
    "catalogos": {"ADMIN": "LCEB", "PMO": "LCE", "LIDER": "L", "RECURSO": "L", "CONSULTA": "L"},
    "proyectos": {"ADMIN": "LCEB", "PMO": "LCE", "LIDER": "LE", "RECURSO": "L", "CONSULTA": "L"},
    "fases_hitos_rubros": {
        "ADMIN": "LCEB",
        "PMO": "LCE",
        "LIDER": "LCE",
        "RECURSO": "L",
        "CONSULTA": "L",
    },
    "recursos_tarifas": {
        "ADMIN": "LCEB",
        "PMO": "LCE",
        "LIDER": "L",
        "RECURSO": "L",
        "CONSULTA": "L",
    },
    "asignaciones": {
        "ADMIN": "LCEB",
        "PMO": "LCE",
        "LIDER": "LCE",
        "RECURSO": "L",
        "CONSULTA": "L",
    },
    "tareas": {"ADMIN": "LCEB", "PMO": "LCE", "LIDER": "LCE", "RECURSO": "LCE", "CONSULTA": "L"},
    "registros_ejecucion": {
        "ADMIN": "LCEB",
        "PMO": "LCE",
        "LIDER": "LCE",
        "RECURSO": "LCE",
        "CONSULTA": "L",
    },
    "gastos_ejecutados": {
        "ADMIN": "LCEB",
        "PMO": "LCE",
        "LIDER": "LC",
        "RECURSO": "",
        "CONSULTA": "L",
    },
    "seguimientos": {
        "ADMIN": "LCEB",
        "PMO": "LCE",
        "LIDER": "LCE",
        "RECURSO": "L",
        "CONSULTA": "L",
    },
    "documentos_expediente": {
        "ADMIN": "LCEB",
        "PMO": "LCE",
        "LIDER": "LCE",
        "RECURSO": "LC",
        "CONSULTA": "L",
    },
    "bitacora": {"ADMIN": "L", "PMO": "L", "LIDER": "L", "RECURSO": "", "CONSULTA": ""},
}
