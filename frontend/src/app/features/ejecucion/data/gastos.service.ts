import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../../../core/api/api.service';
import { GastoEjecutado } from '../../../core/models';

export interface GastoEjecutadoEscritura {
  proyecto: string;
  rubro: string;
  fecha: string;
  monto: number | string;
  proveedor: string;
  numero_documento: string;
  descripcion: string;
}

@Injectable({ providedIn: 'root' })
export class GastosService extends ApiService<GastoEjecutado> {
  protected readonly recurso = 'gastos-ejecutados';

  crearGasto(cuerpo: GastoEjecutadoEscritura): Observable<GastoEjecutado> {
    return this.crear(cuerpo as unknown as Partial<GastoEjecutado>);
  }

  actualizarGasto(id: string, cuerpo: Partial<GastoEjecutadoEscritura>): Observable<GastoEjecutado> {
    return this.actualizar(id, cuerpo as unknown as Partial<GastoEjecutado>);
  }

  enviar(id: string): Observable<GastoEjecutado> {
    return this.accion<GastoEjecutado>(id, 'enviar');
  }

  aprobar(id: string): Observable<GastoEjecutado> {
    return this.accion<GastoEjecutado>(id, 'aprobar');
  }

  rechazar(id: string, motivoRechazo: string): Observable<GastoEjecutado> {
    return this.accion<GastoEjecutado>(id, 'rechazar', { motivo_rechazo: motivoRechazo });
  }

  reabrir(id: string): Observable<GastoEjecutado> {
    return this.accion<GastoEjecutado>(id, 'reabrir');
  }
}
