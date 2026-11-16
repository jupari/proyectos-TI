import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

export type VarianteBoton = 'primario' | 'secundario' | 'peligro' | 'fantasma';
export type TamanoBoton = 'sm' | 'md';

const CLASES_VARIANTE: Record<VarianteBoton, string> = {
  primario: 'bg-teal-700 text-white shadow-tarjeta hover:bg-teal-800 focus-visible:ring-teal-500',
  secundario:
    'bg-white text-neutro-700 border border-neutro-300 hover:bg-teal-50 hover:border-teal-300 focus-visible:ring-teal-500',
  peligro: 'bg-peligro text-white hover:brightness-90 focus-visible:ring-peligro',
  fantasma: 'bg-transparent text-neutro-700 hover:bg-teal-50 hover:text-teal-800 focus-visible:ring-teal-500',
};

const CLASES_TAMANO: Record<TamanoBoton, string> = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
};

@Component({
  selector: 'app-boton',
  templateUrl: './boton.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Boton {
  readonly variante = input<VarianteBoton>('primario');
  readonly tamano = input<TamanoBoton>('md');
  readonly cargando = input(false);
  readonly disabled = input(false);
  readonly tipo = input<'button' | 'submit'>('button');
  /** Ancho 100%. Una clase `w-full` puesta en `<app-boton>` no llegaría al
   * `<button>` interno, por eso es un input y no una clase del host. */
  readonly completo = input(false);

  readonly clic = output<MouseEvent>();

  protected readonly clases = computed(
    () =>
      `inline-flex items-center justify-center rounded-panel font-medium transition-colors duration-150 ` +
      `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 ` +
      `disabled:opacity-50 disabled:cursor-not-allowed ` +
      `${CLASES_VARIANTE[this.variante()]} ${CLASES_TAMANO[this.tamano()]} ` +
      `${this.completo() ? 'w-full' : ''}`,
  );

  protected alClic(evento: MouseEvent): void {
    if (!this.disabled() && !this.cargando()) {
      this.clic.emit(evento);
    }
  }
}
