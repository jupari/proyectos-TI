import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize } from 'rxjs';

import { CargandoService } from '../ui/cargando.service';

export const cargandoInterceptor: HttpInterceptorFn = (req, next) => {
  const cargando = inject(CargandoService);
  cargando.iniciar();
  return next(req).pipe(finalize(() => cargando.finalizar()));
};
