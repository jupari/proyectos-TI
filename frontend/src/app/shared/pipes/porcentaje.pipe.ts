import { Pipe, PipeTransform } from '@angular/core';

/** Un decimal, `—` si es `null` (nunca un 0% engañoso; ver docs/modelo-datos.md §10). */
@Pipe({ name: 'porcentaje' })
export class PorcentajePipe implements PipeTransform {
  private readonly formateador = new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });

  transform(valor: string | number | null | undefined): string {
    if (valor === null || valor === undefined || valor === '') return '—';
    const numero = typeof valor === 'string' ? Number(valor) : valor;
    return Number.isNaN(numero) ? '—' : `${this.formateador.format(numero)}%`;
  }
}
