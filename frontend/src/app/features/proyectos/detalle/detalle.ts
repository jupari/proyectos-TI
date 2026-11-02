import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import {
  AsignacionRecurso,
  ETIQUETAS_ESTADO_PROYECTO,
  ErrorApi,
  TRANSICIONES_PROYECTO,
} from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, FechaCortaPipe, HorasPipe, MonedaPipe, PorcentajePipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Card } from '../../../shared/ui/card/card';
import { Datepicker } from '../../../shared/ui/datepicker/datepicker';
import { Drawer } from '../../../shared/ui/drawer/drawer';
import { Input } from '../../../shared/ui/input/input';
import { Modal } from '../../../shared/ui/modal/modal';
import { Numero } from '../../../shared/ui/numero/numero';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Semaforo, ValorSemaforo } from '../../../shared/ui/semaforo/semaforo';
import { PestanaTab, Tabs } from '../../../shared/ui/tabs/tabs';
import { Textarea } from '../../../shared/ui/textarea/textarea';
import { EnConstruccion } from '../../comun/en-construccion';
import { AsignacionEscritura, AsignacionesService } from '../../recursos/data/asignaciones.service';
import { RecursosService } from '../../recursos/data/recursos.service';
import { ProyectoDetalle } from '../data/proyectos.model';
import { ProyectosService } from '../data/proyectos.service';

const PESTANAS: PestanaTab[] = [
  { id: 'resumen', etiqueta: 'Resumen' },
  { id: 'fases', etiqueta: 'Fases' },
  { id: 'hitos', etiqueta: 'Hitos' },
  { id: 'presupuesto', etiqueta: 'Presupuesto' },
  { id: 'recursos', etiqueta: 'Recursos' },
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
    Drawer,
    Datepicker,
    Numero,
    Input,
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
  private readonly recursosService = inject(RecursosService);
  private readonly asignacionesService = inject(AsignacionesService);
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

  // --- pestaña Recursos (fase 06) ---------------------------------------

  protected readonly asignaciones = signal<AsignacionRecurso[]>([]);
  protected readonly opcionesRecursos = signal<OpcionSelect[]>([]);

  protected readonly totalHorasAsignadas = computed(() =>
    this.asignaciones().reduce((total, a) => total + Number(a.horas_planeadas), 0),
  );
  protected readonly totalCostoAsignado = computed(() =>
    this.asignaciones().reduce((total, a) => total + Number(a.costo_planeado), 0),
  );

  protected readonly drawerAsignacionAbierto = signal(false);
  protected readonly idAsignacionEnEdicion = signal<string | null>(null);
  protected readonly asigRecurso = signal<string | null>(null);
  protected readonly asigRolEnProyecto = signal('');
  protected readonly asigFechaDesde = signal<string | null>(null);
  protected readonly asigFechaHasta = signal<string | null>(null);
  protected readonly asigPorcentajeDedicacion = signal<number | null>(100);
  protected readonly asigHorasPlaneadas = signal<number | null>(null);
  protected readonly asigValorHoraPlan = signal<number | null>(null);
  protected readonly asigTarifaManual = signal(false);
  protected readonly guardandoAsignacion = signal(false);

  protected readonly asigCostoPlaneadoVivo = computed(
    () => (this.asigHorasPlaneadas() ?? 0) * (this.asigValorHoraPlan() ?? 0),
  );

  protected nombreRecurso(id: string): string {
    return this.opcionesRecursos().find((o) => o.valor === id)?.etiqueta ?? id;
  }

  private cargarAsignaciones(): void {
    this.proyectosService
      .recursosPlaneados(this.id)
      .subscribe((asignaciones) => this.asignaciones.set(asignaciones));
    if (this.opcionesRecursos().length === 0) {
      this.recursosService
        .listarRecursos({ page_size: 200 })
        .subscribe((r) =>
          this.opcionesRecursos.set(r.results.map((x) => ({ valor: x.id, etiqueta: x.nombre }))),
        );
    }
  }

  protected abrirNuevaAsignacion(): void {
    this.idAsignacionEnEdicion.set(null);
    this.asigRecurso.set(null);
    this.asigRolEnProyecto.set('');
    this.asigFechaDesde.set(null);
    this.asigFechaHasta.set(null);
    this.asigPorcentajeDedicacion.set(100);
    this.asigHorasPlaneadas.set(null);
    this.asigValorHoraPlan.set(null);
    this.asigTarifaManual.set(false);
    this.drawerAsignacionAbierto.set(true);
  }

  protected cerrarDrawerAsignacion(): void {
    this.drawerAsignacionAbierto.set(false);
  }

  /** Al elegir recurso, precarga `valor_hora_plan` con su tarifa vigente
   * *hoy* a modo de referencia visual; el servidor, al guardar, resuelve la
   * tarifa vigente a la fecha desde real si este campo no se marca manual. */
  protected alElegirRecurso(recursoId: string | null): void {
    this.asigRecurso.set(recursoId);
    this.asigTarifaManual.set(false);
    if (!recursoId) {
      this.asigValorHoraPlan.set(null);
      return;
    }
    this.recursosService.obtenerDetalle(recursoId).subscribe((recurso) => {
      this.asigValorHoraPlan.set(recurso.tarifa_vigente ? Number(recurso.tarifa_vigente) : null);
    });
  }

  protected alEditarValorHora(valor: number | null): void {
    this.asigValorHoraPlan.set(valor);
    this.asigTarifaManual.set(true);
  }

  protected guardarAsignacion(): void {
    if (
      !this.asigRecurso() ||
      !this.asigFechaDesde() ||
      !this.asigFechaHasta() ||
      !this.asigHorasPlaneadas()
    ) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete los campos obligatorios.' });
      return;
    }

    const cuerpo: AsignacionEscritura = {
      proyecto: this.id,
      recurso: this.asigRecurso()!,
      fase: null,
      rol_en_proyecto: this.asigRolEnProyecto(),
      fecha_desde: this.asigFechaDesde()!,
      fecha_hasta: this.asigFechaHasta()!,
      porcentaje_dedicacion: this.asigPorcentajeDedicacion() ?? 100,
      horas_planeadas: this.asigHorasPlaneadas()!,
    };
    if (this.asigTarifaManual() && this.asigValorHoraPlan() !== null) {
      cuerpo.valor_hora_plan = this.asigValorHoraPlan()!;
    }

    this.guardandoAsignacion.set(true);
    const id = this.idAsignacionEnEdicion();
    const peticion = id
      ? this.asignacionesService.actualizar(id, cuerpo)
      : this.asignacionesService.crear(cuerpo);

    peticion.subscribe({
      next: (respuesta) => {
        this.guardandoAsignacion.set(false);
        this.drawerAsignacionAbierto.set(false);
        this.cargarAsignaciones();
        for (const advertencia of respuesta.advertencias) {
          this.toast.mostrar({ tipo: 'alerta', mensaje: advertencia });
        }
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Asignación guardada.' });
      },
      error: (error: unknown) => {
        this.guardandoAsignacion.set(false);
        let mensaje = 'No se pudo guardar la asignación.';
        if (error instanceof HttpErrorResponse) {
          const cuerpoError = error.error as Partial<ErrorApi> | null;
          mensaje = cuerpoError?.error?.mensaje ?? mensaje;
        }
        this.toast.mostrar({ tipo: 'error', mensaje });
      },
    });
  }

  constructor() {
    this.cargar();
    this.cargarAsignaciones();
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
