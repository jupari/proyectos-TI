import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Encabezado común de las pantallas de administración: sección (migas
 * cortas), título, una línea que explica para qué sirve la pantalla y, a la
 * derecha, las acciones principales (`[acciones]`). Debajo se proyecta la
 * "lectura rápida" (`[resumen]`): fichas con los números vivos de la pantalla. */
@Component({
  selector: 'app-cabecera-admin',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="flex flex-col gap-5">
      <div class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div class="min-w-0">
          <p class="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-primario-700">
            <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 1.9l6.2 2.3v4.6c0 3.9-2.6 7.4-6.2 9.3-3.6-1.9-6.2-5.4-6.2-9.3V4.2L10 1.9zm2.7 6.5a.9.9 0 00-1.3-1.2L9.2 9.4 8.4 8.6A.9.9 0 107.1 9.9l1.5 1.5c.4.4 1 .4 1.3 0l2.8-3z" clip-rule="evenodd" />
            </svg>
            Administración
          </p>
          <h1 class="text-balance text-[1.75rem] font-bold leading-tight tracking-tight text-neutro-900">{{ titulo() }}</h1>
          @if (descripcion()) {
            <p class="mt-1 max-w-2xl text-pretty text-sm text-neutro-500">{{ descripcion() }}</p>
          }
        </div>
        <div class="flex flex-wrap items-center gap-2 empty:hidden">
          <ng-content select="[acciones]" />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-3 empty:hidden lg:grid-cols-4">
        <ng-content select="[resumen]" />
      </div>
    </header>
  `,
})
export class CabeceraAdmin {
  readonly titulo = input.required<string>();
  readonly descripcion = input('');
}
