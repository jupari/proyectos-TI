import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ChartData, ChartOptions } from 'chart.js';

import { AuthService } from '../../../core/auth/auth.service';
import {
  AsignacionRecurso,
  CategoriaRubro,
  ETIQUETAS_CATEGORIA_RUBRO,
  ETIQUETAS_ESTADO_FASE,
  ETIQUETAS_ESTADO_HITO,
  ETIQUETAS_ESTADO_PROYECTO,
  ETIQUETAS_ESTADO_TAREA,
  ETIQUETAS_PRIORIDAD,
  ETIQUETAS_TIPO_DEPENDENCIA,
  ETIQUETAS_TIPO_TAREA,
  ErrorApi,
  EstadoFase,
  EstadoHito,
  GastoEjecutado,
  Hito,
  RubroPresupuesto,
  ResumenTareasTablero,
  Seguimiento,
  TRANSICIONES_PROYECTO,
} from '../../../core/models';
import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, FechaCortaPipe, HorasPipe, MonedaPipe, PorcentajePipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Card } from '../../../shared/ui/card/card';
import { Datepicker } from '../../../shared/ui/datepicker/datepicker';
import { Drawer } from '../../../shared/ui/drawer/drawer';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Grafico } from '../../../shared/ui/grafico/grafico';
import { Input } from '../../../shared/ui/input/input';
import { Modal } from '../../../shared/ui/modal/modal';
import { Numero } from '../../../shared/ui/numero/numero';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Semaforo, ValorSemaforo } from '../../../shared/ui/semaforo/semaforo';
import { PestanaTab, Tabs } from '../../../shared/ui/tabs/tabs';
import { Textarea } from '../../../shared/ui/textarea/textarea';
import { GastoEjecutadoEscritura, GastosService } from '../../ejecucion/data/gastos.service';
import { PanelExpediente } from '../../expediente/panel/panel-expediente';
import { SeguimientosService } from '../../seguimientos/data/seguimientos.service';
import { TableroService } from '../../tablero/data/tablero.service';
import { AsignacionEscritura, AsignacionesService } from '../../recursos/data/asignaciones.service';
import { RecursosService } from '../../recursos/data/recursos.service';
import { DependenciaTareaEscritura, DependenciasService } from '../../tareas/data/dependencias.service';
import { FilaCronograma, NodoArbolTarea, TareaEscritura } from '../../tareas/data/tareas.model';
import { TareasService } from '../../tareas/data/tareas.service';
import { FilaComparativoEjecucion, ProyectoDetalle } from '../data/proyectos.model';
import { HitosService, ProyectosService, RubrosPresupuestoService } from '../data/proyectos.service';
import { columnaDeFecha, construirPeriodosMes, construirPeriodosSemana, PeriodoCronograma, rangoFechasDe } from './cronograma.utils';
import { NodoArbolTareaFila } from './nodo-arbol-tarea';

interface FilaFaseEditable {
  /** Identifica la fila en el array local; es el `id` real si ya existe,
   * o una clave temporal mientras no se haya guardado. */
  clave: string;
  id: string | null;
  nombre: string;
  orden: number;
  peso: number | null;
  fecha_inicio_plan: string | null;
  fecha_fin_plan: string | null;
  estado: EstadoFase;
}

const PESTANAS: PestanaTab[] = [
  { id: 'resumen', etiqueta: 'Resumen' },
  { id: 'fases', etiqueta: 'Fases' },
  { id: 'hitos', etiqueta: 'Hitos' },
  { id: 'presupuesto', etiqueta: 'Presupuesto' },
  { id: 'recursos', etiqueta: 'Recursos' },
  { id: 'tareas', etiqueta: 'Tareas' },
  { id: 'cronograma', etiqueta: 'Cronograma' },
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
    NodoArbolTareaFila,
    PanelExpediente,
    Grafico,
    EstadoVacio,
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
  private readonly tareasService = inject(TareasService);
  private readonly dependenciasService = inject(DependenciasService);
  private readonly gastosService = inject(GastosService);
  private readonly seguimientosService = inject(SeguimientosService);
  private readonly tableroService = inject(TableroService);
  private readonly hitosService = inject(HitosService);
  private readonly rubrosService = inject(RubrosPresupuestoService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly ETIQUETAS_ESTADO_PROYECTO = ETIQUETAS_ESTADO_PROYECTO;
  protected readonly ETIQUETAS_ESTADO_TAREA = ETIQUETAS_ESTADO_TAREA;
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

  // --- pestaña Fases (fase 05, adenda: guardado en lote) -------------------

  protected readonly fasesEditables = signal<FilaFaseEditable[]>([]);
  protected readonly guardandoFases = signal(false);

  protected readonly opcionesEstadoFase: OpcionSelect[] = Object.entries(ETIQUETAS_ESTADO_FASE).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );

  protected readonly sumaPesosFases = computed(() =>
    this.fasesEditables().reduce((total, fase) => total + (fase.peso ?? 0), 0),
  );

  private aFasesEditables(fases: ProyectoDetalle['fases']): FilaFaseEditable[] {
    return fases
      .filter((fase) => fase.activo)
      .slice()
      .sort((a, b) => a.orden - b.orden)
      .map((fase) => ({
        clave: fase.id,
        id: fase.id,
        nombre: fase.nombre,
        orden: fase.orden,
        peso: Number(fase.peso),
        fecha_inicio_plan: fase.fecha_inicio_plan,
        fecha_fin_plan: fase.fecha_fin_plan,
        estado: fase.estado,
      }));
  }

  protected agregarFaseFila(): void {
    const filas = this.fasesEditables();
    const siguienteOrden = filas.length > 0 ? Math.max(...filas.map((f) => f.orden)) + 1 : 1;
    const proyecto = this.proyecto();
    this.fasesEditables.set([
      ...filas,
      {
        clave: `nueva-${Date.now()}`,
        id: null,
        nombre: '',
        orden: siguienteOrden,
        peso: 0,
        fecha_inicio_plan: proyecto?.fecha_inicio_plan ?? null,
        fecha_fin_plan: proyecto?.fecha_fin_plan ?? null,
        estado: 'PENDIENTE',
      },
    ]);
  }

  protected quitarFaseFila(clave: string): void {
    this.fasesEditables.set(this.fasesEditables().filter((f) => f.clave !== clave));
  }

  protected actualizarFaseFila(clave: string, cambios: Partial<FilaFaseEditable>): void {
    this.fasesEditables.set(
      this.fasesEditables().map((f) => (f.clave === clave ? { ...f, ...cambios } : f)),
    );
  }

  protected guardarFases(): void {
    const incompleta = this.fasesEditables().find(
      (f) => !f.nombre.trim() || !f.fecha_inicio_plan || !f.fecha_fin_plan,
    );
    if (incompleta) {
      this.toast.mostrar({
        tipo: 'error',
        mensaje: 'Complete el nombre y las fechas plan de todas las fases.',
      });
      return;
    }

    this.guardandoFases.set(true);
    const cuerpo = this.fasesEditables().map((f) => ({
      ...(f.id ? { id: f.id } : {}),
      nombre: f.nombre.trim(),
      orden: f.orden,
      peso: f.peso ?? 0,
      fecha_inicio_plan: f.fecha_inicio_plan,
      fecha_fin_plan: f.fecha_fin_plan,
      estado: f.estado,
    }));

    this.proyectosService.guardarFasesLote(this.id, cuerpo).subscribe({
      next: (fases) => {
        this.guardandoFases.set(false);
        this.proyecto.update((p) => (p ? { ...p, fases } : p));
        this.fasesEditables.set(this.aFasesEditables(fases));
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Fases guardadas.' });
      },
      error: (error: unknown) => {
        this.guardandoFases.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeDeErrorFases(error) });
      },
    });
  }

  private mensajeDeErrorFases(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const cuerpo = error.error as Partial<ErrorApi> | null;
      const peso = cuerpo?.error?.detalles?.['peso'] as unknown as string[] | undefined;
      if (peso?.length) return peso[0];
      return cuerpo?.error?.mensaje ?? 'No se pudieron guardar las fases.';
    }
    return 'No se pudieron guardar las fases.';
  }

  // --- pestaña Hitos (fase 05) ----------------------------------------------

  protected readonly drawerHitoAbierto = signal(false);
  protected readonly idHitoEnEdicion = signal<string | null>(null);
  protected readonly hitoNombre = signal('');
  protected readonly hitoDescripcion = signal('');
  protected readonly hitoFechaPlan = signal<string | null>(null);
  protected readonly hitoFechaReal = signal<string | null>(null);
  protected readonly hitoEstado = signal<EstadoHito>('PENDIENTE');
  protected readonly hitoCriterioCumplimiento = signal('');
  protected readonly hitoEsEntregable = signal(false);
  protected readonly guardandoHito = signal(false);

  protected readonly opcionesEstadoHito: OpcionSelect[] = Object.entries(ETIQUETAS_ESTADO_HITO).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );

  protected abrirNuevoHito(): void {
    this.idHitoEnEdicion.set(null);
    this.hitoNombre.set('');
    this.hitoDescripcion.set('');
    this.hitoFechaPlan.set(null);
    this.hitoFechaReal.set(null);
    this.hitoEstado.set('PENDIENTE');
    this.hitoCriterioCumplimiento.set('');
    this.hitoEsEntregable.set(false);
    this.drawerHitoAbierto.set(true);
  }

  protected abrirEditarHito(hito: Hito): void {
    this.idHitoEnEdicion.set(hito.id);
    this.hitoNombre.set(hito.nombre);
    this.hitoDescripcion.set(hito.descripcion);
    this.hitoFechaPlan.set(hito.fecha_plan);
    this.hitoFechaReal.set(hito.fecha_real);
    this.hitoEstado.set(hito.estado);
    this.hitoCriterioCumplimiento.set(hito.criterio_cumplimiento);
    this.hitoEsEntregable.set(hito.es_entregable);
    this.drawerHitoAbierto.set(true);
  }

  protected cerrarDrawerHito(): void {
    this.drawerHitoAbierto.set(false);
  }

  protected guardarHito(): void {
    if (!this.hitoNombre().trim() || !this.hitoFechaPlan()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete el nombre y la fecha plan.' });
      return;
    }

    const cuerpo = {
      proyecto: this.id,
      nombre: this.hitoNombre().trim(),
      descripcion: this.hitoDescripcion(),
      fecha_plan: this.hitoFechaPlan()!,
      fecha_real: this.hitoFechaReal(),
      estado: this.hitoEstado(),
      criterio_cumplimiento: this.hitoCriterioCumplimiento(),
      es_entregable: this.hitoEsEntregable(),
    };

    this.guardandoHito.set(true);
    const id = this.idHitoEnEdicion();
    const peticion = id ? this.hitosService.actualizar(id, cuerpo) : this.hitosService.crear(cuerpo);
    peticion.subscribe({
      next: () => {
        this.guardandoHito.set(false);
        this.drawerHitoAbierto.set(false);
        this.cargar();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Hito guardado.' });
      },
      error: (error: unknown) => {
        this.guardandoHito.set(false);
        this.toast.mostrar({
          tipo: 'error',
          mensaje: this.mensajeDeError(error, 'No se pudo guardar el hito.'),
        });
      },
    });
  }

  protected async eliminarHito(hito: Hito): Promise<void> {
    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Eliminar hito',
      mensaje: `¿Eliminar el hito «${hito.nombre}»?`,
      variante: 'peligro',
      textoConfirmar: 'Eliminar',
    });
    if (!confirmado) return;

    this.hitosService.eliminar(hito.id).subscribe({
      next: () => {
        this.cargar();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Hito eliminado.' });
      },
      error: (error: unknown) => {
        this.toast.mostrar({
          tipo: 'error',
          mensaje: this.mensajeDeError(error, 'No se pudo eliminar el hito.'),
        });
      },
    });
  }

  // --- pestaña Presupuesto (fase 05) -----------------------------------------

  protected readonly drawerRubroAbierto = signal(false);
  protected readonly idRubroEnEdicion = signal<string | null>(null);
  protected readonly rubroCategoria = signal<string | null>('OTROS');
  protected readonly rubroDescripcion = signal('');
  protected readonly rubroMontoPlaneado = signal<number | null>(null);
  protected readonly guardandoRubro = signal(false);

  protected readonly opcionesCategoriaRubro: OpcionSelect[] = Object.entries(
    ETIQUETAS_CATEGORIA_RUBRO,
  ).map(([valor, etiqueta]) => ({ valor, etiqueta }));

  protected abrirNuevoRubro(): void {
    this.idRubroEnEdicion.set(null);
    this.rubroCategoria.set('OTROS');
    this.rubroDescripcion.set('');
    this.rubroMontoPlaneado.set(null);
    this.drawerRubroAbierto.set(true);
  }

  protected abrirEditarRubro(rubro: RubroPresupuesto): void {
    this.idRubroEnEdicion.set(rubro.id);
    this.rubroCategoria.set(rubro.categoria);
    this.rubroDescripcion.set(rubro.descripcion);
    this.rubroMontoPlaneado.set(Number(rubro.monto_planeado));
    this.drawerRubroAbierto.set(true);
  }

  protected cerrarDrawerRubro(): void {
    this.drawerRubroAbierto.set(false);
  }

  protected guardarRubro(): void {
    if (!this.rubroCategoria() || !this.rubroDescripcion().trim() || !this.rubroMontoPlaneado()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete los campos obligatorios.' });
      return;
    }

    const cuerpo: Partial<RubroPresupuesto> = {
      proyecto: this.id,
      categoria: this.rubroCategoria()! as CategoriaRubro,
      descripcion: this.rubroDescripcion().trim(),
      monto_planeado: this.rubroMontoPlaneado() as unknown as string,
    };

    this.guardandoRubro.set(true);
    const id = this.idRubroEnEdicion();
    const peticion = id
      ? this.rubrosService.actualizar(id, cuerpo)
      : this.rubrosService.crear(cuerpo);
    peticion.subscribe({
      next: () => {
        this.guardandoRubro.set(false);
        this.drawerRubroAbierto.set(false);
        this.cargar();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Rubro guardado.' });
      },
      error: (error: unknown) => {
        this.guardandoRubro.set(false);
        this.toast.mostrar({
          tipo: 'error',
          mensaje: this.mensajeDeError(error, 'No se pudo guardar el rubro.'),
        });
      },
    });
  }

  protected async eliminarRubro(rubro: RubroPresupuesto): Promise<void> {
    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Eliminar rubro',
      mensaje: `¿Eliminar el rubro «${rubro.descripcion}»?`,
      variante: 'peligro',
      textoConfirmar: 'Eliminar',
    });
    if (!confirmado) return;

    this.rubrosService.eliminar(rubro.id).subscribe({
      next: () => {
        this.cargar();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Rubro eliminado.' });
      },
      error: (error: unknown) => {
        this.toast.mostrar({
          tipo: 'error',
          mensaje: this.mensajeDeError(error, 'No se pudo eliminar el rubro.'),
        });
      },
    });
  }

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

  protected abrirEditarAsignacion(asignacion: AsignacionRecurso): void {
    this.idAsignacionEnEdicion.set(asignacion.id);
    this.asigRecurso.set(asignacion.recurso);
    this.asigRolEnProyecto.set(asignacion.rol_en_proyecto);
    this.asigFechaDesde.set(asignacion.fecha_desde);
    this.asigFechaHasta.set(asignacion.fecha_hasta);
    this.asigPorcentajeDedicacion.set(Number(asignacion.porcentaje_dedicacion));
    this.asigHorasPlaneadas.set(Number(asignacion.horas_planeadas));
    this.asigValorHoraPlan.set(Number(asignacion.valor_hora_plan));
    this.asigTarifaManual.set(true);
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
        this.cargarEjecucion();
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

  // --- pestaña Tareas (fase 07) -----------------------------------------

  protected readonly cargandoTareas = signal(false);
  protected readonly arbolTareas = signal<NodoArbolTarea[]>([]);
  protected readonly totalesPorFase = signal<{ fase: string; estimadas: number; ejecutadas: number }[]>(
    [],
  );
  private readonly nodosExpandidos = signal<Set<string>>(new Set());

  protected readonly opcionesFases = computed<OpcionSelect[]>(() =>
    (this.proyecto()?.fases ?? []).map((f) => ({ valor: f.id, etiqueta: f.nombre })),
  );
  protected readonly opcionesTipoTarea: OpcionSelect[] = Object.entries(ETIQUETAS_TIPO_TAREA).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );
  protected readonly opcionesPrioridadTarea: OpcionSelect[] = Object.entries(ETIQUETAS_PRIORIDAD).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );
  protected readonly opcionesTipoDependencia: OpcionSelect[] = Object.entries(
    ETIQUETAS_TIPO_DEPENDENCIA,
  ).map(([valor, etiqueta]) => ({ valor, etiqueta }));

  protected readonly drawerTareaAbierto = signal(false);
  protected readonly idTareaEnEdicion = signal<string | null>(null);
  protected readonly tarPadreId = signal<string | null>(null);
  protected readonly tarFase = signal<string | null>(null);
  protected readonly tarNombre = signal('');
  protected readonly tarDescripcion = signal('');
  protected readonly tarTipo = signal<string | null>('TAREA');
  protected readonly tarPrioridad = signal<string | null>('MEDIA');
  protected readonly tarResponsable = signal<string | null>(null);
  protected readonly tarFechaInicioPlan = signal<string | null>(null);
  protected readonly tarFechaFinPlan = signal<string | null>(null);
  protected readonly tarHorasEstimadas = signal<number | null>(null);
  protected readonly tarMotivoCreacion = signal('');
  protected readonly tarClaveJira = signal('');
  protected readonly guardandoTarea = signal(false);

  protected readonly necesitaMotivoCreacion = computed(
    () => !this.idTareaEnEdicion() && this.proyecto()?.estado === 'EJECUCION',
  );

  protected readonly dependenciasEntrantes = signal<
    { id: string; tarea_origen_codigo: string; tipo: string; dias_desfase: number }[]
  >([]);
  protected readonly dependenciasSalientes = signal<
    { id: string; tarea_destino_codigo: string; tipo: string; dias_desfase: number }[]
  >([]);
  protected readonly depTareaDestinoId = signal<string | null>(null);
  protected readonly depTipo = signal<string | null>('FI');
  protected readonly depDiasDesfase = signal<number | null>(0);
  protected readonly guardandoDependencia = signal(false);
  protected readonly sugiriendoFechas = signal(false);

  protected readonly opcionesOtrasTareas = computed<OpcionSelect[]>(() => {
    const idActual = this.idTareaEnEdicion();
    return this.aplanarArbol(this.arbolTareas())
      .filter((t) => t.id !== idActual)
      .map((t) => ({ valor: t.id, etiqueta: `${t.codigo} — ${t.nombre}` }));
  });

  private aplanarArbol(nodos: NodoArbolTarea[]): NodoArbolTarea[] {
    return nodos.flatMap((n) => [n, ...this.aplanarArbol(n.subtareas)]);
  }

  protected estaExpandidoFn = (id: string): boolean => this.nodosExpandidos().has(id);

  protected alAlternarNodo = (id: string): void => {
    const copia = new Set(this.nodosExpandidos());
    if (copia.has(id)) {
      copia.delete(id);
    } else {
      copia.add(id);
    }
    this.nodosExpandidos.set(copia);
  };

  private cargarArbolTareas(): void {
    this.cargandoTareas.set(true);
    this.tareasService.arbol(this.id).subscribe({
      next: (arbol) => {
        this.arbolTareas.set(arbol);
        this.cargandoTareas.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el árbol de tareas.' });
        this.cargandoTareas.set(false);
      },
    });
    this.tareasService.listarTareas({ proyecto: this.id, page_size: 200 }).subscribe((r) => {
      const totales = new Map<string, { estimadas: number; ejecutadas: number }>();
      for (const tarea of r.results) {
        const clave = tarea.fase_nombre ?? 'Sin fase';
        const actual = totales.get(clave) ?? { estimadas: 0, ejecutadas: 0 };
        actual.estimadas += Number(tarea.horas_estimadas);
        actual.ejecutadas += Number(tarea.horas_ejecutadas);
        totales.set(clave, actual);
      }
      this.totalesPorFase.set(
        [...totales.entries()].map(([fase, t]) => ({ fase, ...t })),
      );
    });
  }

  protected alCrearSubtareaFn = (padreId: string): void => {
    this.abrirDrawerTarea({ padreId });
  };

  protected alEditarTareaFn = (id: string): void => {
    this.abrirDrawerTarea({ idExistente: id });
  };

  protected abrirNuevaTareaRaiz(): void {
    this.abrirDrawerTarea({});
  }

  private abrirDrawerTarea(opciones: { padreId?: string; idExistente?: string }): void {
    this.idTareaEnEdicion.set(opciones.idExistente ?? null);
    this.tarPadreId.set(opciones.padreId ?? null);
    this.tarFase.set(null);
    this.tarNombre.set('');
    this.tarDescripcion.set('');
    this.tarTipo.set('TAREA');
    this.tarPrioridad.set('MEDIA');
    this.tarResponsable.set(null);
    this.tarFechaInicioPlan.set(this.proyecto()?.fecha_inicio_plan ?? null);
    this.tarFechaFinPlan.set(null);
    this.tarHorasEstimadas.set(null);
    this.tarMotivoCreacion.set('');
    this.tarClaveJira.set('');
    this.dependenciasEntrantes.set([]);
    this.dependenciasSalientes.set([]);
    this.drawerTareaAbierto.set(true);

    if (opciones.idExistente) {
      this.tareasService.obtenerDetalle(opciones.idExistente).subscribe((tarea) => {
        this.tarFase.set(tarea.fase);
        this.tarNombre.set(tarea.nombre);
        this.tarDescripcion.set(tarea.descripcion);
        this.tarTipo.set(tarea.tipo);
        this.tarPrioridad.set(tarea.prioridad);
        this.tarResponsable.set(tarea.responsable);
        this.tarFechaInicioPlan.set(tarea.fecha_inicio_plan);
        this.tarFechaFinPlan.set(tarea.fecha_fin_plan);
        this.tarHorasEstimadas.set(Number(tarea.horas_estimadas));
        this.tarClaveJira.set(tarea.clave_jira ?? '');
        this.dependenciasEntrantes.set(tarea.dependencias_entrantes);
        this.dependenciasSalientes.set(tarea.dependencias_salientes);
      });
    }
  }

  protected cerrarDrawerTarea(): void {
    this.drawerTareaAbierto.set(false);
  }

  protected guardarTarea(): void {
    if (
      !this.tarNombre().trim() ||
      !this.tarFechaInicioPlan() ||
      !this.tarFechaFinPlan() ||
      !this.tarHorasEstimadas()
    ) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete los campos obligatorios.' });
      return;
    }
    if (this.necesitaMotivoCreacion() && !this.tarMotivoCreacion().trim()) {
      this.toast.mostrar({
        tipo: 'error',
        mensaje: 'El proyecto está en ejecución: indique el motivo de la creación.',
      });
      return;
    }

    const cuerpo: TareaEscritura = {
      proyecto: this.id,
      fase: this.tarFase(),
      tarea_padre: this.tarPadreId(),
      nombre: this.tarNombre().trim(),
      descripcion: this.tarDescripcion(),
      tipo: this.tarTipo() ?? 'TAREA',
      prioridad: this.tarPrioridad() ?? 'MEDIA',
      responsable: this.tarResponsable(),
      fecha_inicio_plan: this.tarFechaInicioPlan()!,
      fecha_fin_plan: this.tarFechaFinPlan()!,
      fecha_inicio_real: null,
      fecha_fin_real: null,
      horas_estimadas: this.tarHorasEstimadas()!,
      motivo_creacion: this.tarMotivoCreacion().trim(),
      clave_jira: this.tarClaveJira().trim() || null,
    };

    this.guardandoTarea.set(true);
    const idExistente = this.idTareaEnEdicion();
    const peticion = idExistente
      ? this.tareasService.actualizarTarea(idExistente, cuerpo)
      : this.tareasService.crearTarea(cuerpo);

    peticion.subscribe({
      next: (tarea) => {
        this.guardandoTarea.set(false);
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Tarea guardada.' });
        this.cargarArbolTareas();
        if (!idExistente) {
          // Queda en modo edición para poder añadir dependencias de inmediato.
          this.idTareaEnEdicion.set(tarea.id);
          this.tarPadreId.set(tarea.tarea_padre);
        } else {
          this.drawerTareaAbierto.set(false);
        }
      },
      error: (error: unknown) => {
        this.guardandoTarea.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeDeError(error, 'No se pudo guardar la tarea.') });
      },
    });
  }

  protected sugerirFechasEnDrawer(): void {
    const id = this.idTareaEnEdicion();
    if (!id) {
      this.toast.mostrar({
        tipo: 'alerta',
        mensaje: 'Guarde la tarea primero para poder sugerir fechas con sus dependencias.',
      });
      return;
    }
    this.sugiriendoFechas.set(true);
    this.tareasService.fechasSugeridas(id).subscribe({
      next: (resultado) => {
        this.sugiriendoFechas.set(false);
        if (resultado.fecha_inicio_sugerida) {
          this.tarFechaInicioPlan.set(resultado.fecha_inicio_sugerida);
        }
        if (resultado.fecha_fin_sugerida) {
          this.tarFechaFinPlan.set(resultado.fecha_fin_sugerida);
        }
      },
      error: () => {
        this.sugiriendoFechas.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo calcular la sugerencia.' });
      },
    });
  }

  protected guardarDependenciaEnDrawer(): void {
    const origenId = this.idTareaEnEdicion();
    const destinoId = this.depTareaDestinoId();
    const tipo = this.depTipo();
    if (!origenId || !destinoId || !tipo) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Indique la tarea sucesora y el tipo.' });
      return;
    }

    const cuerpo: DependenciaTareaEscritura = {
      tarea_origen: origenId,
      tarea_destino: destinoId,
      tipo: tipo as DependenciaTareaEscritura['tipo'],
      dias_desfase: this.depDiasDesfase() ?? 0,
    };

    this.guardandoDependencia.set(true);
    this.dependenciasService.crear(cuerpo).subscribe({
      next: () => {
        this.guardandoDependencia.set(false);
        this.depTareaDestinoId.set(null);
        this.depDiasDesfase.set(0);
        this.abrirDrawerTarea({ idExistente: origenId });
      },
      error: (error: unknown) => {
        this.guardandoDependencia.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeDeErrorCiclo(error) });
      },
    });
  }

  protected eliminarDependenciaEnDrawer(id: string): void {
    const origenId = this.idTareaEnEdicion();
    if (!origenId) return;
    this.dependenciasService.eliminar(id).subscribe(() => this.abrirDrawerTarea({ idExistente: origenId }));
  }

  private mensajeDeError(error: unknown, porDefecto: string): string {
    if (error instanceof HttpErrorResponse) {
      const cuerpo = error.error as Partial<ErrorApi> | null;
      return cuerpo?.error?.mensaje ?? porDefecto;
    }
    return porDefecto;
  }

  private mensajeDeErrorCiclo(error: unknown): string {
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

  // --- pestaña Cronograma (fase 07) ----------------------------------------

  protected readonly cargandoCronograma = signal(false);
  protected readonly filasCronograma = signal<FilaCronograma[]>([]);
  protected readonly escalaCronograma = signal<'semana' | 'mes'>('semana');

  protected readonly periodosCronograma = computed<PeriodoCronograma[]>(() => {
    const filas = this.filasCronograma();
    const hitos = this.proyecto()?.hitos ?? [];
    const fechas = [
      ...filas.flatMap((f) => [f.inicio_plan, f.fin_plan, f.inicio_real, f.fin_real]),
      ...hitos.map((h) => h.fecha_plan),
    ];
    const rango = rangoFechasDe(fechas);
    if (!rango) return [];
    return this.escalaCronograma() === 'semana'
      ? construirPeriodosSemana(rango.minimo, rango.maximo)
      : construirPeriodosMes(rango.minimo, rango.maximo);
  });

  protected cambiarEscalaCronograma(escala: 'semana' | 'mes'): void {
    this.escalaCronograma.set(escala);
  }

  private cargarCronograma(): void {
    this.cargandoCronograma.set(true);
    this.proyectosService.cronograma(this.id).subscribe({
      next: (filas) => {
        this.filasCronograma.set(filas);
        this.cargandoCronograma.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el cronograma.' });
        this.cargandoCronograma.set(false);
      },
    });
  }

  protected columnaInicioPlan(fila: FilaCronograma): number {
    return columnaDeFecha(fila.inicio_plan, this.periodosCronograma());
  }

  protected columnaFinPlan(fila: FilaCronograma): number {
    return columnaDeFecha(fila.fin_plan, this.periodosCronograma()) + 1;
  }

  protected columnaInicioReal(fila: FilaCronograma): number | null {
    return fila.inicio_real ? columnaDeFecha(fila.inicio_real, this.periodosCronograma()) : null;
  }

  protected columnaFinReal(fila: FilaCronograma): number | null {
    return fila.fin_real ? columnaDeFecha(fila.fin_real, this.periodosCronograma()) + 1 : null;
  }

  protected columnaHito(fechaIso: string): number {
    return columnaDeFecha(fechaIso, this.periodosCronograma());
  }

  protected tituloDependencias(fila: FilaCronograma): string {
    if (fila.dependencias.length === 0) return 'Sin dependencias.';
    const codigoDe = new Map(this.filasCronograma().map((f) => [f.tarea_id, f.codigo]));
    return `Depende de: ${fila.dependencias
      .map((d) => `${codigoDe.get(d.tarea_id) ?? d.tarea_id} (${d.tipo})`)
      .join(', ')}`;
  }

  // --- pestaña Ejecución (fase 08) -----------------------------------------

  protected readonly cargandoEjecucion = signal(false);
  protected readonly comparativoPorRecurso = signal<FilaComparativoEjecucion[]>([]);
  protected readonly comparativoPorMes = signal<FilaComparativoEjecucion[]>([]);
  protected readonly gastos = signal<GastoEjecutado[]>([]);

  protected readonly opcionesRubros = computed<OpcionSelect[]>(() =>
    (this.proyecto()?.rubros ?? []).map((r) => ({ valor: r.id, etiqueta: r.descripcion })),
  );

  protected readonly puedeCrearGasto = computed(() => this.auth.tienePermiso('ejecucion.registrar'));

  protected readonly drawerGastoAbierto = signal(false);
  protected readonly gastoRubro = signal<string | null>(null);
  protected readonly gastoMonto = signal<number | null>(null);
  protected readonly gastoProveedor = signal('');
  protected readonly gastoNumeroDocumento = signal('');
  protected readonly gastoFecha = signal<string | null>(null);
  protected readonly guardandoGasto = signal(false);

  private cargarEjecucion(): void {
    this.cargandoEjecucion.set(true);
    this.proyectosService.ejecucion(this.id).subscribe({
      next: (comparativo) => {
        this.comparativoPorRecurso.set(comparativo.por_recurso);
        this.comparativoPorMes.set(comparativo.por_mes);
        this.cargandoEjecucion.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la ejecución.' });
        this.cargandoEjecucion.set(false);
      },
    });
    this.gastosService.listar({ proyecto: this.id }).subscribe((r) => this.gastos.set(r.results));
  }

  protected claseConsumo(pct: number | null): string {
    if (pct === null) return 'bg-neutro-100 text-neutro-500';
    if (pct > 100) return 'bg-peligro/10 text-peligro';
    if (pct >= 90) return 'bg-alerta/10 text-alerta';
    return 'bg-exito/10 text-exito';
  }

  protected etiquetaMes(fila: FilaComparativoEjecucion): string {
    return `${fila.anio}-${String(fila.mes).padStart(2, '0')}`;
  }

  protected abrirNuevoGasto(): void {
    this.gastoRubro.set(null);
    this.gastoMonto.set(null);
    this.gastoProveedor.set('');
    this.gastoNumeroDocumento.set('');
    this.gastoFecha.set(null);
    this.drawerGastoAbierto.set(true);
  }

  protected cerrarDrawerGasto(): void {
    this.drawerGastoAbierto.set(false);
  }

  protected guardarGasto(): void {
    if (!this.gastoRubro() || !this.gastoMonto() || !this.gastoFecha()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete los campos obligatorios.' });
      return;
    }

    const cuerpo: GastoEjecutadoEscritura = {
      proyecto: this.id,
      rubro: this.gastoRubro()!,
      fecha: this.gastoFecha()!,
      monto: this.gastoMonto()!,
      proveedor: this.gastoProveedor(),
      numero_documento: this.gastoNumeroDocumento(),
      descripcion: '',
    };

    this.guardandoGasto.set(true);
    this.gastosService.crearGasto(cuerpo).subscribe({
      next: () => {
        this.guardandoGasto.set(false);
        this.drawerGastoAbierto.set(false);
        this.cargarEjecucion();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Gasto registrado.' });
      },
      error: (error: unknown) => {
        this.guardandoGasto.set(false);
        this.toast.mostrar({
          tipo: 'error',
          mensaje: this.mensajeDeError(error, 'No se pudo registrar el gasto.'),
        });
      },
    });
  }

  // --- flujo de aprobación de gastos (BORRADOR -> ENVIADO -> APROBADO) ------

  protected readonly puedeAprobarGasto = computed(() => this.auth.tienePermiso('gastos.aprobar'));
  protected readonly procesandoGasto = signal(false);
  protected readonly dialogoRechazoGastoAbierto = signal(false);
  protected readonly gastoARechazar = signal<GastoEjecutado | null>(null);
  protected readonly motivoRechazoGasto = signal('');

  protected async enviarGasto(gasto: GastoEjecutado): Promise<void> {
    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Enviar a aprobación',
      mensaje: `¿Enviar el gasto de «${gasto.rubro_descripcion}» a aprobación?`,
      textoConfirmar: 'Enviar',
    });
    if (!confirmado) return;

    this.procesandoGasto.set(true);
    this.gastosService.enviar(gasto.id).subscribe({
      next: () => {
        this.procesandoGasto.set(false);
        this.cargarEjecucion();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Gasto enviado a aprobación.' });
      },
      error: (error: unknown) => {
        this.procesandoGasto.set(false);
        this.toast.mostrar({
          tipo: 'error',
          mensaje: this.mensajeDeError(error, 'No se pudo enviar el gasto.'),
        });
      },
    });
  }

  protected async aprobarGasto(gasto: GastoEjecutado): Promise<void> {
    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Aprobar gasto',
      mensaje: `¿Aprobar el gasto de «${gasto.rubro_descripcion}»? Quedará contado como ejecutado.`,
      textoConfirmar: 'Aprobar',
    });
    if (!confirmado) return;

    this.procesandoGasto.set(true);
    this.gastosService.aprobar(gasto.id).subscribe({
      next: () => {
        this.procesandoGasto.set(false);
        this.cargarEjecucion();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Gasto aprobado.' });
      },
      error: (error: unknown) => {
        this.procesandoGasto.set(false);
        this.toast.mostrar({
          tipo: 'error',
          mensaje: this.mensajeDeError(error, 'No se pudo aprobar el gasto.'),
        });
      },
    });
  }

  protected abrirRechazoGasto(gasto: GastoEjecutado): void {
    this.gastoARechazar.set(gasto);
    this.motivoRechazoGasto.set('');
    this.dialogoRechazoGastoAbierto.set(true);
  }

  protected cerrarRechazoGasto(): void {
    this.dialogoRechazoGastoAbierto.set(false);
    this.gastoARechazar.set(null);
  }

  protected confirmarRechazoGasto(): void {
    const gasto = this.gastoARechazar();
    const motivo = this.motivoRechazoGasto().trim();
    if (!gasto) return;
    if (!motivo) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Escriba el motivo del rechazo.' });
      return;
    }

    this.procesandoGasto.set(true);
    this.gastosService.rechazar(gasto.id, motivo).subscribe({
      next: () => {
        this.procesandoGasto.set(false);
        this.dialogoRechazoGastoAbierto.set(false);
        this.gastoARechazar.set(null);
        this.cargarEjecucion();
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Gasto rechazado.' });
      },
      error: (error: unknown) => {
        this.procesandoGasto.set(false);
        this.toast.mostrar({
          tipo: 'error',
          mensaje: this.mensajeDeError(error, 'No se pudo rechazar el gasto.'),
        });
      },
    });
  }

  // --- Gráficos de la pestaña Resumen (fase 10 §10.3.8) --------------------

  protected readonly resumenTareas = signal<ResumenTareasTablero | null>(null);

  private readonly MARCA_400 = '#60a5fa';
  private readonly MARCA_900 = '#1e3a8a';
  private readonly SEMAFORO: Record<string, string> = {
    PENDIENTE: '#94a3b8',
    EN_PROGRESO: '#60a5fa',
    BLOQUEADA: '#dc2626',
    EN_REVISION: '#eab308',
    COMPLETADA: '#16a34a',
    CANCELADA: '#334155',
  };

  protected readonly graficoEjecucionMensual = computed<ChartData>(() => {
    const serie = this.comparativoPorMes();
    return {
      labels: serie.map((fila) => this.etiquetaMes(fila)),
      datasets: [
        { label: 'Horas plan', data: serie.map((f) => f.horas_plan), borderColor: this.MARCA_400, backgroundColor: 'transparent' },
        { label: 'Horas ejec.', data: serie.map((f) => f.horas_ejec), borderColor: this.MARCA_900, backgroundColor: 'transparent' },
      ],
    };
  });

  protected readonly filasTablaEjecucionMensual = computed(() =>
    this.comparativoPorMes().map((f) => [this.etiquetaMes(f), f.horas_plan, f.horas_ejec]),
  );

  protected readonly graficoPorRecurso = computed<ChartData>(() => {
    const filas = this.comparativoPorRecurso();
    return {
      labels: filas.map((f) => f.recurso_nombre ?? ''),
      datasets: [
        { label: 'Horas plan', data: filas.map((f) => f.horas_plan), backgroundColor: this.MARCA_400 },
        { label: 'Horas ejec.', data: filas.map((f) => f.horas_ejec), backgroundColor: this.MARCA_900 },
      ],
    };
  });

  protected readonly filasTablaPorRecurso = computed(() =>
    this.comparativoPorRecurso().map((f) => [f.recurso_nombre ?? '', f.horas_plan, f.horas_ejec]),
  );

  protected readonly graficoTareasPorEstado = computed<ChartData>(() => {
    const porEstado = this.resumenTareas()?.por_estado ?? {};
    const estados = Object.keys(porEstado);
    return {
      labels: estados.map((estado) => ETIQUETAS_ESTADO_TAREA[estado as keyof typeof ETIQUETAS_ESTADO_TAREA] ?? estado),
      datasets: [
        {
          label: 'Tareas',
          data: estados.map((estado) => porEstado[estado]),
          backgroundColor: estados.map((estado) => this.SEMAFORO[estado] ?? '#94a3b8'),
        },
      ],
    };
  });

  protected readonly filasTablaTareasPorEstado = computed(() => {
    const porEstado = this.resumenTareas()?.por_estado ?? {};
    return Object.entries(porEstado).map(([estado, total]) => [
      ETIQUETAS_ESTADO_TAREA[estado as keyof typeof ETIQUETAS_ESTADO_TAREA] ?? estado,
      total,
    ]);
  });

  protected readonly opcionesGraficoSinLeyenda: ChartOptions = {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
  };

  protected readonly graficoAvanceSeguimientos = computed<ChartData>(() => {
    const seguimientos = [...this.seguimientosProyecto()].sort((a, b) =>
      a.periodo_inicio.localeCompare(b.periodo_inicio),
    );
    return {
      labels: seguimientos.map((s) => s.periodo_inicio),
      datasets: [
        {
          label: 'Avance reportado',
          data: seguimientos.map((s) => Number(s.avance_reportado)),
          borderColor: this.MARCA_900,
          backgroundColor: 'transparent',
        },
      ],
    };
  });

  protected readonly filasTablaAvanceSeguimientos = computed(() =>
    [...this.seguimientosProyecto()]
      .sort((a, b) => a.periodo_inicio.localeCompare(b.periodo_inicio))
      .map((s) => [s.periodo_inicio, s.avance_reportado]),
  );

  private cargarResumenTareas(): void {
    this.tableroService.tareas({ proyecto: this.id }).subscribe({
      next: (respuesta) => this.resumenTareas.set(respuesta),
      error: () => undefined,
    });
  }

  constructor() {
    this.cargar();
    this.cargarAsignaciones();
    // La pestaña Resumen es la activa por defecto, así que su ejecución
    // mensual/por-recurso y su distribución de tareas se cargan de una vez
    // (no de forma perezosa como las demás pestañas en `cambiarPestana`).
    this.cargarEjecucion();
    this.cargarResumenTareas();
    this.cargarSeguimientos();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.proyectosService.obtenerDetalle(this.id).subscribe({
      next: (proyecto) => {
        this.proyecto.set(proyecto);
        this.fasesEditables.set(this.aFasesEditables(proyecto.fases));
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
    if (id === 'tareas' && this.arbolTareas().length === 0) {
      this.cargarArbolTareas();
    }
    if (id === 'cronograma' && this.filasCronograma().length === 0) {
      this.cargarCronograma();
    }
    if (id === 'ejecucion' && this.comparativoPorRecurso().length === 0 && this.gastos().length === 0) {
      this.cargarEjecucion();
    }
    if (id === 'seguimientos' && this.seguimientosProyecto().length === 0) {
      this.cargarSeguimientos();
    }
  }

  protected readonly cargandoSeguimientos = signal(false);
  protected readonly seguimientosProyecto = signal<Seguimiento[]>([]);

  private cargarSeguimientos(): void {
    this.cargandoSeguimientos.set(true);
    this.seguimientosService.listarSeguimientos({ proyecto: this.id, page_size: 50 }).subscribe({
      next: (respuesta) => {
        this.seguimientosProyecto.set(respuesta.results);
        this.cargandoSeguimientos.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudieron cargar los seguimientos.' });
        this.cargandoSeguimientos.set(false);
      },
    });
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
