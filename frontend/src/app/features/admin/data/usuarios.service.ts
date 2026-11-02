import { Injectable } from '@angular/core';

import { ApiService } from '../../../core/api/api.service';
import { Usuario } from '../../../core/models';

/** Lectura: ADMIN y PMO (docs/api-contrato.md §8); lo usa el formulario de
 * proyecto para elegir gerente y líder técnico. */
@Injectable({ providedIn: 'root' })
export class UsuariosService extends ApiService<Usuario> {
  protected readonly recurso = 'usuarios';
}
