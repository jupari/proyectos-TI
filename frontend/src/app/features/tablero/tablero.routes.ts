import { Routes } from '@angular/router';

export const tableroRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./panel/panel').then((m) => m.PanelTablero),
  },
  {
    path: 'recursos',
    loadComponent: () => import('./recursos/recursos').then((m) => m.RecursosTablero),
  },
  {
    path: 'proyectos-por-periodo',
    loadComponent: () =>
      import('./proyectos-periodo/proyectos-periodo').then((m) => m.ProyectosPeriodoTablero),
  },
  {
    path: 'plan-costos',
    loadComponent: () => import('./plan-costos/plan-costos').then((m) => m.PlanCostosTablero),
  },
];
