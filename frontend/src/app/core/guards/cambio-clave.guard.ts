import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';

/** Si `debe_cambiar_clave` es true, fuerza la ruta de cambio de contraseña. */
export const cambioClaveGuard: CanActivateFn = (_ruta, estado) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const usuario = authService.usuario();
  if (usuario?.debe_cambiar_clave && estado.url !== '/auth/cambiar-clave') {
    return router.createUrlTree(['/auth/cambiar-clave']);
  }
  return true;
};
