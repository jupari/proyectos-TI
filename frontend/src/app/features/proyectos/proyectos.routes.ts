import { Routes } from '@angular/router';

import { permisoGuard } from '../../core/guards/permiso.guard';

export const proyectosRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./lista/lista').then((m) => m.ListaProyectos),
  },
  {
    path: 'nuevo',
    loadComponent: () => import('./formulario/formulario').then((m) => m.FormularioProyecto),
    canActivate: [permisoGuard('proyectos.crear')],
  },
  {
    path: ':id/editar',
    loadComponent: () => import('./formulario/formulario').then((m) => m.FormularioProyecto),
    canActivate: [permisoGuard('proyectos.editar')],
  },
  {
    path: ':id',
    loadComponent: () => import('./detalle/detalle').then((m) => m.DetalleProyecto),
  },
];
