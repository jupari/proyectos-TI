import { Routes } from '@angular/router';

export const tareasRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./bandeja/bandeja').then((m) => m.BandejaTareas),
  },
  {
    path: ':id',
    loadComponent: () => import('./detalle/detalle').then((m) => m.DetalleTarea),
  },
];
