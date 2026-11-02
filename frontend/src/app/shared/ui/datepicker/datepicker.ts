import { ChangeDetectionStrategy, Component, computed, forwardRef, input, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { noop } from '../../utils/noop';

let siguienteId = 0;

interface DiaCalendario {
  fecha: Date;
  iso: string;
  numero: number;
  delMesActual: boolean;
  deshabilitado: boolean;
}

function aIso(fecha: Date): string {
  const anio = fecha.getFullYear();
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');
  return `${anio}-${mes}-${dia}`;
}

function aVisual(iso: string | null): string {
  if (!iso) return '';
  const [anio, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${anio}`;
}

function desdeVisual(texto: string): string | null {
  const coincidencia = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(texto.trim());
  if (!coincidencia) return null;
  const [, dia, mes, anio] = coincidencia;
  const fecha = new Date(Number(anio), Number(mes) - 1, Number(dia));
  if (fecha.getDate() !== Number(dia) || fecha.getMonth() !== Number(mes) - 1) return null;
  return aIso(fecha);
}

const NOMBRES_MES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];
const NOMBRES_DIA = ['lu', 'ma', 'mi', 'ju', 'vi', 'sá', 'do'];

@Component({
  selector: 'app-datepicker',
  templateUrl: './datepicker.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    { provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => Datepicker), multi: true },
  ],
  host: {
    '(document:click)': 'alClicFuera($event)',
  },
})
export class Datepicker implements ControlValueAccessor {
  readonly etiqueta = input<string>('');
  readonly ayuda = input<string>('');
  readonly error = input<string>('');
  readonly minimo = input<string | null>(null);
  readonly maximo = input<string | null>(null);

  protected readonly id = `app-datepicker-${siguienteId++}`;
  protected readonly valorIso = signal<string | null>(null);
  protected readonly textoVisual = signal('');
  protected readonly deshabilitado = signal(false);
  protected readonly abierto = signal(false);
  protected readonly mesVisible = signal(new Date());

  protected readonly etiquetaMes = computed(
    () => `${NOMBRES_MES[this.mesVisible().getMonth()]} ${this.mesVisible().getFullYear()}`,
  );
  protected readonly nombresDia = NOMBRES_DIA;

  protected readonly dias = computed<DiaCalendario[]>(() => {
    const base = this.mesVisible();
    const primerDiaMes = new Date(base.getFullYear(), base.getMonth(), 1);
    const corrimiento = (primerDiaMes.getDay() + 6) % 7; // lunes = 0
    const inicio = new Date(primerDiaMes);
    inicio.setDate(inicio.getDate() - corrimiento);

    const min = this.minimo();
    const max = this.maximo();
    const dias: DiaCalendario[] = [];
    for (let i = 0; i < 42; i++) {
      const fecha = new Date(inicio);
      fecha.setDate(inicio.getDate() + i);
      const iso = aIso(fecha);
      dias.push({
        fecha,
        iso,
        numero: fecha.getDate(),
        delMesActual: fecha.getMonth() === base.getMonth(),
        deshabilitado: (min !== null && iso < min) || (max !== null && iso > max),
      });
    }
    return dias;
  });

  private alCambiar: (valor: string | null) => void = noop;
  protected alTocar: () => void = noop;

  writeValue(valor: string | null): void {
    this.valorIso.set(valor);
    this.textoVisual.set(aVisual(valor));
    this.mesVisible.set(valor ? new Date(valor) : new Date());
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

  protected alEscribirTexto(evento: Event): void {
    const texto = (evento.target as HTMLInputElement).value;
    this.textoVisual.set(texto);
    const iso = desdeVisual(texto);
    if (iso || texto === '') {
      this.valorIso.set(iso);
      this.alCambiar(iso);
      if (iso) this.mesVisible.set(new Date(iso));
    }
  }

  protected alternar(): void {
    if (this.deshabilitado()) return;
    this.abierto.update((valor) => !valor);
  }

  protected elegirDia(dia: DiaCalendario): void {
    if (dia.deshabilitado) return;
    this.valorIso.set(dia.iso);
    this.textoVisual.set(aVisual(dia.iso));
    this.alCambiar(dia.iso);
    this.abierto.set(false);
    this.alTocar();
  }

  protected mesAnterior(): void {
    const actual = this.mesVisible();
    this.mesVisible.set(new Date(actual.getFullYear(), actual.getMonth() - 1, 1));
  }

  protected mesSiguiente(): void {
    const actual = this.mesVisible();
    this.mesVisible.set(new Date(actual.getFullYear(), actual.getMonth() + 1, 1));
  }

  protected alClicFuera(evento: MouseEvent): void {
    const objetivo = evento.target as HTMLElement;
    if (!objetivo.closest(`[data-datepicker-id="${this.id}"]`)) {
      this.abierto.set(false);
    }
  }

  protected alTeclaCampo(evento: KeyboardEvent): void {
    if (evento.key === 'Escape') {
      this.abierto.set(false);
    } else if (evento.key === 'ArrowDown') {
      evento.preventDefault();
      this.abierto.set(true);
    }
  }
}
