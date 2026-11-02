import { Routes } from '@angular/router';

import { permisoGuard } from '../../core/guards/permiso.guard';

export const recursosRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./lista/lista').then((m) => m.ListaRecursos),
  },
  {
    path: 'nuevo',
    loadComponent: () => import('./formulario/formulario').then((m) => m.FormularioRecurso),
    canActivate: [permisoGuard('recursos.crear')],
  },
  {
    path: ':id/editar',
    loadComponent: () => import('./formulario/formulario').then((m) => m.FormularioRecurso),
    canActivate: [permisoGuard('recursos.editar')],
  },
  {
    // Debe ir antes de `:id`: de lo contrario el router resuelve
    // "/recursos/asignaciones" como el detalle del recurso con id="asignaciones".
    path: 'asignaciones',
    loadComponent: () =>
      import('./asignaciones-globales/asignaciones-globales').then((m) => m.AsignacionesGlobales),
  },
  {
    path: ':id',
    loadComponent: () => import('./detalle/detalle').then((m) => m.DetalleRecurso),
  },
];
