import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import {
  EjecucionMensualTablero,
  FiltrosTablero,
  RecursosTablero,
  ResumenGlobalTablero,
  ResumenTareasTablero,
  TablaProyectosTablero,
} from '../../../core/models';

export type VistaExportarTablero = 'proyectos' | 'recursos' | 'ejecucion-mensual';

/** Los seis endpoints de `docs/api-contrato.md §7` no son un CRUD de un
 * recurso (no hay modelo propio: todo es agregación de solo lectura), así
 * que este servicio llama a `HttpClient` directamente en vez de extender
 * `ApiService<T>`. */
@Injectable({ providedIn: 'root' })
export class TableroService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/tablero`;

  private parametros(filtros?: FiltrosTablero): HttpParams {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros ?? {})) {
      if (valor !== undefined && valor !== null && valor !== '') {
        params = params.set(clave, String(valor));
      }
    }
    return params;
  }

  resumen(filtros?: FiltrosTablero): Observable<ResumenGlobalTablero> {
    return this.http.get<ResumenGlobalTablero>(`${this.base}/resumen/`, {
      params: this.parametros(filtros),
    });
  }

  proyectos(filtros?: FiltrosTablero): Observable<TablaProyectosTablero> {
    return this.http.get<TablaProyectosTablero>(`${this.base}/proyectos/`, {
      params: this.parametros(filtros),
    });
  }

  ejecucionMensual(filtros?: FiltrosTablero): Observable<EjecucionMensualTablero> {
    return this.http.get<EjecucionMensualTablero>(`${this.base}/ejecucion-mensual/`, {
      params: this.parametros(filtros),
    });
  }

  recursos(filtros?: FiltrosTablero): Observable<RecursosTablero> {
    return this.http.get<RecursosTablero>(`${this.base}/recursos/`, {
      params: this.parametros(filtros),
    });
  }

  tareas(filtros?: FiltrosTablero): Observable<ResumenTareasTablero> {
    return this.http.get<ResumenTareasTablero>(`${this.base}/tareas/`, {
      params: this.parametros(filtros),
    });
  }

  exportarCsv(vista: VistaExportarTablero, filtros?: FiltrosTablero): Observable<Blob> {
    const params = this.parametros(filtros).set('formato', 'csv').set('vista', vista);
    return this.http.get(`${this.base}/exportar/`, { params, responseType: 'blob' });
  }
}
