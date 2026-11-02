import { Pipe, PipeTransform } from '@angular/core';

/** `1.234,50 h`; `—` si es `null`. */
@Pipe({ name: 'horas' })
export class HorasPipe implements PipeTransform {
  private readonly formateador = new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  transform(valor: string | number | null | undefined): string {
    if (valor === null || valor === undefined || valor === '') return '—';
    const numero = typeof valor === 'string' ? Number(valor) : valor;
    return Number.isNaN(numero) ? '—' : `${this.formateador.format(numero)} h`;
  }
}
