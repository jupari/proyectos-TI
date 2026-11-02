import { Pipe, PipeTransform } from '@angular/core';

/** `{{ proyecto.estado | etiquetaEnum:ETIQUETAS_ESTADO_PROYECTO }}` — usa el
 * mismo mapa de `core/models/enums.ts` que el resto de la app, para que la
 * etiqueta en español nunca se repita suelta en una plantilla. */
@Pipe({ name: 'etiquetaEnum' })
export class EtiquetaEnumPipe implements PipeTransform {
  transform(valor: string | null | undefined, mapa: Record<string, string>): string {
    if (!valor) return '—';
    return mapa[valor] ?? valor;
  }
}
