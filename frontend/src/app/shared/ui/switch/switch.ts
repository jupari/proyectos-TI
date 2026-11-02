import { ChangeDetectionStrategy, Component, forwardRef, input, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { noop } from '../../utils/noop';

let siguienteId = 0;

@Component({
  selector: 'app-switch',
  templateUrl: './switch.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => Switch), multi: true }],
})
export class Switch implements ControlValueAccessor {
  readonly etiqueta = input<string>('');

  protected readonly id = `app-switch-${siguienteId++}`;
  protected readonly encendido = signal(false);
  protected readonly deshabilitado = signal(false);

  private alCambiar: (valor: boolean) => void = noop;
  private alTocar: () => void = noop;

  writeValue(valor: boolean): void {
    this.encendido.set(!!valor);
  }

  registerOnChange(fn: (valor: boolean) => void): void {
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
    this.encendido.update((valor) => !valor);
    this.alCambiar(this.encendido());
    this.alTocar();
  }
}
