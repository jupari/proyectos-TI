export interface ItemMenu {
  etiqueta: string;
  icono: string;
  ruta: string;
  /** Si se omite junto con `permisos`, es visible para cualquiera autenticado. */
  permiso?: string;
  /** Visible si el usuario tiene cualquiera de estos permisos. */
  permisos?: string[];
}

/** PLAN.md §4 / fase-04: ítems del menú lateral y su permiso de visibilidad.
 * Un ítem sin permiso no se renderiza; además la ruta queda protegida por guard. */
export const ITEMS_MENU: ItemMenu[] = [
  { etiqueta: 'Tablero', icono: '📊', ruta: '/tablero' },
  { etiqueta: 'Mi trabajo', icono: '🧑‍💻', ruta: '/mi-trabajo' },
  { etiqueta: 'Proyectos', icono: '📁', ruta: '/proyectos' },
  { etiqueta: 'Tareas', icono: '✅', ruta: '/tareas' },
  {
    etiqueta: 'Ejecución',
    icono: '⏱️',
    ruta: '/ejecucion/registros',
    permisos: ['ejecucion.registrar', 'ejecucion.aprobar'],
  },
  { etiqueta: 'Seguimientos', icono: '📈', ruta: '/seguimientos' },
  { etiqueta: 'Recursos', icono: '👥', ruta: '/recursos', permiso: 'recursos.ver' },
  { etiqueta: 'Administración', icono: '⚙️', ruta: '/admin/usuarios', permiso: 'admin.usuarios' },
  { etiqueta: 'Catálogos', icono: '🗂️', ruta: '/admin/catalogos', permiso: 'catalogos.crear' },
  {
    etiqueta: 'Integraciones',
    icono: '🔌',
    ruta: '/admin/integraciones',
    permiso: 'admin.integraciones',
  },
];
