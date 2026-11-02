import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../../../core/api/api.service';
import { AsignacionRecurso, Recurso, RespuestaPaginada, TarifaRecurso } from '../../../core/models';
import { CargaMensual, FiltrosRecurso, RecursoEscritura, RecursoLista } from './recursos.model';

@Injectable({ providedIn: 'root' })
export class RecursosService extends ApiService<Recurso> {
  protected readonly recurso = 'recursos';

  listarRecursos(filtros?: FiltrosRecurso): Observable<RespuestaPaginada<RecursoLista>> {
    return this.listar<RecursoLista>(filtros as Record<string, string | number | boolean | undefined | null>);
  }

  obtenerDetalle(id: string): Observable<RecursoLista> {
    return this.obtener<RecursoLista>(id);
  }

  crearRecurso(cuerpo: RecursoEscritura): Observable<RecursoLista> {
    return this.crear(cuerpo as Partial<Recurso>) as unknown as Observable<RecursoLista>;
  }

  actualizarRecurso(id: string, cuerpo: Partial<RecursoEscritura>): Observable<RecursoLista> {
    return this.actualizar(id, cuerpo as Partial<Recurso>) as unknown as Observable<RecursoLista>;
  }

  tarifas(id: string): Observable<TarifaRecurso[]> {
    return this.accionGet<TarifaRecurso[]>(id, 'tarifas');
  }

  carga(id: string, desde: string, hasta: string): Observable<CargaMensual[]> {
    return this.accionGet<CargaMensual[]>(id, 'carga', { desde, hasta });
  }

  asignaciones(id: string): Observable<AsignacionRecurso[]> {
    return this.accionGet<AsignacionRecurso[]>(id, 'asignaciones');
  }
}
