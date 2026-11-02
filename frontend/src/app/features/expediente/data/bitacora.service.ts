import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { EntradaBitacora, RespuestaPaginada } from '../../../core/models';

export interface FiltrosBitacora {
  proyecto?: string;
  tipo_evento?: string;
  entidad?: string;
  entidad_id?: string;
  usuario?: string;
  desde?: string;
  hasta?: string;
  page?: number;
  page_size?: number;
}

@Injectable({ providedIn: 'root' })
export class BitacoraService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/bitacora/`;

  listar(filtros?: FiltrosBitacora): Observable<RespuestaPaginada<EntradaBitacora>> {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros ?? {})) {
      if (valor !== undefined && valor !== null && valor !== '') {
        params = params.set(clave, String(valor));
      }
    }
    return this.http.get<RespuestaPaginada<EntradaBitacora>>(this.base, { params });
  }
}
