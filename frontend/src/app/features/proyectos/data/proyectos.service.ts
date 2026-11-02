import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../../../core/api/api.service';
import {
  AsignacionRecurso,
  FaseProyecto,
  Hito,
  Proyecto,
  RespuestaPaginada,
  RubroPresupuesto,
} from '../../../core/models';
import { FiltrosProyecto, ProyectoDetalle, ProyectoEscritura, ProyectoLista } from './proyectos.model';

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

  hitos(id: string): Observable<Hito[]> {
    return this.accionGet<Hito[]>(id, 'hitos');
  }

  rubros(id: string): Observable<RubroPresupuesto[]> {
    return this.accionGet<RubroPresupuesto[]>(id, 'rubros');
  }

  recursosPlaneados(id: string): Observable<AsignacionRecurso[]> {
    return this.accionGet<AsignacionRecurso[]>(id, 'recursos-planeados');
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
export class RubrosPresupuestoService extends ApiService<RubroPresupuesto> {
  protected readonly recurso = 'rubros-presupuesto';
}
