import { ChangeDetectionStrategy, Component, computed, forwardRef, input, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { noop } from '../../utils/noop';

export interface OpcionSelect {
  valor: string;
  etiqueta: string;
}

let siguienteId = 0;

@Component({
  selector: 'app-select',
  templateUrl: './select.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => Select),
      multi: true,
    },
  ],
  host: {
    '(document:click)': 'alClicFuera($event)',
  },
})
export class Select implements ControlValueAccessor {
  readonly etiqueta = input<string>('');
  readonly ayuda = input<string>('');
  readonly error = input<string>('');
  readonly placeholder = input('Seleccione…');
  readonly opciones = input<OpcionSelect[]>([]);
  readonly limpiable = input(false);

  protected readonly id = `app-select-${siguienteId++}`;
  protected readonly abierto = signal(false);
  protected readonly termino = signal('');
  protected readonly indiceActivo = signal(0);
  protected readonly valor = signal<string | null>(null);
  protected readonly deshabilitado = signal(false);

  protected readonly conBusqueda = computed(() => this.opciones().length > 10);

  protected readonly opcionesFiltradas = computed(() => {
    const termino = this.termino().trim().toLowerCase();
    if (!termino) {
      return this.opciones();
    }
    return this.opciones().filter((opcion) => opcion.etiqueta.toLowerCase().includes(termino));
  });

  protected readonly etiquetaSeleccionada = computed(() => {
    const valor = this.valor();
    return this.opciones().find((opcion) => opcion.valor === valor)?.etiqueta ?? null;
  });

  private alCambiar: (valor: string | null) => void = noop;
  protected alTocar: () => void = noop;

  writeValue(valor: string | null): void {
    this.valor.set(valor);
  }

  registerOnChange(fn: (valor: string | null) => void): void {
    this.alCambiar = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.alTocar = fn;
  }

  setDisabledState(deshabilitado: boolean): void {
    this.deshabilitado.set(deshabilitado);
  }

  protected alternar(): void {
    if (this.deshabilitado()) return;
    this.abierto.update((valor) => !valor);
    if (this.abierto()) {
      this.indiceActivo.set(0);
      this.termino.set('');
    } else {
      this.alTocar();
    }
  }

  protected seleccionar(opcion: OpcionSelect): void {
    this.valor.set(opcion.valor);
    this.alCambiar(opcion.valor);
    this.abierto.set(false);
    this.alTocar();
  }

  protected limpiar(evento: Event): void {
    evento.stopPropagation();
    this.valor.set(null);
    this.alCambiar(null);
    this.alTocar();
  }

  protected alBuscar(evento: Event): void {
    this.termino.set((evento.target as HTMLInputElement).value);
  }

  protected alClicFuera(evento: MouseEvent): void {
    const objetivo = evento.target as HTMLElement;
    if (!objetivo.closest(`[data-select-id="${this.id}"]`)) {
      this.abierto.set(false);
    }
  }

  protected alTeclaBoton(evento: KeyboardEvent): void {
    if (evento.key === 'ArrowDown' || evento.key === 'Enter' || evento.key === ' ') {
      evento.preventDefault();
      if (!this.abierto()) {
        this.alternar();
      }
    }
  }

  protected alTeclaLista(evento: KeyboardEvent): void {
    const opciones = this.opcionesFiltradas();
    if (evento.key === 'ArrowDown') {
      evento.preventDefault();
      this.indiceActivo.set(Math.min(this.indiceActivo() + 1, opciones.length - 1));
    } else if (evento.key === 'ArrowUp') {
      evento.preventDefault();
      this.indiceActivo.set(Math.max(this.indiceActivo() - 1, 0));
    } else if (evento.key === 'Enter') {
      evento.preventDefault();
      const opcion = opciones[this.indiceActivo()];
      if (opcion) {
        this.seleccionar(opcion);
      }
    } else if (evento.key === 'Escape') {
      evento.preventDefault();
      this.abierto.set(false);
    }
  }
}
