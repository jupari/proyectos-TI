import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { ModoColor, TemaService } from '../../core/tema/tema.service';

interface OpcionModo {
  valor: ModoColor;
  etiqueta: string;
  icono: string;
}

@Component({
  selector: 'app-selector-tema',
  templateUrl: './selector-tema.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '(document:click)': 'alClicFuera($event)',
    '(document:keydown.escape)': 'abierto.set(false)',
  },
})
export class SelectorTema {
  protected readonly tema = inject(TemaService);
  protected readonly abierto = signal(false);

  protected readonly modos: readonly OpcionModo[] = [
    { valor: 'claro', etiqueta: 'Claro', icono: '☀️' },
    { valor: 'oscuro', etiqueta: 'Oscuro', icono: '🌙' },
    { valor: 'sistema', etiqueta: 'Sistema', icono: '💻' },
  ];

  protected alClicFuera(evento: MouseEvent): void {
    if (!(evento.target as HTMLElement).closest('[data-selector-tema]')) {
      this.abierto.set(false);
    }
  }
}
