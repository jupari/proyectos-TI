import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '../../../core/api/api.service';
import { Usuario, UsuarioCreado, UsuarioEscritura } from '../../../core/models';

/** Lectura: ADMIN y PMO (docs/api-contrato.md §8); lo usa el formulario de
 * proyecto para elegir gerente y líder técnico. Escritura: solo ADMIN. */
@Injectable({ providedIn: 'root' })
export class UsuariosService extends ApiService<Usuario> {
  protected readonly recurso = 'usuarios';

  crearUsuario(cuerpo: Partial<UsuarioEscritura>): Observable<UsuarioCreado> {
    return this.crear(cuerpo as Partial<Usuario>) as unknown as Observable<UsuarioCreado>;
  }

  actualizarUsuario(id: string, cuerpo: Partial<UsuarioEscritura>): Observable<Usuario> {
    return this.actualizar(id, cuerpo as Partial<Usuario>);
  }

  activar(id: string): Observable<Usuario> {
    return this.accion<Usuario>(id, 'activar');
  }

  desactivar(id: string): Observable<Usuario> {
    return this.accion<Usuario>(id, 'desactivar');
  }
}
