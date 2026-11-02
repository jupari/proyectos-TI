import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { AsignacionRecurso, RespuestaPaginada } from '../../../core/models';

export interface AsignacionEscritura {
  proyecto: string;
  recurso: string;
  fase: string | null;
  rol_en_proyecto: string;
  fecha_desde: string;
  fecha_hasta: string;
  porcentaje_dedicacion: number | string;
  horas_planeadas: number | string;
  valor_hora_plan?: number | string;
}

export interface RespuestaAsignacion extends AsignacionRecurso {
  advertencias: string[];
}

export interface FiltrosAsignacion {
  proyecto?: string;
  recurso?: string;
  fase?: string;
}

/** No extiende `ApiService<T>` porque sus respuestas de escritura traen
 * `advertencias` además de los campos del modelo (docs/api-contrato.md §5). */
@Injectable({ providedIn: 'root' })
export class AsignacionesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/asignaciones/`;

  listar(filtros?: FiltrosAsignacion): Observable<RespuestaPaginada<AsignacionRecurso>> {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros ?? {})) {
      if (valor) params = params.set(clave, valor);
    }
    return this.http.get<RespuestaPaginada<AsignacionRecurso>>(this.base, { params });
  }

  crear(cuerpo: AsignacionEscritura): Observable<RespuestaAsignacion> {
    return this.http.post<RespuestaAsignacion>(this.base, cuerpo);
  }

  actualizar(id: string, cuerpo: Partial<AsignacionEscritura>): Observable<RespuestaAsignacion> {
    return this.http.patch<RespuestaAsignacion>(`${this.base}${id}/`, cuerpo);
  }

  eliminar(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}${id}/`);
  }
}
