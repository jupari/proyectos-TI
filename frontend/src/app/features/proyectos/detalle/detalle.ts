import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import {
  ETIQUETAS_ESTADO_PROYECTO,
  ErrorApi,
  TRANSICIONES_PROYECTO,
} from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, FechaCortaPipe, HorasPipe, MonedaPipe, PorcentajePipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Card } from '../../../shared/ui/card/card';
import { Modal } from '../../../shared/ui/modal/modal';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Semaforo, ValorSemaforo } from '../../../shared/ui/semaforo/semaforo';
import { PestanaTab, Tabs } from '../../../shared/ui/tabs/tabs';
import { Textarea } from '../../../shared/ui/textarea/textarea';
import { EnConstruccion } from '../../comun/en-construccion';
import { ProyectoDetalle } from '../data/proyectos.model';
import { ProyectosService } from '../data/proyectos.service';

const PESTANAS: PestanaTab[] = [
  { id: 'resumen', etiqueta: 'Resumen' },
  { id: 'fases', etiqueta: 'Fases' },
  { id: 'hitos', etiqueta: 'Hitos' },
  { id: 'presupuesto', etiqueta: 'Presupuesto' },
  { id: 'tareas', etiqueta: 'Tareas' },
  { id: 'ejecucion', etiqueta: 'Ejecución' },
  { id: 'seguimientos', etiqueta: 'Seguimientos' },
  { id: 'expediente', etiqueta: 'Expediente' },
];

@Component({
  selector: 'app-detalle-proyecto',
  templateUrl: './detalle.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Tabs,
    Card,
    Badge,
    Semaforo,
    Progreso,
    Boton,
    Select,
    Textarea,
    Modal,
    EnConstruccion,
    EtiquetaEnumPipe,
    FechaCortaPipe,
    MonedaPipe,
    HorasPipe,
    PorcentajePipe,
  ],
})
export class DetalleProyecto {
  private readonly proyectosService = inject(ProyectosService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly ETIQUETAS_ESTADO_PROYECTO = ETIQUETAS_ESTADO_PROYECTO;
  protected readonly pestanas = PESTANAS;

  private readonly id = this.ruta.snapshot.paramMap.get('id')!;
  protected readonly cargando = signal(true);
  protected readonly proyecto = signal<ProyectoDetalle | null>(null);
  protected readonly pestanaActiva = signal('resumen');

  protected readonly puedeEditar = computed(() => this.auth.tienePermiso('proyectos.editar'));

  protected readonly dialogoEstadoAbierto = signal(false);
  protected readonly estadoSeleccionado = signal<string | null>(null);
  protected readonly observacionEstado = signal('');
  protected readonly cambiandoEstado = signal(false);

  protected readonly opcionesTransicion = computed<OpcionSelect[]>(() => {
    const proyecto = this.proyecto();
    if (!proyecto) return [];
    const estado = proyecto.estado;
    return (TRANSICIONES_PROYECTO[estado] ?? []).map((valor) => ({
      valor,
      etiqueta: ETIQUETAS_ESTADO_PROYECTO[valor],
    }));
  });

  protected readonly sumaPesosFases = computed(() => {
    const proyecto = this.proyecto();
    if (!proyecto) return 0;
    return proyecto.fases
      .filter((fase) => fase.activo)
      .reduce((total, fase) => total + Number(fase.peso), 0);
  });

  protected readonly totalRubrosPlaneado = computed(() => {
    const proyecto = this.proyecto();
    if (!proyecto) return 0;
    return proyecto.rubros.reduce((total, rubro) => total + Number(rubro.monto_planeado), 0);
  });

  protected readonly totalRubrosEjecutado = computed(() => {
    const proyecto = this.proyecto();
    if (!proyecto) return 0;
    return proyecto.rubros.reduce((total, rubro) => total + Number(rubro.monto_ejecutado), 0);
  });

  constructor() {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.proyectosService.obtenerDetalle(this.id).subscribe({
      next: (proyecto) => {
        this.proyecto.set(proyecto);
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el proyecto.' });
        this.cargando.set(false);
      },
    });
  }

  protected cambiarPestana(id: string): void {
    this.pestanaActiva.set(id);
  }

  protected esValorSemaforo(valor: string): ValorSemaforo {
    return valor as ValorSemaforo;
  }

  protected numero(valor: string): number {
    return Number(valor);
  }

  protected abrirDialogoEstado(): void {
    this.estadoSeleccionado.set(null);
    this.observacionEstado.set('');
    this.dialogoEstadoAbierto.set(true);
  }

  protected cerrarDialogoEstado(): void {
    this.dialogoEstadoAbierto.set(false);
  }

  protected confirmarCambioEstado(): void {
    const estado = this.estadoSeleccionado();
    const observacion = this.observacionEstado().trim();
    if (!estado || !observacion) {
      this.toast.mostrar({
        tipo: 'error',
        mensaje: 'Seleccione el nuevo estado y escriba una observación.',
      });
      return;
    }

    this.cambiandoEstado.set(true);
    this.proyectosService.cambiarEstado(this.id, estado, observacion).subscribe({
      next: (proyecto) => {
        this.proyecto.set(proyecto);
        this.cambiandoEstado.set(false);
        this.dialogoEstadoAbierto.set(false);
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Estado actualizado.' });
      },
      error: (error: unknown) => {
        this.cambiandoEstado.set(false);
        let mensaje = 'No se pudo cambiar el estado.';
        if (error instanceof HttpErrorResponse) {
          const cuerpo = error.error as Partial<ErrorApi> | null;
          mensaje = cuerpo?.error?.mensaje ?? mensaje;
        }
        this.toast.mostrar({ tipo: 'error', mensaje });
      },
    });
  }
}
