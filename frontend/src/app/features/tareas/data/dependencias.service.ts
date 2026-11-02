import { Injectable } from '@angular/core';

import { ApiService } from '../../../core/api/api.service';
import { DependenciaTarea, TipoDependencia } from '../../../core/models';

export interface DependenciaTareaEscritura {
  tarea_origen: string;
  tarea_destino: string;
  tipo: TipoDependencia;
  dias_desfase: number;
}

@Injectable({ providedIn: 'root' })
export class DependenciasService extends ApiService<DependenciaTarea> {
  protected readonly recurso = 'dependencias-tarea';
}
