import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type ValorSemaforo = 'VERDE' | 'AMARILLO' | 'ROJO';

const CLASES: Record<ValorSemaforo, string> = {
  VERDE: 'bg-semaforo-verde',
  AMARILLO: 'bg-semaforo-amarillo',
  ROJO: 'bg-semaforo-rojo',
};

const ETIQUETAS: Record<ValorSemaforo, string> = {
  VERDE: 'En curso normal',
  AMARILLO: 'En riesgo',
  ROJO: 'Crítico',
};

/** El color nunca es el único portador de significado: siempre va con el
 * texto de `ETIQUETAS` (visible u oculto para lectores de pantalla). */
@Component({
  selector: 'app-semaforo',
  templateUrl: './semaforo.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Semaforo {
  readonly valor = input.required<ValorSemaforo>();
  readonly mostrarTexto = input(true);

  protected readonly clase = computed(() => CLASES[this.valor()]);
  protected readonly etiqueta = computed(() => ETIQUETAS[this.valor()]);
}
