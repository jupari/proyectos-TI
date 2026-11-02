import { Routes } from '@angular/router';

import { permisoGuard } from '../../core/guards/permiso.guard';

export const seguimientosRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./lista/lista').then((m) => m.ListaSeguimientos),
  },
  {
    path: 'nuevo',
    loadComponent: () => import('./editor/editor').then((m) => m.EditorSeguimiento),
    canActivate: [permisoGuard('seguimientos.crear')],
  },
  {
    path: ':id',
    loadComponent: () => import('./editor/editor').then((m) => m.EditorSeguimiento),
  },
];
