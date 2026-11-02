import { Pipe, PipeTransform } from '@angular/core';

const PATRON_FECHA_ISO = /^(\d{4})-(\d{2})-(\d{2})/;

/** `dd/MM/yyyy`; `—` si es `null`.
 *
 * Para una fecha-sin-hora (`DateField` del backend, p. ej. `"2026-01-15"`)
 * NO se usa `new Date(valor)`: el constructor interpreta ese formato como
 * medianoche UTC, y en America/Bogota (UTC-5) eso muestra el día anterior.
 * Se extraen año/mes/día directamente del string en ese caso.
 */
@Pipe({ name: 'fechaCorta' })
export class FechaCortaPipe implements PipeTransform {
  transform(valor: string | Date | null | undefined): string {
    if (!valor) return '—';

    if (typeof valor === 'string') {
      const coincidencia = PATRON_FECHA_ISO.exec(valor);
      if (coincidencia) {
        const [, anio, mes, dia] = coincidencia;
        return `${dia}/${mes}/${anio}`;
      }
    }

    const fecha = typeof valor === 'string' ? new Date(valor) : valor;
    if (Number.isNaN(fecha.getTime())) return '—';
    const dia = String(fecha.getDate()).padStart(2, '0');
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    return `${dia}/${mes}/${fecha.getFullYear()}`;
  }
}
