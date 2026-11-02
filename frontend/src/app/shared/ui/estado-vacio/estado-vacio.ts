import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Boton } from '../boton/boton';

@Component({
  selector: 'app-estado-vacio',
  templateUrl: './estado-vacio.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Boton],
})
export class EstadoVacio {
  readonly mensaje = input('No hay datos para mostrar.');
  readonly textoAccion = input<string>('');

  readonly accion = output<void>();
}
