import { HttpClient, HttpEvent, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { DocumentoExpediente, RespuestaPaginada } from '../../../core/models';

export interface MetadatosDocumento {
  proyecto: string;
  seguimiento?: string | null;
  tarea?: string | null;
  categoria: string;
  nombre: string;
  descripcion?: string;
}

export interface FiltrosDocumento {
  proyecto?: string;
  categoria?: string;
  seguimiento?: string;
  tarea?: string;
  page?: number;
  page_size?: number;
}

/** No extiende `ApiService<T>`: la subida necesita `reportProgress: true`
 * con `observe: 'events'` para la barra de progreso real
 * (docs/plan/fase-09-seguimiento-expediente.md §9.4.13), algo que la
 * envoltura genérica no modela. */
@Injectable({ providedIn: 'root' })
export class DocumentosService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/documentos-expediente/`;

  listar(filtros?: FiltrosDocumento): Observable<RespuestaPaginada<DocumentoExpediente>> {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros ?? {})) {
      if (valor !== undefined && valor !== null && valor !== '') {
        params = params.set(clave, String(valor));
      }
    }
    return this.http.get<RespuestaPaginada<DocumentoExpediente>>(this.base, { params });
  }

  obtener(id: string): Observable<DocumentoExpediente> {
    return this.http.get<DocumentoExpediente>(`${this.base}${id}/`);
  }

  /** Emite eventos de progreso (`HttpEventType.UploadProgress`) y termina
   * con el documento creado (`HttpEventType.Response`). */
  subir(metadatos: MetadatosDocumento, archivo: File): Observable<HttpEvent<DocumentoExpediente>> {
    const formulario = this._formulario(metadatos, archivo);
    return this.http.post<DocumentoExpediente>(this.base, formulario, {
      reportProgress: true,
      observe: 'events',
    });
  }

  nuevaVersion(id: string, archivo: File): Observable<HttpEvent<DocumentoExpediente>> {
    const formulario = new FormData();
    formulario.append('archivo', archivo);
    return this.http.post<DocumentoExpediente>(`${this.base}${id}/nueva-version/`, formulario, {
      reportProgress: true,
      observe: 'events',
    });
  }

  actualizarMetadatos(
    id: string,
    cuerpo: Partial<MetadatosDocumento>,
  ): Observable<DocumentoExpediente> {
    return this.http.patch<DocumentoExpediente>(`${this.base}${id}/`, cuerpo);
  }

  eliminar(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}${id}/`);
  }

  /** La descarga siempre pasa por este endpoint autenticado: nunca se
   * construye un enlace directo a `MEDIA_ROOT` (docs/plan/fase-09 §9.4.14). */
  descargar(id: string): Observable<Blob> {
    return this.http.get(`${this.base}${id}/descargar/`, { responseType: 'blob' });
  }

  private _formulario(metadatos: MetadatosDocumento, archivo: File): FormData {
    const formulario = new FormData();
    formulario.append('proyecto', metadatos.proyecto);
    if (metadatos.seguimiento) formulario.append('seguimiento', metadatos.seguimiento);
    if (metadatos.tarea) formulario.append('tarea', metadatos.tarea);
    formulario.append('categoria', metadatos.categoria);
    formulario.append('nombre', metadatos.nombre);
    formulario.append('descripcion', metadatos.descripcion ?? '');
    formulario.append('archivo', archivo);
    return formulario;
  }
}
