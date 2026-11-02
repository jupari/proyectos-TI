import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';

export function permisoGuard(codigo: string): CanActivateFn {
  return () => {
    const authService = inject(AuthService);
    const router = inject(Router);

    if (authService.tienePermiso(codigo)) {
      return true;
    }
    return router.createUrlTree(['/403']);
  };
}
