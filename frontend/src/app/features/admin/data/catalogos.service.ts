import { Injectable } from '@angular/core';

import { ApiService } from '../../../core/api/api.service';
import { Area, PerfilRecurso, Portafolio } from '../../../core/models';

@Injectable({ providedIn: 'root' })
export class AreasService extends ApiService<Area> {
  protected readonly recurso = 'areas';
}

@Injectable({ providedIn: 'root' })
export class PortafoliosService extends ApiService<Portafolio> {
  protected readonly recurso = 'portafolios';
}

@Injectable({ providedIn: 'root' })
export class PerfilesRecursoService extends ApiService<PerfilRecurso> {
  protected readonly recurso = 'perfiles-recurso';
}
