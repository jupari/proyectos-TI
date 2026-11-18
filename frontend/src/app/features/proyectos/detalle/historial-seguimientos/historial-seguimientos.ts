import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ETIQUETAS_ESTADO_SEGUIMIENTO, Seguimiento } from '../../../../core/models';
import { HorasPipe, MonedaPipe } from '../../../../shared/pipes';
import { Badge } from '../../../../shared/ui/badge/badge';
import { Semaforo, ValorSemaforo } from '../../../../shared/ui/semaforo/semaforo';
import { agruparSeguimientos } from './historial-seguimientos.utils';

/** Historial de seguimientos del proyecto agrupado por periodicidad
 * (semanal / mensual / diario), del más reciente al más antiguo. */
@Component({
  selector: 'app-historial-seguimientos',
  templateUrl: './historial-seguimientos.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Badge, Semaforo, HorasPipe, MonedaPipe],
})
export class HistorialSeguimientos {
  readonly seguimientos = input.required<Seguimiento[]>();

  protected readonly ETIQUETAS_ESTADO = ETIQUETAS_ESTADO_SEGUIMIENTO;
  protected readonly grupos = computed(() => agruparSeguimientos(this.seguimientos()));

  protected valorSemaforo(valor: string): ValorSemaforo {
    return valor as ValorSemaforo;
  }

  protected avance(seguimiento: Seguimiento): number {
    return Math.min(100, Math.max(0, Number(seguimiento.avance_reportado)));
  }

  protected claseVariacion(variacion: number): string {
    if (variacion > 0) return 'bg-exito/10 text-exito';
    if (variacion < 0) return 'bg-peligro/10 text-peligro';
    return 'bg-neutro-100 text-neutro-600';
  }

  protected textoVariacion(variacion: number): string {
    const puntos = Math.abs(Math.round(variacion * 10) / 10);
    if (variacion > 0) return `▲ +${puntos} pts`;
    if (variacion < 0) return `▼ −${puntos} pts`;
    return '= sin cambio';
  }
}
