import { Pipe, PipeTransform } from '@angular/core';

/** es-CO, sin decimales (COP no los usa en la práctica); `—` si es `null`. */
@Pipe({ name: 'moneda' })
export class MonedaPipe implements PipeTransform {
  private readonly formateador = new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  });

  transform(valor: string | number | null | undefined): string {
    if (valor === null || valor === undefined || valor === '') return '—';
    const numero = typeof valor === 'string' ? Number(valor) : valor;
    return Number.isNaN(numero) ? '—' : this.formateador.format(numero);
  }
}
