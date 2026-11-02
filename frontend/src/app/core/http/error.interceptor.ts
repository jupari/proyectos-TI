import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { ErrorApi } from '../models';
import { ToastService } from '../ui/toast.service';

/** Traduce la respuesta a `ErrorApi`, muestra `mensaje` en un toast (salvo en
 * 401, que ya maneja `authInterceptor`) y repropaga el error para que el
 * formulario pueda pintar `detalles` campo por campo. */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);

  return next(req).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status !== 401) {
        const cuerpo = error.error as Partial<ErrorApi> | null;
        const mensaje = cuerpo?.error?.mensaje ?? 'Ocurrió un error inesperado. Intente de nuevo.';
        toast.mostrar({ tipo: 'error', mensaje });
      }
      return throwError(() => error);
    }),
  );
};
