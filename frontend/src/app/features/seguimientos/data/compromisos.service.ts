import { Injectable } from '@angular/core';

import { ApiService } from '../../../core/api/api.service';
import { CompromisoSeguimiento } from '../../../core/models';

export interface CompromisoEscritura {
  seguimiento: string;
  descripcion: string;
  responsable: string;
  fecha_compromiso: string;
  estado?: string;
  fecha_cumplimiento?: string | null;
}

export interface FiltrosCompromiso {
  estado?: string;
  responsable?: string;
  vencidos?: boolean;
  page?: number;
  page_size?: number;
}

@Injectable({ providedIn: 'root' })
export class CompromisosService extends ApiService<CompromisoSeguimiento> {
  protected readonly recurso = 'compromisos-seguimiento';
}
