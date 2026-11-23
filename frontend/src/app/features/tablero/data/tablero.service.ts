import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import {
  BurndownSprint,
  EjecucionMensualTablero,
  FiltrosTablero,
  MiTrabajo,
  PlanCostosProyecto,
  RecursosTablero,
  ResumenGlobalTablero,
  ResumenTareasTablero,
  SprintsProyecto,
  TablaProyectosPorPeriodoTablero,
  TablaProyectosTablero,
} from '../../../core/models';

export type VistaExportarTablero =
  | 'proyectos'
  | 'recursos'
  | 'ejecucion-mensual'
  | 'proyectos-por-periodo'
  | 'plan-costos';

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

  proyectosPorPeriodo(filtros?: FiltrosTablero): Observable<TablaProyectosPorPeriodoTablero> {
    return this.http.get<TablaProyectosPorPeriodoTablero>(`${this.base}/proyectos-por-periodo/`, {
      params: this.parametros(filtros),
    });
  }

  sprintsDelProyecto(proyectoId: string): Observable<SprintsProyecto> {
    return this.http.get<SprintsProyecto>(`${this.base}/sprints/`, {
      params: { proyecto: proyectoId },
    });
  }

  burndownDelSprint(sprintId: string): Observable<BurndownSprint> {
    return this.http.get<BurndownSprint>(`${this.base}/sprints/${sprintId}/burndown/`);
  }

  miTrabajo(): Observable<MiTrabajo> {
    return this.http.get<MiTrabajo>(`${this.base}/mi-trabajo/`);
  }

  recursos(filtros?: FiltrosTablero): Observable<RecursosTablero> {
    return this.http.get<RecursosTablero>(`${this.base}/recursos/`, {
      params: this.parametros(filtros),
    });
  }

  planCostos(filtros: FiltrosTablero): Observable<PlanCostosProyecto> {
    return this.http.get<PlanCostosProyecto>(`${this.base}/plan-costos/`, {
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
