import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { CargandoService } from '../core/ui/cargando.service';
import { Confirmacion } from '../shared/ui/confirmacion/confirmacion';
import { Toast } from '../shared/ui/toast/toast';
import { Breadcrumbs } from './breadcrumbs/breadcrumbs';
import { Sidebar } from './sidebar/sidebar';
import { Topbar } from './topbar/topbar';

@Component({
  selector: 'app-shell',
  templateUrl: './shell.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, Topbar, Sidebar, Breadcrumbs, Toast, Confirmacion],
})
export class Shell {
  protected readonly cargando = inject(CargandoService);
}
