import { Routes } from '@angular/router';

import { environment } from '../environments/environment';
import { autenticadoGuard } from './core/guards/autenticado.guard';
import { cambioClaveGuard } from './core/guards/cambio-clave.guard';
import { permisoGuard } from './core/guards/permiso.guard';
import { CambiarClave } from './features/auth/cambiar-clave';
import { GoogleCallback } from './features/auth/google-callback';
import { Login } from './features/auth/login';
import { Perfil } from './features/auth/perfil';
import { EnConstruccion } from './features/comun/en-construccion';
import { Pagina403 } from './features/comun/pagina-403';
import { Pagina404 } from './features/comun/pagina-404';
import { Shell } from './layout/shell';
import { Catalogo } from './shared/ui/catalogo/catalogo';

export const routes: Routes = [
  { path: 'auth/login', component: Login },
  { path: 'auth/google/callback', component: GoogleCallback },
  { path: 'auth/cambiar-clave', component: CambiarClave, canActivate: [autenticadoGuard] },
  { path: '403', component: Pagina403 },

  ...(!environment.production
    ? [{ path: 'dev/catalogo', component: Catalogo }]
    : []),

  {
    path: '',
    component: Shell,
    canActivate: [autenticadoGuard, cambioClaveGuard],
    canActivateChild: [cambioClaveGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'tablero' },
      { path: 'tablero', component: EnConstruccion },
      {
        path: 'proyectos',
        loadChildren: () => import('./features/proyectos/proyectos.routes').then((m) => m.proyectosRoutes),
      },
      {
        path: 'tareas',
        loadChildren: () => import('./features/tareas/tareas.routes').then((m) => m.tareasRoutes),
      },
      {
        path: 'ejecucion',
        loadChildren: () => import('./features/ejecucion/ejecucion.routes').then((m) => m.ejecucionRoutes),
      },
      { path: 'seguimientos', component: EnConstruccion },
      {
        path: 'recursos',
        loadChildren: () => import('./features/recursos/recursos.routes').then((m) => m.recursosRoutes),
        canActivate: [permisoGuard('recursos.ver')],
      },
      {
        path: 'admin/usuarios',
        component: EnConstruccion,
        canActivate: [permisoGuard('admin.usuarios')],
      },
      {
        path: 'admin/roles',
        component: EnConstruccion,
        canActivate: [permisoGuard('admin.usuarios')],
      },
      {
        path: 'admin/catalogos',
        loadComponent: () =>
          import('./features/admin/catalogos/catalogos').then((m) => m.Catalogos),
        canActivate: [permisoGuard('catalogos.crear')],
      },
      { path: 'perfil', component: Perfil },
    ],
  },

  { path: '**', component: Pagina404 },
];
