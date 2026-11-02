import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { ApiService } from '../../../core/api/api.service';
import { RespuestaPaginada, Seguimiento } from '../../../core/models';
import { FiltrosSeguimiento, PrecargaSeguimiento, SeguimientoEscritura } from './seguimientos.model';

@Injectable({ providedIn: 'root' })
export class SeguimientosService extends ApiService<Seguimiento> {
  protected readonly recurso = 'seguimientos';

  listarSeguimientos(filtros?: FiltrosSeguimiento): Observable<RespuestaPaginada<Seguimiento>> {
    return this.listar<Seguimiento>(
      filtros as Record<string, string | number | boolean | undefined | null>,
    );
  }

  obtenerDetalle(id: string): Observable<Seguimiento> {
    return this.obtener<Seguimiento>(id);
  }

  crearSeguimiento(cuerpo: SeguimientoEscritura): Observable<Seguimiento> {
    return this.crear(cuerpo as Partial<Seguimiento>);
  }

  actualizarSeguimiento(
    id: string,
    cuerpo: Partial<SeguimientoEscritura>,
  ): Observable<Seguimiento> {
    return this.actualizar(id, cuerpo as Partial<Seguimiento>);
  }

  /** `POST /seguimientos/precargar/`: no es un sub-recurso de detalle (no
   * hay `{id}` en la ruta), así que no se puede expresar con `accion()`. */
  precargar(
    proyecto: string,
    periodicidad: string,
    periodoInicio: string,
  ): Observable<PrecargaSeguimiento> {
    return this.http.post<PrecargaSeguimiento>(`${environment.apiBaseUrl}/seguimientos/precargar/`, {
      proyecto,
      periodicidad,
      periodo_inicio: periodoInicio,
    });
  }

  publicar(id: string): Observable<Seguimiento> {
    return this.accion<Seguimiento>(id, 'publicar');
  }

  reabrir(id: string): Observable<Seguimiento> {
    return this.accion<Seguimiento>(id, 'reabrir');
  }
}
