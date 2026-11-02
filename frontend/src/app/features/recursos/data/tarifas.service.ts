import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { TarifaRecurso } from '../../../core/models';

export interface TarifaRecursoEscritura {
  recurso: string;
  valor_hora: number | string;
  moneda: string;
  vigente_desde: string;
  vigente_hasta: string | null;
}

export interface RespuestaTarifa extends TarifaRecurso {
  avisos: string[];
}

/** No extiende `ApiService<T>` porque sus respuestas de escritura traen
 * `avisos` además de los campos del modelo (docs/plan/fase-06 §6.1). */
@Injectable({ providedIn: 'root' })
export class TarifasRecursoService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/tarifas-recurso/`;

  crear(cuerpo: TarifaRecursoEscritura): Observable<RespuestaTarifa> {
    return this.http.post<RespuestaTarifa>(this.base, cuerpo);
  }

  actualizar(id: string, cuerpo: Partial<TarifaRecursoEscritura>): Observable<RespuestaTarifa> {
    return this.http.patch<RespuestaTarifa>(`${this.base}${id}/`, cuerpo);
  }

  eliminar(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}${id}/`);
  }
}
