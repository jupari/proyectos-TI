import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { RegistroEjecucion, RespuestaPaginada } from '../../../core/models';

export interface RegistroEjecucionEscritura {
  proyecto: string;
  tarea: string | null;
  recurso: string;
  periodicidad: string;
  periodo_inicio: string;
  horas: number | string;
  descripcion: string;
  valor_hora_aplicado?: number | string;
}

export interface RespuestaRegistroEjecucion extends RegistroEjecucion {
  advertencias: string[];
}

export interface FiltrosRegistroEjecucion {
  search?: string;
  proyecto?: string;
  tarea?: string;
  recurso?: string;
  periodicidad?: string;
  estado_aprobacion?: string;
  periodo_inicio__gte?: string;
  periodo_fin__lte?: string;
  mis_registros?: boolean;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface RespuestaLote {
  creados: number;
  errores: { indice: number; detalle: unknown }[];
}

export interface FilaResumenEjecucion {
  recurso?: string;
  recurso_nombre?: string;
  tarea?: string | null;
  tarea_codigo?: string | null;
  anio?: number;
  mes?: number;
  horas: number;
  costo: number;
}

/** No extiende `ApiService<T>` porque sus respuestas de escritura traen
 * `advertencias` además de los campos del modelo, igual que
 * `AsignacionesService` (docs/plan/fase-08-ejecucion-ingesta.md §8.2). */
@Injectable({ providedIn: 'root' })
export class RegistrosEjecucionService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/registros-ejecucion/`;

  private construirParametros(filtros?: FiltrosRegistroEjecucion): HttpParams {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros ?? {})) {
      if (valor !== undefined && valor !== null && valor !== '') {
        params = params.set(clave, String(valor));
      }
    }
    return params;
  }

  listar(filtros?: FiltrosRegistroEjecucion): Observable<RespuestaPaginada<RegistroEjecucion>> {
    return this.http.get<RespuestaPaginada<RegistroEjecucion>>(this.base, {
      params: this.construirParametros(filtros),
    });
  }

  crear(cuerpo: RegistroEjecucionEscritura): Observable<RespuestaRegistroEjecucion> {
    return this.http.post<RespuestaRegistroEjecucion>(this.base, cuerpo);
  }

  actualizar(
    id: string,
    cuerpo: Partial<RegistroEjecucionEscritura>,
  ): Observable<RespuestaRegistroEjecucion> {
    return this.http.patch<RespuestaRegistroEjecucion>(`${this.base}${id}/`, cuerpo);
  }

  enviar(id: string): Observable<RegistroEjecucion> {
    return this.http.post<RegistroEjecucion>(`${this.base}${id}/enviar/`, {});
  }

  aprobar(id: string): Observable<RegistroEjecucion> {
    return this.http.post<RegistroEjecucion>(`${this.base}${id}/aprobar/`, {});
  }

  rechazar(id: string, motivoRechazo: string): Observable<RegistroEjecucion> {
    return this.http.post<RegistroEjecucion>(`${this.base}${id}/rechazar/`, {
      motivo_rechazo: motivoRechazo,
    });
  }

  reabrir(id: string): Observable<RegistroEjecucion> {
    return this.http.post<RegistroEjecucion>(`${this.base}${id}/reabrir/`, {});
  }

  lote(registros: RegistroEjecucionEscritura[]): Observable<RespuestaLote> {
    return this.http.post<RespuestaLote>(`${this.base}lote/`, { registros });
  }

  resumen(proyectoId: string, agruparPor: 'recurso' | 'tarea' | 'mes'): Observable<FilaResumenEjecucion[]> {
    return this.http.get<FilaResumenEjecucion[]>(`${this.base}resumen/`, {
      params: { proyecto: proyectoId, agrupar_por: agruparPor },
    });
  }
}
