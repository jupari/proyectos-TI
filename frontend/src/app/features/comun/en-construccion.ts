import { ChangeDetectionStrategy, Component } from '@angular/core';

/** Marcador para las rutas de negocio de las fases 05 a 10: así el menú
 * funciona completo desde esta fase, sin pantallas reales todavía. */
@Component({
  selector: 'app-en-construccion',
  template: `
    <div class="flex flex-col items-center gap-3 py-16 text-center">
      <span class="text-4xl" aria-hidden="true">🚧</span>
      <h1 class="text-lg font-semibold text-neutro-800">Esta sección está en construcción</h1>
      <p class="text-sm text-neutro-500">Llega en una fase posterior del plan.</p>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EnConstruccion {}
