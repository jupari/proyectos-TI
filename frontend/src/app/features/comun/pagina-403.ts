import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-pagina-403',
  template: `
    <div class="flex min-h-screen flex-col items-center justify-center gap-3 text-center">
      <span class="text-5xl font-bold text-neutro-300">403</span>
      <h1 class="text-lg font-semibold text-neutro-800">No tiene permiso para ver esta página</h1>
      <p class="text-sm text-neutro-500">Si considera que es un error, contacte al administrador.</p>
      <a routerLink="/tablero" class="text-sm font-medium text-teal-700 hover:underline">
        Volver al tablero
      </a>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
})
export class Pagina403 {}
