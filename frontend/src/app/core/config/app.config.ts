import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection,
} from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';

import { routes } from '../../app.routes';
import { AuthService } from '../auth/auth.service';
import { authInterceptor } from '../http/auth.interceptor';
import { cargandoInterceptor } from '../http/cargando.interceptor';
import { errorInterceptor } from '../http/error.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(withInterceptors([authInterceptor, errorInterceptor, cargandoInterceptor])),
    provideAppInitializer(() => inject(AuthService).restaurarSesion()),
  ],
};
