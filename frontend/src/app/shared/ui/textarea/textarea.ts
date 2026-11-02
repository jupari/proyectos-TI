import { ChangeDetectionStrategy, Component, computed, forwardRef, input, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { noop } from '../../utils/noop';

let siguienteId = 0;

@Component({
  selector: 'app-textarea',
  templateUrl: './textarea.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => Textarea),
      multi: true,
    },
  ],
})
export class Textarea implements ControlValueAccessor {
  readonly etiqueta = input<string>('');
  readonly ayuda = input<string>('');
  readonly error = input<string>('');
  readonly placeholder = input<string>('');
  readonly filas = input(3);
  readonly maximoCaracteres = input<number | null>(null);

  protected readonly id = `app-textarea-${siguienteId++}`;
  protected readonly valor = signal('');
  protected readonly deshabilitado = signal(false);

  protected readonly contador = computed(() => {
    const maximo = this.maximoCaracteres();
    return maximo === null ? null : `${this.valor().length}/${maximo}`;
  });

  private alCambiar: (valor: string) => void = noop;
  protected alTocar: () => void = noop;

  writeValue(valor: string | null): void {
    this.valor.set(valor ?? '');
  }

  registerOnChange(fn: (valor: string) => void): void {
    this.alCambiar = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.alTocar = fn;
  }

  setDisabledState(deshabilitado: boolean): void {
    this.deshabilitado.set(deshabilitado);
  }

  protected alEscribir(evento: Event): void {
    const valor = (evento.target as HTMLTextAreaElement).value;
    this.valor.set(valor);
    this.alCambiar(valor);
  }
}
