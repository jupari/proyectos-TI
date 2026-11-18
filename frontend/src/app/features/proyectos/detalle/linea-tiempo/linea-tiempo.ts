import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input, output, signal } from '@angular/core';

import {
  EntregableHito,
  ErrorApi,
  EstadoEntregable,
  ETIQUETAS_ESTADO_ENTREGABLE,
  ETIQUETAS_ESTADO_FASE,
  ETIQUETAS_ESTADO_HITO,
  FaseProyecto,
  Hito,
} from '../../../../core/models';
import { ConfirmacionService } from '../../../../core/ui/confirmacion.service';
import { ToastService } from '../../../../core/ui/toast.service';
import { FechaCortaPipe } from '../../../../shared/pipes';
import { Badge } from '../../../../shared/ui/badge/badge';
import { Boton } from '../../../../shared/ui/boton/boton';
import { EntregablesHitoService } from '../../data/proyectos.service';
import {
  avanceDeFase,
  construirLineaTiempo,
  hitoVencido,
  hoyIso,
  resumirLineaTiempo,
} from './linea-tiempo.utils';

/** Ciclo al pulsar el círculo de un entregable. */
const SIGUIENTE_ESTADO: Record<EstadoEntregable, EstadoEntregable> = {
  PENDIENTE: 'ENTREGADO',
  ENTREGADO: 'APROBADO',
  APROBADO: 'PENDIENTE',
};

/** Línea de tiempo vertical del proyecto: fases e hitos en orden
 * cronológico, con los entregables de cada hito. Es de presentación: cuando
 * cambia un entregable avisa con `cambio` y el padre recarga el proyecto. */
@Component({
  selector: 'app-linea-tiempo',
  templateUrl: './linea-tiempo.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Badge, Boton, FechaCortaPipe],
})
export class LineaTiempo {
  private readonly entregablesService = inject(EntregablesHitoService);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly toast = inject(ToastService);

  readonly proyectoId = input.required<string>();
  readonly fases = input.required<FaseProyecto[]>();
  readonly hitos = input.required<Hito[]>();
  readonly puedeEditar = input(false);

  readonly nuevoHito = output<void>();
  readonly editarHito = output<Hito>();
  /** Se emitió un cambio en entregables: el padre debe recargar el proyecto. */
  readonly cambio = output<void>();

  protected readonly ETIQUETAS_FASE = ETIQUETAS_ESTADO_FASE;
  protected readonly ETIQUETAS_HITO = ETIQUETAS_ESTADO_HITO;
  protected readonly ETIQUETAS_ENTREGABLE = ETIQUETAS_ESTADO_ENTREGABLE;

  protected readonly hoy = hoyIso();
  protected readonly items = computed(() => construirLineaTiempo(this.fases(), this.hitos(), this.hoy));
  protected readonly resumen = computed(() => resumirLineaTiempo(this.fases(), this.hitos(), this.hoy));
  protected readonly pctEntregables = computed(() => {
    const { entregablesListos, entregablesTotal } = this.resumen();
    return entregablesTotal === 0 ? 0 : Math.round((entregablesListos / entregablesTotal) * 100);
  });

  protected readonly hitoAgregando = signal<string | null>(null);
  protected readonly nombreNuevo = signal('');
  protected readonly guardando = signal(false);

  protected avance(fase: FaseProyecto): number {
    return avanceDeFase(fase, this.hoy);
  }

  protected vencido(hito: Hito): boolean {
    return hitoVencido(hito, this.hoy);
  }

  /** Tolera respuestas sin `entregables` (API aún sin actualizar). */
  protected entregablesDe(hito: Hito): EntregableHito[] {
    return hito.entregables ?? [];
  }

  protected entregablesListos(hito: Hito): number {
    return this.entregablesDe(hito).filter((e) => e.estado !== 'PENDIENTE').length;
  }

  protected claseMarcadorFase(fase: FaseProyecto): string {
    if (fase.estado === 'COMPLETADA') return 'bg-exito text-white';
    if (fase.estado === 'EN_PROGRESO') return 'bg-primario-500 text-white';
    return 'bg-surface text-neutro-400 border-2 border-neutro-300';
  }

  protected claseMarcadorHito(hito: Hito): string {
    if (hito.estado === 'CUMPLIDO') return 'bg-exito border-exito';
    if (hito.estado === 'INCUMPLIDO' || this.vencido(hito)) return 'bg-peligro border-peligro';
    if (hito.estado === 'REPROGRAMADO') return 'bg-alerta border-alerta';
    return 'bg-surface border-primario-400';
  }

  protected claseIconoEntregable(estado: EstadoEntregable): string {
    if (estado === 'APROBADO') return 'bg-exito border-exito text-white';
    if (estado === 'ENTREGADO') return 'bg-primario-500 border-primario-500 text-white';
    return 'bg-surface border-neutro-300 text-transparent hover:border-primario-400';
  }

  protected abrirAgregar(hito: Hito): void {
    this.nombreNuevo.set('');
    this.hitoAgregando.set(hito.id);
  }

  protected cancelarAgregar(): void {
    this.hitoAgregando.set(null);
  }

  protected agregar(hito: Hito): void {
    const nombre = this.nombreNuevo().trim();
    if (!nombre || this.guardando()) return;
    this.guardando.set(true);
    this.entregablesService
      .crear({ proyecto: this.proyectoId(), hito: hito.id, nombre } as Partial<EntregableHito>)
      .subscribe({
        next: () => {
          this.guardando.set(false);
          this.hitoAgregando.set(null);
          this.cambio.emit();
        },
        error: (error: unknown) => this.fallar(error, 'No se pudo agregar el entregable.'),
      });
  }

  protected avanzarEstado(entregable: EntregableHito): void {
    if (!this.puedeEditar() || this.guardando()) return;
    const estado = SIGUIENTE_ESTADO[entregable.estado];
    this.guardando.set(true);
    this.entregablesService
      .actualizar(entregable.id, {
        estado,
        fecha_entrega: estado === 'PENDIENTE' ? null : (entregable.fecha_entrega ?? this.hoy),
      } as Partial<EntregableHito>)
      .subscribe({
        next: () => {
          this.guardando.set(false);
          this.cambio.emit();
        },
        error: (error: unknown) => this.fallar(error, 'No se pudo actualizar el entregable.'),
      });
  }

  protected async eliminar(entregable: EntregableHito): Promise<void> {
    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Eliminar entregable',
      mensaje: `¿Eliminar el entregable «${entregable.nombre}»?`,
      variante: 'peligro',
      textoConfirmar: 'Eliminar',
    });
    if (!confirmado) return;
    this.entregablesService.eliminar(entregable.id).subscribe({
      next: () => this.cambio.emit(),
      error: (error: unknown) => this.fallar(error, 'No se pudo eliminar el entregable.'),
    });
  }

  private fallar(error: unknown, porDefecto: string): void {
    this.guardando.set(false);
    const cuerpo = error instanceof HttpErrorResponse ? (error.error as Partial<ErrorApi> | null) : null;
    this.toast.mostrar({ tipo: 'error', mensaje: cuerpo?.error?.mensaje ?? porDefecto });
  }
}
