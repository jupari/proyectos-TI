import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ErrorApi, ETIQUETAS_ESTADO_TAREA, ETIQUETAS_TIPO_DEPENDENCIA } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, FechaCortaPipe, HorasPipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Card } from '../../../shared/ui/card/card';
import { EnConstruccion } from '../../comun/en-construccion';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Modal } from '../../../shared/ui/modal/modal';
import { Numero } from '../../../shared/ui/numero/numero';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Textarea } from '../../../shared/ui/textarea/textarea';
import { DependenciaTareaEscritura, DependenciasService } from '../data/dependencias.service';
import { TareaDetalle } from '../data/tareas.model';
import { TareasService } from '../data/tareas.service';

@Component({
  selector: 'app-detalle-tarea',
  templateUrl: './detalle.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Card,
    Badge,
    Progreso,
    Boton,
    Modal,
    Select,
    Numero,
    Textarea,
    EstadoVacio,
    EnConstruccion,
    EtiquetaEnumPipe,
    FechaCortaPipe,
    HorasPipe,
  ],
})
export class DetalleTarea {
  private readonly tareasService = inject(TareasService);
  private readonly dependenciasService = inject(DependenciasService);
  private readonly toast = inject(ToastService);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly ETIQUETAS_ESTADO_TAREA = ETIQUETAS_ESTADO_TAREA;

  private readonly id = this.ruta.snapshot.paramMap.get('id')!;
  protected readonly cargando = signal(true);
  protected readonly tarea = signal<TareaDetalle | null>(null);

  protected readonly opcionesEstado: OpcionSelect[] = Object.entries(ETIQUETAS_ESTADO_TAREA).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );
  protected readonly opcionesTipoDependencia: OpcionSelect[] = Object.entries(
    ETIQUETAS_TIPO_DEPENDENCIA,
  ).map(([valor, etiqueta]) => ({ valor, etiqueta }));

  protected readonly dialogoEstadoAbierto = signal(false);
  protected readonly estadoSeleccionado = signal<string | null>(null);
  protected readonly notaEstado = signal('');
  protected readonly cambiandoEstado = signal(false);

  protected readonly dialogoDependenciaAbierto = signal(false);
  protected readonly depTareaDestinoId = signal<string | null>(null);
  protected readonly depTipo = signal<string | null>('FI');
  protected readonly depDiasDesfase = signal<number | null>(0);
  protected readonly guardandoDependencia = signal(false);
  protected readonly opcionesTareasProyecto = signal<OpcionSelect[]>([]);

  protected readonly sugiriendoFechas = signal(false);
  protected readonly fechaInicioSugerida = signal<string | null>(null);
  protected readonly fechaFinSugerida = signal<string | null>(null);

  protected readonly necesitaNota = computed(() => this.estadoSeleccionado() === 'BLOQUEADA');

  constructor() {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.tareasService.obtenerDetalle(this.id).subscribe({
      next: (tarea) => {
        this.tarea.set(tarea);
        this.cargando.set(false);
        this.tareasService
          .listarTareas({ proyecto: tarea.proyecto, page_size: 200 })
          .subscribe((r) =>
            this.opcionesTareasProyecto.set(
              r.results
                .filter((t) => t.id !== this.id)
                .map((t) => ({ valor: t.id, etiqueta: `${t.codigo} — ${t.nombre}` })),
            ),
          );
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la tarea.' });
        this.cargando.set(false);
      },
    });
  }

  protected numero(valor: string): number {
    return Number(valor);
  }

  // --- cambiar estado ------------------------------------------------------

  protected abrirDialogoEstado(): void {
    this.estadoSeleccionado.set(this.tarea()?.estado ?? null);
    this.notaEstado.set('');
    this.dialogoEstadoAbierto.set(true);
  }

  protected cerrarDialogoEstado(): void {
    this.dialogoEstadoAbierto.set(false);
  }

  protected confirmarCambioEstado(): void {
    const estado = this.estadoSeleccionado();
    if (!estado) return;
    if (this.necesitaNota() && !this.notaEstado().trim()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Escriba el motivo del bloqueo.' });
      return;
    }

    this.cambiandoEstado.set(true);
    this.tareasService
      .cambiarEstado(this.id, {
        estado,
        nota: this.necesitaNota() ? this.notaEstado().trim() : undefined,
      })
      .subscribe({
        next: (tarea) => {
          this.tarea.set(tarea);
          this.cambiandoEstado.set(false);
          this.dialogoEstadoAbierto.set(false);
          this.toast.mostrar({ tipo: 'exito', mensaje: 'Estado actualizado.' });
        },
        error: (error: unknown) => {
          this.cambiandoEstado.set(false);
          this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeError(error) });
        },
      });
  }

  // --- dependencias ---------------------------------------------------------

  protected abrirDialogoDependencia(): void {
    this.depTareaDestinoId.set(null);
    this.depTipo.set('FI');
    this.depDiasDesfase.set(0);
    this.dialogoDependenciaAbierto.set(true);
  }

  protected cerrarDialogoDependencia(): void {
    this.dialogoDependenciaAbierto.set(false);
  }

  protected guardarDependencia(): void {
    const destinoId = this.depTareaDestinoId();
    const tipo = this.depTipo();
    if (!destinoId || !tipo) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Indique la tarea sucesora y el tipo.' });
      return;
    }

    const cuerpo: DependenciaTareaEscritura = {
      tarea_origen: this.id,
      tarea_destino: destinoId,
      tipo: tipo as DependenciaTareaEscritura['tipo'],
      dias_desfase: this.depDiasDesfase() ?? 0,
    };

    this.guardandoDependencia.set(true);
    this.dependenciasService.crear(cuerpo).subscribe({
      next: () => {
        this.guardandoDependencia.set(false);
        this.dialogoDependenciaAbierto.set(false);
        this.cargar();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Dependencia creada.' });
      },
      error: (error: unknown) => {
        this.guardandoDependencia.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeErrorCiclo(error) });
      },
    });
  }

  protected eliminarDependencia(id: string): void {
    this.dependenciasService.eliminar(id).subscribe({
      next: () => {
        this.cargar();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Dependencia eliminada.' });
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo eliminar la dependencia.' });
      },
    });
  }

  // --- fechas sugeridas -------------------------------------------------------

  protected sugerirFechas(): void {
    this.sugiriendoFechas.set(true);
    this.tareasService.fechasSugeridas(this.id).subscribe({
      next: (resultado) => {
        this.sugiriendoFechas.set(false);
        this.fechaInicioSugerida.set(resultado.fecha_inicio_sugerida);
        this.fechaFinSugerida.set(resultado.fecha_fin_sugerida);
        if (!resultado.fecha_inicio_sugerida) {
          this.toast.mostrar({
            tipo: 'alerta',
            mensaje: 'No hay dependencias FI para sugerir una fecha.',
          });
        }
      },
      error: () => {
        this.sugiriendoFechas.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo calcular la sugerencia.' });
      },
    });
  }

  private mensajeError(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const cuerpo = error.error as Partial<ErrorApi> | null;
      return cuerpo?.error?.mensaje ?? 'No se pudo completar la operación.';
    }
    return 'No se pudo completar la operación.';
  }

  /** Si el servidor rechazó por ciclo, `detalles.ciclo` trae la ruta
   * completa (docs/plan/fase-07-tareas-programacion.md §7.1); mostrarla es
   * lo que hace útil el error, en vez de un mensaje genérico. */
  private mensajeErrorCiclo(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const cuerpo = error.error as Partial<ErrorApi> | null;
      const ciclo = cuerpo?.error?.detalles?.['ciclo'] as unknown as string[] | undefined;
      if (ciclo?.length) {
        return `Esa dependencia crearía un ciclo: ${ciclo.join(' → ')}.`;
      }
      return cuerpo?.error?.mensaje ?? 'No se pudo crear la dependencia.';
    }
    return 'No se pudo crear la dependencia.';
  }
}
