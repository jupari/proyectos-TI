import { Routes } from '@angular/router';

import { permisoGuard } from '../../core/guards/permiso.guard';

export const ejecucionRoutes: Routes = [
  {
    path: 'registros',
    loadComponent: () => import('./mi-registro/mi-registro').then((m) => m.MiRegistro),
    canActivate: [permisoGuard('ejecucion.registrar')],
  },
  {
    path: 'aprobaciones',
    loadComponent: () => import('./aprobaciones/aprobaciones').then((m) => m.Aprobaciones),
    canActivate: [permisoGuard('ejecucion.aprobar')],
  },
];
