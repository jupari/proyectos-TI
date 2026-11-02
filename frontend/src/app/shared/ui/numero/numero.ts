import { ChangeDetectionStrategy, Component, computed, forwardRef, input, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { noop } from '../../utils/noop';

export type ModoNumero = 'numero' | 'moneda' | 'horas';

let siguienteId = 0;

/** Formatea con separador de miles es-CO; muestra el valor sin formato
 * mientras el usuario escribe (evita que el cursor "salte") y lo formatea
 * de nuevo al perder el foco. */
@Component({
  selector: 'app-numero',
  templateUrl: './numero.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => Numero), multi: true }],
})
export class Numero implements ControlValueAccessor {
  readonly etiqueta = input<string>('');
  readonly ayuda = input<string>('');
  readonly error = input<string>('');
  readonly modo = input<ModoNumero>('numero');
  readonly decimales = input<number | null>(null);

  protected readonly id = `app-numero-${siguienteId++}`;
  protected readonly valor = signal<number | null>(null);
  protected readonly enEdicion = signal(false);
  protected readonly textoEdicion = signal('');
  protected readonly deshabilitado = signal(false);

  protected readonly decimalesEfectivos = computed(() => {
    const explicito = this.decimales();
    if (explicito !== null) return explicito;
    return this.modo() === 'moneda' ? 0 : 2;
  });

  protected readonly prefijo = computed(() => (this.modo() === 'moneda' ? '$' : ''));
  protected readonly sufijo = computed(() => (this.modo() === 'horas' ? 'h' : ''));

  private formateador(): Intl.NumberFormat {
    return new Intl.NumberFormat('es-CO', {
      minimumFractionDigits: this.decimalesEfectivos(),
      maximumFractionDigits: this.decimalesEfectivos(),
    });
  }

  protected readonly textoMostrado = computed(() => {
    const valor = this.valor();
    return valor === null ? '' : this.formateador().format(valor);
  });

  private alCambiar: (valor: number | null) => void = noop;
  protected alTocar: () => void = noop;

  writeValue(valor: number | null): void {
    this.valor.set(valor);
  }

  registerOnChange(fn: (valor: number | null) => void): void {
    this.alCambiar = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.alTocar = fn;
  }

  setDisabledState(deshabilitado: boolean): void {
    this.deshabilitado.set(deshabilitado);
  }

  protected alEnfocar(): void {
    this.enEdicion.set(true);
    const valor = this.valor();
    this.textoEdicion.set(valor === null ? '' : String(valor).replace('.', ','));
  }

  protected alEscribir(evento: Event): void {
    this.textoEdicion.set((evento.target as HTMLInputElement).value);
  }

  protected alDesenfocar(): void {
    const texto = this.textoEdicion().replace(/\./g, '').replace(',', '.').trim();
    const numero = texto === '' ? null : Number(texto);
    this.valor.set(numero !== null && !Number.isNaN(numero) ? numero : null);
    this.alCambiar(this.valor());
    this.enEdicion.set(false);
    this.alTocar();
  }
}
