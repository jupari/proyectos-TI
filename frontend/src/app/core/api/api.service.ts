import { HttpClient, HttpParams } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { RespuestaPaginada } from '../models';

export type ParametrosConsulta = Record<string, string | number | boolean | undefined | null>;

/**
 * Envoltura genérica tipada sobre `HttpClient`. Los servicios de cada
 * feature la extienden fijando `recurso`; ningún componente llama a
 * `HttpClient` directamente.
 */
export abstract class ApiService<T> {
  protected readonly http = inject(HttpClient);
  protected abstract readonly recurso: string;

  private get base(): string {
    return `${environment.apiBaseUrl}/${this.recurso}/`;
  }

  private construirParametros(parametros?: ParametrosConsulta): HttpParams {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(parametros ?? {})) {
      if (valor !== undefined && valor !== null) {
        params = params.set(clave, String(valor));
      }
    }
    return params;
  }

  /** `R` permite tipar listados cuyo serializer de lectura expone más
   * campos que el modelo base (p. ej. nombres resueltos, `resumen_ejecucion`). */
  listar<R = T>(parametros?: ParametrosConsulta): Observable<RespuestaPaginada<R>> {
    return this.http.get<RespuestaPaginada<R>>(this.base, {
      params: this.construirParametros(parametros),
    });
  }

  obtener<R = T>(id: string): Observable<R> {
    return this.http.get<R>(`${this.base}${id}/`);
  }

  crear(cuerpo: Partial<T>): Observable<T> {
    return this.http.post<T>(this.base, cuerpo);
  }

  actualizar(id: string, cuerpo: Partial<T>): Observable<T> {
    return this.http.patch<T>(`${this.base}${id}/`, cuerpo);
  }

  eliminar(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}${id}/`);
  }

  accion<R = T>(id: string, nombre: string, cuerpo?: unknown): Observable<R> {
    return this.http.post<R>(`${this.base}${id}/${nombre}/`, cuerpo ?? {});
  }

  /** Sub-recurso de solo lectura bajo el detalle (p. ej. `/proyectos/{id}/fases/`). */
  accionGet<R = T>(id: string, nombre: string): Observable<R> {
    return this.http.get<R>(`${this.base}${id}/${nombre}/`);
  }
}
