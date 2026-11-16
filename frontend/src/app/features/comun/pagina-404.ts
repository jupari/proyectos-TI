import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-pagina-404',
  template: `
    <div class="flex min-h-screen flex-col items-center justify-center gap-3 text-center">
      <span class="text-5xl font-bold text-neutro-300">404</span>
      <h1 class="text-lg font-semibold text-neutro-800">Página no encontrada</h1>
      <p class="text-sm text-neutro-500">La ruta que busca no existe.</p>
      <a routerLink="/tablero" class="text-sm font-medium text-primario-700 hover:underline">
        Volver al tablero
      </a>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
})
export class Pagina404 {}
