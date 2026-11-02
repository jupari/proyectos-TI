import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { ApiService, ParametrosConsulta } from '../../../core/api/api.service';
import { RespuestaPaginada, Tarea } from '../../../core/models';
import {
  FechasSugeridas,
  FiltrosTarea,
  NodoArbolTarea,
  TareaDetalle,
  TareaEscritura,
  TareaLista,
} from './tareas.model';

@Injectable({ providedIn: 'root' })
export class TareasService extends ApiService<Tarea> {
  protected readonly recurso = 'tareas';

  listarTareas(filtros?: FiltrosTarea): Observable<RespuestaPaginada<TareaLista>> {
    return this.listar<TareaLista>(filtros as ParametrosConsulta);
  }

  obtenerDetalle(id: string): Observable<TareaDetalle> {
    return this.obtener<TareaDetalle>(id);
  }

  crearTarea(cuerpo: TareaEscritura): Observable<TareaDetalle> {
    return this.crear(cuerpo as Partial<Tarea>) as unknown as Observable<TareaDetalle>;
  }

  actualizarTarea(id: string, cuerpo: Partial<TareaEscritura>): Observable<TareaDetalle> {
    return this.actualizar(id, cuerpo as Partial<Tarea>) as unknown as Observable<TareaDetalle>;
  }

  cambiarEstado(
    id: string,
    datos: { estado: string; fecha_inicio_real?: string; fecha_fin_real?: string; nota?: string },
  ): Observable<TareaDetalle> {
    return this.accion<TareaDetalle>(id, 'cambiar-estado', datos);
  }

  fechasSugeridas(id: string): Observable<FechasSugeridas> {
    return this.accionGet<FechasSugeridas>(id, 'fechas-sugeridas');
  }

  /** `GET /tareas/arbol/?proyecto=`: a diferencia de las demás acciones de
   * este servicio, no es un sub-recurso de detalle (no hay `{id}` en la
   * ruta), así que no se puede expresar con `accionGet`. */
  arbol(proyectoId: string): Observable<NodoArbolTarea[]> {
    return this.http.get<NodoArbolTarea[]>(`${environment.apiBaseUrl}/tareas/arbol/`, {
      params: this.construirParametros({ proyecto: proyectoId }),
    });
  }
}
