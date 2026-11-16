import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { RutaActualService } from '../../core/ui/ruta-actual.service';
import { ContadorAprobacionesService } from '../../features/ejecucion/data/contador-aprobaciones.service';
import { ITEMS_MENU } from '../menu.config';

const CLAVE_COLAPSADO = 'sp_menu_colapsado';

function leerColapsado(): boolean {
  try {
    return localStorage.getItem(CLAVE_COLAPSADO) === 'true';
  } catch {
    return false;
  }
}

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
})
export class Sidebar {
  private readonly auth = inject(AuthService);
  private readonly rutaActual = inject(RutaActualService);
  protected readonly contadorAprobaciones = inject(ContadorAprobacionesService);

  readonly colapsado = signal(leerColapsado());

  protected readonly items = computed(() =>
    ITEMS_MENU.filter((item) => {
      if (!item.permiso && !item.permisos) return true;
      if (item.permiso) return this.auth.tienePermiso(item.permiso);
      return item.permisos!.some((permiso) => this.auth.tienePermiso(permiso));
    }),
  );

  constructor() {
    this.contadorAprobaciones.actualizar();
  }

  /** Un ítem está activo si la URL es su ruta o cuelga de ella; Ejecución
   * agrupa todas sus subpantallas bajo `/ejecucion`. */
  protected esActivo(ruta: string): boolean {
    const base = ruta.startsWith('/ejecucion') ? '/ejecucion' : ruta;
    const url = this.rutaActual.url().split(/[?#]/)[0];
    return url === base || url.startsWith(`${base}/`);
  }

  protected contadorDe(ruta: string): number {
    return ruta === '/ejecucion/registros' ? this.contadorAprobaciones.cantidad() : 0;
  }

  protected alternarColapso(): void {
    this.colapsado.update((valor) => !valor);
    try {
      localStorage.setItem(CLAVE_COLAPSADO, String(this.colapsado()));
    } catch {
      // almacenamiento no disponible: el estado solo vive en memoria
    }
  }
}
