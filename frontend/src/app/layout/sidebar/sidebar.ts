import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { ITEMS_MENU } from '../menu.config';

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive],
})
export class Sidebar {
  private readonly auth = inject(AuthService);

  readonly colapsado = signal(false);

  protected readonly items = computed(() =>
    ITEMS_MENU.filter((item) => {
      if (!item.permiso && !item.permisos) return true;
      if (item.permiso) return this.auth.tienePermiso(item.permiso);
      return item.permisos!.some((permiso) => this.auth.tienePermiso(permiso));
    }),
  );

  protected alternarColapso(): void {
    this.colapsado.update((valor) => !valor);
  }
}
