import { ChangeDetectionStrategy, Component, forwardRef, input, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { noop } from '../../utils/noop';

let siguienteId = 0;

@Component({
  selector: 'app-input',
  templateUrl: './input.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => Input),
      multi: true,
    },
  ],
})
export class Input implements ControlValueAccessor {
  readonly etiqueta = input<string>('');
  readonly ayuda = input<string>('');
  readonly error = input<string>('');
  readonly tipo = input<'text' | 'email' | 'password' | 'tel' | 'url'>('text');
  readonly placeholder = input<string>('');
  readonly prefijo = input<string>('');
  readonly sufijo = input<string>('');
  readonly autocomplete = input<string>('off');

  protected readonly id = `app-input-${siguienteId++}`;
  protected readonly valor = signal('');
  protected readonly deshabilitado = signal(false);

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
    const valor = (evento.target as HTMLInputElement).value;
    this.valor.set(valor);
    this.alCambiar(valor);
  }
}
