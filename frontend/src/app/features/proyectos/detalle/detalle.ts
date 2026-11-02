import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import {
  AsignacionRecurso,
  ETIQUETAS_ESTADO_PROYECTO,
  ETIQUETAS_ESTADO_TAREA,
  ETIQUETAS_PRIORIDAD,
  ETIQUETAS_TIPO_DEPENDENCIA,
  ETIQUETAS_TIPO_TAREA,
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
import { DependenciaTareaEscritura, DependenciasService } from '../../tareas/data/dependencias.service';
import { FilaCronograma, NodoArbolTarea, TareaEscritura } from '../../tareas/data/tareas.model';
import { TareasService } from '../../tareas/data/tareas.service';
import { ProyectoDetalle } from '../data/proyectos.model';
import { ProyectosService } from '../data/proyectos.service';
import { columnaDeFecha, construirPeriodosMes, construirPeriodosSemana, PeriodoCronograma, rangoFechasDe } from './cronograma.utils';
import { NodoArbolTareaFila } from './nodo-arbol-tarea';

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
    EnConstruccion,
    NodoArbolTareaFila,
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
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
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
    if (id === 'tareas' && this.arbolTareas().length === 0) {
      this.cargarArbolTareas();
    }
    if (id === 'cronograma' && this.filasCronograma().length === 0) {
      this.cargarCronograma();
    }
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
