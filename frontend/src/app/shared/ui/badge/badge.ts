import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type CategoriaBadge = 'exito' | 'alerta' | 'peligro' | 'info' | 'neutro';

/** Un mismo valor de enumerado (p. ej. `PENDIENTE`) significa lo mismo en
 * distintas entidades, así que un solo mapa por valor cubre los 17
 * enumerados del backend sin repetir la lógica por cada uno. */
const CATEGORIA_POR_VALOR: Record<string, CategoriaBadge> = {
  COMPLETADA: 'exito', COMPLETADO: 'exito', APROBADO: 'exito', CUMPLIDO: 'exito',
  PUBLICADO: 'exito', VERDE: 'exito', ACTIVO: 'exito',
  EJECUCION: 'info', EN_PROGRESO: 'info', PLANEACION: 'info', LOCAL: 'info', GOOGLE: 'info',
  ENVIADO: 'alerta', PENDIENTE: 'alerta', AMARILLO: 'alerta', REPROGRAMADO: 'alerta',
  EN_REVISION: 'alerta', ABIERTO: 'alerta', ALTA: 'alerta', CRITICA: 'peligro',
  CANCELADA: 'peligro', CANCELADO: 'peligro', RECHAZADO: 'peligro', RECHAZO: 'peligro',
  VENCIDO: 'peligro', INCUMPLIDO: 'peligro', ROJO: 'peligro', BLOQUEADA: 'peligro',
  SUSPENDIDO: 'peligro',
  BORRADOR: 'neutro', CERRADO: 'neutro', BAJA: 'neutro', MEDIA: 'neutro',
};

const CLASES_POR_CATEGORIA: Record<CategoriaBadge, string> = {
  exito: 'bg-exito/10 text-exito',
  alerta: 'bg-alerta/10 text-alerta',
  peligro: 'bg-peligro/10 text-peligro',
  info: 'bg-marca-50 text-marca-700',
  neutro: 'bg-neutro-100 text-neutro-700',
};

@Component({
  selector: 'app-badge',
  templateUrl: './badge.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Badge {
  /** Valor crudo del enumerado (p. ej. `'APROBADO'`), usado para elegir el color. */
  readonly valor = input.required<string>();
  /** Texto a mostrar; si se omite, se usa `valor()` tal cual. */
  readonly etiqueta = input('');

  protected readonly texto = computed(() => this.etiqueta() || this.valor());
  protected readonly clases = computed(
    () => CLASES_POR_CATEGORIA[CATEGORIA_POR_VALOR[this.valor()] ?? 'neutro'],
  );
}
