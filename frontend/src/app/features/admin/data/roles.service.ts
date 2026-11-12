import { Injectable } from '@angular/core';

import { ApiService } from '../../../core/api/api.service';
import { RolMeta } from '../../../core/models';

/** Lectura: cualquier autenticado puede ver la lista (`EsAdminOSoloLectura`);
 * escritura: solo ADMIN. Un rol de sistema (`es_sistema`) no se puede borrar
 * (docs/api-contrato.md §8). */
@Injectable({ providedIn: 'root' })
export class RolesService extends ApiService<RolMeta> {
  protected readonly recurso = 'roles';
}
