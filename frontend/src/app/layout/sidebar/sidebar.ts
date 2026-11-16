import { ChangeDetectionStrategy, Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { PantallaService } from '../../core/ui/pantalla.service';
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

/**
 * Escritorio: menú fijo, colapsable (se recuerda). Tableta: riel de iconos que
 * se puede expandir. Móvil: cajón que se abre desde la barra superior.
 */
@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
})
export class Sidebar {
  private readonly auth = inject(AuthService);
  private readonly rutaActual = inject(RutaActualService);
  protected readonly pantalla = inject(PantallaService);
  protected readonly contadorAprobaciones = inject(ContadorAprobacionesService);

  private readonly colapsadoEscritorio = signal(leerColapsado());
  private readonly expandidoTableta = signal(false);

  /** Solo el escritorio/tableta colapsan; en el cajón móvil siempre se ven las etiquetas. */
  readonly colapsado = computed(() => {
    switch (this.pantalla.tipo()) {
      case 'escritorio':
        return this.colapsadoEscritorio();
      case 'tableta':
        return !this.expandidoTableta();
      default:
        return false;
    }
  });

  protected readonly items = computed(() =>
    ITEMS_MENU.filter((item) => {
      if (!item.permiso && !item.permisos) return true;
      if (item.permiso) return this.auth.tienePermiso(item.permiso);
      return item.permisos!.some((permiso) => this.auth.tienePermiso(permiso));
    }),
  );

  constructor() {
    this.contadorAprobaciones.actualizar();
    effect(() => {
      this.rutaActual.url();
      untracked(() => this.pantalla.menuMovilAbierto.set(false));
    });
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
    if (this.pantalla.tipo() === 'tableta') {
      this.expandidoTableta.update((valor) => !valor);
      return;
    }
    this.colapsadoEscritorio.update((valor) => !valor);
    try {
      localStorage.setItem(CLAVE_COLAPSADO, String(this.colapsadoEscritorio()));
    } catch {
      // almacenamiento no disponible: el estado solo vive en memoria
    }
  }

  protected cerrarMovil(): void {
    this.pantalla.menuMovilAbierto.set(false);
  }
}
