import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { ApiService, ParametrosConsulta } from '../../../core/api/api.service';
import {
  AsignacionRecurso,
  EntregableHito,
  FaseProyecto,
  Hito,
  Proyecto,
  RespuestaPaginada,
  RubroPresupuesto,
} from '../../../core/models';
import { FilaCronograma } from '../../tareas/data/tareas.model';
import {
  ComparativoEjecucion,
  ExpedienteProyecto,
  FiltrosProyecto,
  ProyectoDetalle,
  ProyectoEscritura,
  ProyectoLista,
} from './proyectos.model';

@Injectable({ providedIn: 'root' })
export class ProyectosService extends ApiService<Proyecto> {
  protected readonly recurso = 'proyectos';

  listarProyectos(filtros?: FiltrosProyecto): Observable<RespuestaPaginada<ProyectoLista>> {
    return this.listar<ProyectoLista>(filtros as Record<string, string | number | boolean | undefined | null>);
  }

  obtenerDetalle(id: string): Observable<ProyectoDetalle> {
    return this.obtener<ProyectoDetalle>(id);
  }

  crearProyecto(cuerpo: ProyectoEscritura): Observable<ProyectoDetalle> {
    return this.crear(cuerpo as Partial<Proyecto>) as unknown as Observable<ProyectoDetalle>;
  }

  actualizarProyecto(id: string, cuerpo: Partial<ProyectoEscritura>): Observable<ProyectoDetalle> {
    return this.actualizar(id, cuerpo as Partial<Proyecto>) as unknown as Observable<ProyectoDetalle>;
  }

  cambiarEstado(id: string, estado: string, observacion: string): Observable<ProyectoDetalle> {
    return this.accion<ProyectoDetalle>(id, 'cambiar-estado', { estado, observacion });
  }

  fases(id: string): Observable<FaseProyecto[]> {
    return this.accionGet<FaseProyecto[]>(id, 'fases');
  }

  /** Reemplaza toda la lista de fases activas en una sola transacción: la
   * suma de `peso` se valida una sola vez al final, no en cada fila (ver
   * docs/plan/fase-05-proyectos-presupuesto.md, adenda) — por eso no hay
   * un `crear`/`actualizar` fila por fila para fases desde esta pantalla. */
  guardarFasesLote(id: string, fases: unknown[]): Observable<FaseProyecto[]> {
    return this.accion<FaseProyecto[]>(id, 'fases/guardar-lote', { fases });
  }

  hitos(id: string): Observable<Hito[]> {
    return this.accionGet<Hito[]>(id, 'hitos');
  }

  rubros(id: string): Observable<RubroPresupuesto[]> {
    return this.accionGet<RubroPresupuesto[]>(id, 'rubros');
  }

  recursosPlaneados(id: string): Observable<AsignacionRecurso[]> {
    return this.accionGet<AsignacionRecurso[]>(id, 'recursos-planeados');
  }

  cronograma(id: string): Observable<FilaCronograma[]> {
    return this.accionGet<FilaCronograma[]>(id, 'cronograma');
  }

  ejecucion(id: string): Observable<ComparativoEjecucion> {
    return this.accionGet<ComparativoEjecucion>(id, 'ejecucion');
  }

  expediente(id: string, parametros?: ParametrosConsulta): Observable<ExpedienteProyecto> {
    return this.accionGet<ExpedienteProyecto>(id, 'expediente', parametros);
  }

  /** La exportación siempre pasa por este endpoint autenticado (nunca un
   * enlace directo): se descarga como blob y se entrega con
   * `URL.createObjectURL` desde el componente. */
  exportarExpediente(id: string): Observable<Blob> {
    return this.http.get(`${environment.apiBaseUrl}/proyectos/${id}/expediente/exportar/`, {
      responseType: 'blob',
    });
  }
}

@Injectable({ providedIn: 'root' })
export class FasesProyectoService extends ApiService<FaseProyecto> {
  protected readonly recurso = 'fases-proyecto';
}

@Injectable({ providedIn: 'root' })
export class HitosService extends ApiService<Hito> {
  protected readonly recurso = 'hitos';
}

@Injectable({ providedIn: 'root' })
export class EntregablesHitoService extends ApiService<EntregableHito> {
  protected readonly recurso = 'entregables-hito';
}

@Injectable({ providedIn: 'root' })
export class RubrosPresupuestoService extends ApiService<RubroPresupuesto> {
  protected readonly recurso = 'rubros-presupuesto';
}
