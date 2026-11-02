import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';

import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/auth/auth.service';
import { RespuestaPaginada } from '../../../core/models';

/** Cuenta de `RegistroEjecucion` en `ENVIADO`, para el contador del menú
 * lateral (docs/plan/fase-08-ejecucion-ingesta.md §8.3.9). Solo consulta si
 * el usuario puede aprobar: a los demás no les aporta nada y evitamos una
 * petición de más en cada carga de la aplicación. */
@Injectable({ providedIn: 'root' })
export class ContadorAprobacionesService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  readonly cantidad = signal(0);

  actualizar(): void {
    if (!this.auth.tienePermiso('ejecucion.aprobar')) {
      this.cantidad.set(0);
      return;
    }
    this.http
      .get<RespuestaPaginada<unknown>>(`${environment.apiBaseUrl}/registros-ejecucion/`, {
        params: { estado_aprobacion: 'ENVIADO', page_size: '1' },
      })
      .subscribe({
        next: (respuesta) => this.cantidad.set(respuesta.count),
        error: () => this.cantidad.set(0),
      });
  }
}
