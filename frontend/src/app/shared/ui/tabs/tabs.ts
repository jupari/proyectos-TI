import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface PestanaTab {
  id: string;
  etiqueta: string;
}

/** Solo pinta la lista de pestañas (role="tablist"); el panel visible lo
 * decide el consumidor con `@if (activa() === 'x')`, así no hace falta
 * acoplar el contenido a este componente. */
@Component({
  selector: 'app-tabs',
  templateUrl: './tabs.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Tabs {
  readonly pestanas = input.required<PestanaTab[]>();
  readonly activa = input.required<string>();

  readonly cambio = output<string>();

  protected idBoton(id: string): string {
    return `app-tab-${id}`;
  }

  protected seleccionar(id: string): void {
    if (id !== this.activa()) {
      this.cambio.emit(id);
    }
  }

  protected alTecla(evento: KeyboardEvent, indice: number): void {
    const pestanas = this.pestanas();
    let nuevoIndice: number;
    if (evento.key === 'ArrowRight') {
      nuevoIndice = (indice + 1) % pestanas.length;
    } else if (evento.key === 'ArrowLeft') {
      nuevoIndice = (indice - 1 + pestanas.length) % pestanas.length;
    } else if (evento.key === 'Home') {
      nuevoIndice = 0;
    } else if (evento.key === 'End') {
      nuevoIndice = pestanas.length - 1;
    } else {
      return;
    }
    evento.preventDefault();
    const nuevaPestana = pestanas[nuevoIndice];
    this.seleccionar(nuevaPestana.id);
    queueMicrotask(() => {
      document.getElementById(this.idBoton(nuevaPestana.id))?.focus();
    });
  }
}
