import { Injectable, signal } from '@angular/core';

/** Móvil < 768 px, tableta 768–1023 px, escritorio ≥ 1024 px (breakpoints `md` y `lg` de Tailwind). */
export type TipoPantalla = 'movil' | 'tableta' | 'escritorio';

function calcular(): TipoPantalla {
  if (window.matchMedia('(min-width: 1024px)').matches) return 'escritorio';
  if (window.matchMedia('(min-width: 768px)').matches) return 'tableta';
  return 'movil';
}

@Injectable({ providedIn: 'root' })
export class PantallaService {
  readonly tipo = signal<TipoPantalla>(calcular());
  /** Cajón del menú lateral, solo se usa en móvil. */
  readonly menuMovilAbierto = signal(false);

  constructor() {
    for (const consulta of ['(min-width: 768px)', '(min-width: 1024px)']) {
      window.matchMedia(consulta).addEventListener('change', () => {
        this.tipo.set(calcular());
        if (this.tipo() !== 'movil') this.menuMovilAbierto.set(false);
      });
    }
  }
}
