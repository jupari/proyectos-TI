import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { Boton } from '../boton/boton';
import { Modal } from '../modal/modal';

/** Diálogo de confirmación basado en `ConfirmacionService` (promesa +
 * signal); se monta una sola vez en el shell. */
@Component({
  selector: 'app-confirmacion',
  templateUrl: './confirmacion.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Modal, Boton],
})
export class Confirmacion {
  protected readonly servicio = inject(ConfirmacionService);

  protected responder(confirmado: boolean): void {
    this.servicio.responder(confirmado);
  }
}
