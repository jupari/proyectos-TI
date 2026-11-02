import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { ToastService, TipoToast } from '../../../core/ui/toast.service';

const ICONO_POR_TIPO: Record<TipoToast, string> = {
  exito: '✓',
  alerta: '!',
  error: '✕',
  info: 'i',
};

const CLASES_POR_TIPO: Record<TipoToast, string> = {
  exito: 'border-exito/30 text-exito',
  alerta: 'border-alerta/30 text-alerta',
  error: 'border-peligro/30 text-peligro',
  info: 'border-marca-300 text-marca-700',
};

/** Pila de notificaciones; se monta una sola vez en el shell y lee
 * `ToastService.mensajes`. */
@Component({
  selector: 'app-toast',
  templateUrl: './toast.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Toast {
  protected readonly servicio = inject(ToastService);
  protected readonly icono = ICONO_POR_TIPO;
  protected readonly clase = CLASES_POR_TIPO;
}
