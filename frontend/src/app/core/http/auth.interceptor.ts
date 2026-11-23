import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, filter, from, switchMap, take, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';

// Endpoints sin sesión: no llevan Bearer ni disparan el refresco ante un 401
// (un código incorrecto responde 401 y no significa "sesión vencida").
const RUTA_PUBLICA =
  /\/auth\/(login|verificar-codigo|reenviar-codigo|recuperar-clave|restablecer-clave|refresh|google\/autorizar|google\/callback)\/?(\?|$)/;

let refrescando = false;
const accessTokenRefrescado$ = new BehaviorSubject<string | null>(null);

/** Añade `Authorization: Bearer`; ante un 401 intenta un único refresh y
 * reencola las peticiones en vuelo. Si el refresh falla, limpia la sesión y
 * redirige a /auth/login con `returnUrl`. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const esRutaPublica = RUTA_PUBLICA.test(req.url);
  const accessToken = authService.obtenerAccessToken();
  const peticion =
    accessToken && !esRutaPublica
      ? req.clone({ setHeaders: { Authorization: `Bearer ${accessToken}` } })
      : req;

  return next(peticion).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || error.status !== 401 || esRutaPublica) {
        return throwError(() => error);
      }

      if (refrescando) {
        return accessTokenRefrescado$.pipe(
          filter((token): token is string => token !== null),
          take(1),
          switchMap((token) =>
            next(peticion.clone({ setHeaders: { Authorization: `Bearer ${token}` } })),
          ),
        );
      }

      refrescando = true;
      accessTokenRefrescado$.next(null);

      return from(authService.refrescar()).pipe(
        switchMap((nuevoToken) => {
          refrescando = false;
          accessTokenRefrescado$.next(nuevoToken);
          return next(peticion.clone({ setHeaders: { Authorization: `Bearer ${nuevoToken}` } }));
        }),
        catchError((errorRefresco: unknown) => {
          refrescando = false;
          authService.limpiarSesion();
          // `.navigate()` puede rechazar (p. ej. navegación cancelada por otro guard);
          // eso nunca debe quedar como un rechazo sin manejar.
          router
            .navigate(['/auth/login'], { queryParams: { returnUrl: router.url } })
            .catch(() => undefined);
          return throwError(() => errorRefresco);
        }),
      );
    }),
  );
};
