import { NgTemplateOutlet } from '@angular/common';
import { ChangeDetectionStrategy, Component, effect, inject, input, output, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import {
  CompromisoSeguimiento,
  DocumentoExpediente,
  ETIQUETAS_CATEGORIA_DOCUMENTO,
  ETIQUETAS_ESTADO_COMPROMISO,
  ETIQUETAS_ESTADO_SEGUIMIENTO,
  ETIQUETAS_PERIODICIDAD,
  Seguimiento,
} from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, FechaCortaPipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Modal } from '../../../shared/ui/modal/modal';
import { Semaforo, ValorSemaforo } from '../../../shared/ui/semaforo/semaforo';
import { DocumentosService } from '../../expediente/data/documentos.service';
import { CompromisosService } from '../data/compromisos.service';

/** Vista rápida de un seguimiento (logros, dificultades, riesgos, acciones,
 * compromisos y adjuntos). Se abre mientras `seguimiento` no sea `null`; el
 * padre lo pone en `null` al recibir `cerrar`. La usan la lista de
 * seguimientos y la pestaña Seguimientos del proyecto. */
@Component({
  selector: 'app-detalle-seguimiento-modal',
  templateUrl: './detalle-seguimiento-modal.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NgTemplateOutlet, RouterLink, Boton, Badge, Semaforo, Modal, EtiquetaEnumPipe, FechaCortaPipe],
})
export class DetalleSeguimientoModal {
  private readonly compromisosService = inject(CompromisosService);
  private readonly documentosService = inject(DocumentosService);
  private readonly toast = inject(ToastService);

  readonly seguimiento = input<Seguimiento | null>(null);
  readonly cerrar = output<void>();

  protected readonly ETIQUETAS_ESTADO_SEGUIMIENTO = ETIQUETAS_ESTADO_SEGUIMIENTO;
  protected readonly ETIQUETAS_PERIODICIDAD = ETIQUETAS_PERIODICIDAD;
  protected readonly ETIQUETAS_ESTADO_COMPROMISO = ETIQUETAS_ESTADO_COMPROMISO;
  protected readonly ETIQUETAS_CATEGORIA_DOCUMENTO = ETIQUETAS_CATEGORIA_DOCUMENTO;

  protected readonly compromisos = signal<CompromisoSeguimiento[]>([]);
  protected readonly documentos = signal<DocumentoExpediente[]>([]);
  protected readonly cargando = signal(false);

  /** Evita que la respuesta de un seguimiento anterior pise a la del actual. */
  private solicitud = 0;

  constructor() {
    effect(() => {
      const actual = this.seguimiento();
      untracked(() => this.cargar(actual));
    });
  }

  private cargar(seguimiento: Seguimiento | null): void {
    const solicitud = ++this.solicitud;
    this.compromisos.set([]);
    this.documentos.set([]);
    if (!seguimiento) {
      this.cargando.set(false);
      return;
    }
    this.cargando.set(true);
    forkJoin({
      compromisos: this.compromisosService.listar({ seguimiento: seguimiento.id, page_size: 200 }),
      documentos: this.documentosService.listar({ seguimiento: seguimiento.id, page_size: 200 }),
    }).subscribe({
      next: (respuesta) => {
        if (solicitud !== this.solicitud) return;
        this.compromisos.set(respuesta.compromisos.results);
        this.documentos.set(respuesta.documentos.results);
        this.cargando.set(false);
      },
      error: () => {
        if (solicitud !== this.solicitud) return;
        this.cargando.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el detalle del seguimiento.' });
      },
    });
  }

  protected valorSemaforo(valor: string): ValorSemaforo {
    return valor as ValorSemaforo;
  }

  protected descargarAdjunto(documento: DocumentoExpediente): void {
    this.documentosService.descargar(documento.id).subscribe((blob) => {
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = documento.nombre_original;
      enlace.click();
      URL.revokeObjectURL(url);
    });
  }
}
