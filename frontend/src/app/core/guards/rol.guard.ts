import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';

export function rolGuard(codigos: string[]): CanActivateFn {
  return () => {
    const authService = inject(AuthService);
    const router = inject(Router);

    if (codigos.some((codigo) => authService.tieneRol(codigo))) {
      return true;
    }
    return router.createUrlTree(['/403']);
  };
}
