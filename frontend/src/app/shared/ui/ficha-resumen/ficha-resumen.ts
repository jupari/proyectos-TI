import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type TonoFicha = 'neutro' | 'primario' | 'exito' | 'alerta' | 'peligro';

const PUNTO: Record<TonoFicha, string> = {
  neutro: 'bg-neutro-400',
  primario: 'bg-primario-500',
  exito: 'bg-exito',
  alerta: 'bg-alerta',
  peligro: 'bg-peligro',
};

/** Ficha de "lectura rápida": cifra grande, etiqueta chica y un punto de
 * color que indica de qué tipo de dato se trata. La cifra es el foco. */
@Component({
  selector: 'app-ficha-resumen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex h-full flex-col gap-1 rounded-panel border border-neutro-200 bg-surface px-4 py-3">
      <p class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-neutro-500">
        <span class="h-1.5 w-1.5 rounded-full" [class]="punto()"></span>
        {{ etiqueta() }}
      </p>
      <p class="text-[1.75rem] font-semibold leading-none tracking-tight text-neutro-900 tabular-nums">{{ valor() }}</p>
      @if (nota()) {
        <p class="text-xs text-neutro-500">{{ nota() }}</p>
      }
    </div>
  `,
})
export class FichaResumen {
  readonly etiqueta = input.required<string>();
  readonly valor = input.required<string | number>();
  readonly nota = input('');
  readonly tono = input<TonoFicha>('neutro');

  protected readonly punto = computed(() => PUNTO[this.tono()]);
}
