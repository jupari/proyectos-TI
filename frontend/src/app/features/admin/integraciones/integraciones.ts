import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ToastService } from '../../../core/ui/toast.service';
import { Card } from '../../../shared/ui/card/card';
import { Switch } from '../../../shared/ui/switch/switch';
import { IntegracionesJiraService } from '../data/integraciones-jira.service';

@Component({
  selector: 'app-integraciones',
  templateUrl: './integraciones.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Card, Switch],
})
export class Integraciones {
  private readonly integracionesJiraService = inject(IntegracionesJiraService);
  private readonly toast = inject(ToastService);

  protected readonly cargando = signal(true);
  protected readonly guardando = signal(false);
  protected readonly autoAprobarImportados = signal(false);

  constructor() {
    this.integracionesJiraService.obtenerConfiguracion().subscribe({
      next: (configuracion) => {
        this.autoAprobarImportados.set(configuracion.auto_aprobar_importados);
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la configuración.' });
        this.cargando.set(false);
      },
    });
  }

  protected cambiarAutoAprobar(valor: boolean): void {
    const anterior = this.autoAprobarImportados();
    this.autoAprobarImportados.set(valor);
    this.guardando.set(true);
    this.integracionesJiraService.actualizarConfiguracion({ auto_aprobar_importados: valor }).subscribe({
      next: () => {
        this.guardando.set(false);
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Configuración guardada.' });
      },
      error: () => {
        this.guardando.set(false);
        this.autoAprobarImportados.set(anterior);
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo guardar la configuración.' });
      },
    });
  }
}
