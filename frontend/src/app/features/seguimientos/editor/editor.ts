import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { ETIQUETAS_ESTADO_COMPROMISO, ErrorApi, Seguimiento, Usuario } from '../../../core/models';
import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { ToastService } from '../../../core/ui/toast.service';
import { HorasPipe, MonedaPipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Card } from '../../../shared/ui/card/card';
import { Datepicker } from '../../../shared/ui/datepicker/datepicker';
import { Modal } from '../../../shared/ui/modal/modal';
import { Numero } from '../../../shared/ui/numero/numero';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Semaforo, ValorSemaforo } from '../../../shared/ui/semaforo/semaforo';
import { Textarea } from '../../../shared/ui/textarea/textarea';
import { UsuariosService } from '../../admin/data/usuarios.service';
import { DocumentosService } from '../../expediente/data/documentos.service';
import { ProyectosService } from '../../proyectos/data/proyectos.service';
import { CompromisosService } from '../data/compromisos.service';
import { PrecargaSeguimiento, SeguimientoEscritura } from '../data/seguimientos.model';
import { SeguimientosService } from '../data/seguimientos.service';

interface FilaCompromiso {
  id: string | null;
  descripcion: string;
  responsable: string | null;
  fecha_compromiso: string | null;
  estado: string;
  tarea: string | null;
  tarea_codigo: string | null;
  guardando: boolean;
}

@Component({
  selector: 'app-editor-seguimiento',
  templateUrl: './editor.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Card,
    Badge,
    Semaforo,
    Boton,
    Select,
    Datepicker,
    Modal,
    Numero,
    Textarea,
    HorasPipe,
    MonedaPipe,
  ],
})
export class EditorSeguimiento {
  private readonly seguimientosService = inject(SeguimientosService);
  private readonly proyectosService = inject(ProyectosService);
  private readonly compromisosService = inject(CompromisosService);
  private readonly documentosService = inject(DocumentosService);
  private readonly usuariosService = inject(UsuariosService);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  private readonly idActual = this.ruta.snapshot.paramMap.get('id');
  protected readonly esNuevo = this.idActual === null;

  protected readonly cargando = signal(true);
  protected readonly guardando = signal(false);
  protected readonly publicando = signal(false);
  protected readonly precargando = signal(false);

  protected readonly seguimiento = signal<Seguimiento | null>(null);
  protected readonly precarga = signal<PrecargaSeguimiento | null>(null);

  // --- paso 1: identidad del seguimiento (fija una vez guardado) -----------

  protected readonly proyectoSel = signal<string | null>(null);
  protected readonly periodicidadSel = signal<string>('MENSUAL');
  protected readonly periodoInicioSel = signal<string | null>(null);
  protected readonly opcionesProyectos = signal<OpcionSelect[]>([]);
  protected readonly opcionesPeriodicidad: OpcionSelect[] = [
    { valor: 'DIARIA', etiqueta: 'Diaria' },
    { valor: 'SEMANAL', etiqueta: 'Semanal' },
    { valor: 'MENSUAL', etiqueta: 'Mensual' },
  ];

  // --- bloque editable -------------------------------------------------------

  protected readonly avanceAnterior = signal<string | null>(null);
  protected readonly avanceReportado = signal<number | null>(null);
  protected readonly semaforoDeclarado = signal<ValorSemaforo>('VERDE');
  protected readonly justificacionSemaforo = signal('');
  protected readonly logros = signal('');
  protected readonly dificultades = signal('');
  protected readonly riesgos = signal('');
  protected readonly accionesSiguientes = signal('');

  protected readonly opcionesSemaforo: { valor: ValorSemaforo; etiqueta: string }[] = [
    { valor: 'VERDE', etiqueta: 'Verde' },
    { valor: 'AMARILLO', etiqueta: 'Amarillo' },
    { valor: 'ROJO', etiqueta: 'Rojo' },
  ];

  protected readonly necesitaJustificacion = computed(() => {
    const calculado = this.precarga()?.semaforo_calculado;
    return !!calculado && calculado !== this.semaforoDeclarado();
  });

  protected readonly esInmutable = computed(() => this.seguimiento()?.estado === 'PUBLICADO');

  // --- compromisos ------------------------------------------------------------

  protected readonly compromisos = signal<FilaCompromiso[]>([]);

  protected etiquetaEstadoCompromiso(estado: string): string {
    return (ETIQUETAS_ESTADO_COMPROMISO as Record<string, string>)[estado] ?? estado;
  }

  protected readonly modalConvertirAbierto = signal(false);
  protected readonly indiceCompromisoConvertir = signal<number | null>(null);
  protected readonly horasEstimadasConvertir = signal<number | null>(null);
  protected readonly fechaFinConvertir = signal<string | null>(null);
  protected readonly convirtiendo = signal(false);
  protected readonly opcionesResponsables = signal<OpcionSelect[]>([]);

  // --- adjuntos -----------------------------------------------------------------

  protected readonly subiendoAdjunto = signal(false);
  protected readonly progresoAdjunto = signal(0);

  constructor() {
    this.usuariosService
      .listar({ page_size: 200 })
      .subscribe((r) =>
        this.opcionesResponsables.set(
          (r.results as Usuario[]).map((u) => ({
            valor: u.id,
            etiqueta: `${u.nombres} ${u.apellidos}`,
          })),
        ),
      );
    this.proyectosService
      .listarProyectos({ page_size: 200 })
      .subscribe((r) =>
        this.opcionesProyectos.set(
          r.results.map((p) => ({ valor: p.id, etiqueta: `${p.codigo} — ${p.nombre}` })),
        ),
      );

    if (this.idActual) {
      this.cargarExistente(this.idActual);
    } else {
      this.cargando.set(false);
    }
  }

  private cargarExistente(id: string): void {
    this.cargando.set(true);
    this.seguimientosService.obtenerDetalle(id).subscribe({
      next: (seguimiento) => {
        this.seguimiento.set(seguimiento);
        this.proyectoSel.set(seguimiento.proyecto);
        this.periodicidadSel.set(seguimiento.periodicidad);
        this.periodoInicioSel.set(seguimiento.periodo_inicio);
        this.avanceReportado.set(Number(seguimiento.avance_reportado));
        this.semaforoDeclarado.set(seguimiento.semaforo as ValorSemaforo);
        this.justificacionSemaforo.set(seguimiento.justificacion_semaforo);
        this.logros.set(seguimiento.logros);
        this.dificultades.set(seguimiento.dificultades);
        this.riesgos.set(seguimiento.riesgos);
        this.accionesSiguientes.set(seguimiento.acciones_siguientes);
        this.cargando.set(false);
        this.cargarCompromisos(id);
        if (seguimiento.estado === 'BORRADOR') {
          this.precargar(seguimiento.proyecto, seguimiento.periodicidad, seguimiento.periodo_inicio);
        } else {
          // ya publicado: lo calculado que importa es lo que quedó
          // congelado en el propio seguimiento, no un recálculo nuevo.
          this.precarga.set({
            proyecto: seguimiento.proyecto,
            periodicidad: seguimiento.periodicidad,
            periodo_inicio: seguimiento.periodo_inicio,
            periodo_fin: seguimiento.periodo_fin,
            fecha_corte: seguimiento.fecha_corte,
            horas_periodo: seguimiento.horas_periodo,
            costo_periodo: seguimiento.costo_periodo,
            horas_acumuladas: seguimiento.horas_acumuladas,
            costo_acumulado: seguimiento.costo_acumulado,
            semaforo_calculado: seguimiento.semaforo_calculado,
            avance_reportado: seguimiento.avance_reportado,
            tareas_completadas_en_periodo: [],
            tareas_vencidas: [],
            hitos_del_periodo: [],
            tareas_creadas_en_periodo: [],
          });
        }
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el seguimiento.' });
        this.cargando.set(false);
      },
    });
  }

  private cargarCompromisos(seguimientoId: string): void {
    this.compromisosService
      .listar({ seguimiento: seguimientoId, page_size: 200 })
      .subscribe((r) =>
        this.compromisos.set(
          r.results.map((c) => ({
            id: c.id,
            descripcion: c.descripcion,
            responsable: c.responsable,
            fecha_compromiso: c.fecha_compromiso,
            estado: c.estado,
            tarea: c.tarea,
            tarea_codigo: c.tarea_codigo,
            guardando: false,
          })),
        ),
      );
  }

  protected precargar(proyectoId?: string, periodicidad?: string, periodoInicio?: string): void {
    const proyecto = proyectoId ?? this.proyectoSel();
    const periodo = periodicidad ?? this.periodicidadSel();
    const inicio = periodoInicio ?? this.periodoInicioSel();
    if (!proyecto || !periodo || !inicio) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Elija proyecto, periodicidad y fecha de inicio.' });
      return;
    }

    this.precargando.set(true);
    this.seguimientosService.precargar(proyecto, periodo, inicio).subscribe({
      next: (datos) => {
        this.precarga.set(datos);
        this.precargando.set(false);
        if (!this.seguimiento()) {
          this.avanceAnterior.set(datos.avance_reportado);
          this.avanceReportado.set(Number(datos.avance_reportado));
          this.semaforoDeclarado.set(datos.semaforo_calculado as ValorSemaforo);
        } else {
          this.avanceAnterior.set(datos.avance_reportado);
        }
      },
      error: (error: unknown) => {
        this.precargando.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeError(error, 'No se pudo precargar.') });
      },
    });
  }

  protected insertarEnLogros(): void {
    const datos = this.precarga();
    if (!datos) return;
    const lineas: string[] = [];
    if (datos.tareas_completadas_en_periodo.length) {
      lineas.push('Tareas completadas:');
      for (const t of datos.tareas_completadas_en_periodo) lineas.push(`- ${t.codigo}: ${t.nombre}`);
    }
    if (datos.hitos_del_periodo.length) {
      lineas.push('Hitos del periodo:');
      for (const h of datos.hitos_del_periodo) lineas.push(`- ${h.nombre}`);
    }
    if (lineas.length === 0) {
      this.toast.mostrar({ tipo: 'alerta', mensaje: 'No hay nada para insertar todavía.' });
      return;
    }
    const actual = this.logros();
    this.logros.set(actual ? `${actual}\n${lineas.join('\n')}` : lineas.join('\n'));
  }

  private cuerpoActual(): SeguimientoEscritura {
    return {
      proyecto: this.proyectoSel()!,
      periodicidad: this.periodicidadSel(),
      periodo_inicio: this.periodoInicioSel()!,
      avance_reportado: this.avanceReportado() ?? 0,
      semaforo: this.semaforoDeclarado(),
      justificacion_semaforo: this.justificacionSemaforo(),
      logros: this.logros(),
      dificultades: this.dificultades(),
      riesgos: this.riesgos(),
      acciones_siguientes: this.accionesSiguientes(),
    };
  }

  protected guardarBorrador(): void {
    if (!this.proyectoSel() || !this.periodicidadSel() || !this.periodoInicioSel()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete proyecto, periodicidad y periodo.' });
      return;
    }
    this.guardando.set(true);
    const existente = this.seguimiento();
    const peticion = existente
      ? this.seguimientosService.actualizarSeguimiento(existente.id, this.cuerpoActual())
      : this.seguimientosService.crearSeguimiento(this.cuerpoActual());

    peticion.subscribe({
      next: (seguimiento) => {
        this.guardando.set(false);
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Borrador guardado.' });
        if (!existente) {
          void this.router.navigate(['/seguimientos', seguimiento.id]);
        } else {
          this.seguimiento.set(seguimiento);
        }
      },
      error: (error: unknown) => {
        this.guardando.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeError(error, 'No se pudo guardar.') });
      },
    });
  }

  protected async publicar(): Promise<void> {
    const seguimiento = this.seguimiento();
    if (!seguimiento) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Guarde el borrador antes de publicar.' });
      return;
    }
    if (this.necesitaJustificacion() && !this.justificacionSemaforo().trim()) {
      this.toast.mostrar({
        tipo: 'error',
        mensaje: 'El semáforo declarado difiere del calculado: explique por qué.',
      });
      return;
    }

    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Publicar seguimiento',
      mensaje:
        'El seguimiento quedará inmutable y actualizará el avance y el semáforo del proyecto. ¿Continuar?',
    });
    if (!confirmado) return;

    this.publicando.set(true);
    this.guardarBorradorYLuego(() => {
      this.seguimientosService.publicar(seguimiento.id).subscribe({
        next: (actualizado) => {
          this.publicando.set(false);
          this.seguimiento.set(actualizado);
          this.toast.mostrar({ tipo: 'exito', mensaje: 'Seguimiento publicado.' });
        },
        error: (error: unknown) => {
          this.publicando.set(false);
          this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeError(error, 'No se pudo publicar.') });
        },
      });
    });
  }

  private guardarBorradorYLuego(continuar: () => void): void {
    const seguimiento = this.seguimiento();
    if (!seguimiento) return;
    this.seguimientosService.actualizarSeguimiento(seguimiento.id, this.cuerpoActual()).subscribe({
      next: (actualizado) => {
        this.seguimiento.set(actualizado);
        continuar();
      },
      error: (error: unknown) => {
        this.publicando.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeError(error, 'No se pudo guardar.') });
      },
    });
  }

  // --- compromisos --------------------------------------------------------------

  protected agregarCompromiso(): void {
    this.compromisos.update((filas) => [
      ...filas,
      {
        id: null,
        descripcion: '',
        responsable: null,
        fecha_compromiso: null,
        estado: 'ABIERTO',
        tarea: null,
        tarea_codigo: null,
        guardando: false,
      },
    ]);
  }

  protected actualizarCompromiso(indice: number, cambios: Partial<FilaCompromiso>): void {
    this.compromisos.update((filas) =>
      filas.map((fila, i) => (i === indice ? { ...fila, ...cambios } : fila)),
    );
  }

  protected guardarCompromiso(indice: number): void {
    const seguimiento = this.seguimiento();
    const fila = this.compromisos()[indice];
    if (!seguimiento || !fila.descripcion || !fila.responsable || !fila.fecha_compromiso) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete descripción, responsable y fecha.' });
      return;
    }
    this.actualizarCompromiso(indice, { guardando: true });
    const cuerpo = {
      seguimiento: seguimiento.id,
      descripcion: fila.descripcion,
      responsable: fila.responsable,
      fecha_compromiso: fila.fecha_compromiso,
    };
    const peticion = fila.id
      ? this.compromisosService.actualizar(fila.id, cuerpo)
      : this.compromisosService.crear(cuerpo);
    peticion.subscribe({
      next: (creado) => {
        this.actualizarCompromiso(indice, { id: creado.id, guardando: false });
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Compromiso guardado.' });
      },
      error: () => {
        this.actualizarCompromiso(indice, { guardando: false });
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo guardar el compromiso.' });
      },
    });
  }

  protected eliminarCompromiso(indice: number): void {
    const fila = this.compromisos()[indice];
    if (!fila.id) {
      this.compromisos.update((filas) => filas.filter((_, i) => i !== indice));
      return;
    }
    this.compromisosService.eliminar(fila.id).subscribe(() => {
      this.compromisos.update((filas) => filas.filter((_, i) => i !== indice));
    });
  }

  protected abrirConversion(indice: number): void {
    const fila = this.compromisos()[indice];
    this.indiceCompromisoConvertir.set(indice);
    this.horasEstimadasConvertir.set(null);
    this.fechaFinConvertir.set(fila.fecha_compromiso);
    this.modalConvertirAbierto.set(true);
  }

  protected cerrarConversion(): void {
    this.modalConvertirAbierto.set(false);
  }

  protected confirmarConversion(): void {
    const indice = this.indiceCompromisoConvertir();
    const horas = this.horasEstimadasConvertir();
    if (indice === null) return;
    const fila = this.compromisos()[indice];
    if (!fila.id || !horas || horas <= 0) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Indique las horas estimadas (mayor que cero).' });
      return;
    }

    this.convirtiendo.set(true);
    this.compromisosService
      .convertirEnTarea(fila.id, {
        horas_estimadas: horas,
        fecha_fin_plan: this.fechaFinConvertir() ?? undefined,
      })
      .subscribe({
        next: (actualizado) => {
          this.convirtiendo.set(false);
          this.modalConvertirAbierto.set(false);
          this.actualizarCompromiso(indice, {
            estado: actualizado.estado,
            tarea: actualizado.tarea,
            tarea_codigo: actualizado.tarea_codigo,
          });
          this.toast.mostrar({
            tipo: 'exito',
            mensaje: `Tarea ${actualizado.tarea_codigo} creada en el cronograma del proyecto.`,
          });
        },
        error: (error: unknown) => {
          this.convirtiendo.set(false);
          this.toast.mostrar({
            tipo: 'error',
            mensaje: this.mensajeError(error, 'No se pudo convertir el compromiso.'),
          });
        },
      });
  }

  // --- adjuntos ----------------------------------------------------------------

  protected alSeleccionarAdjunto(evento: Event): void {
    const input = evento.target as HTMLInputElement;
    const archivo = input.files?.[0];
    const seguimiento = this.seguimiento();
    if (!archivo || !seguimiento) return;

    this.subiendoAdjunto.set(true);
    this.progresoAdjunto.set(0);
    this.documentosService
      .subir(
        {
          proyecto: seguimiento.proyecto,
          seguimiento: seguimiento.id,
          categoria: 'SOPORTE',
          nombre: archivo.name,
        },
        archivo,
      )
      .subscribe({
        next: (evento) => {
          if (evento.type === 1 && evento.total) {
            this.progresoAdjunto.set(Math.round((evento.loaded / evento.total) * 100));
          } else if (evento.type === 4) {
            this.subiendoAdjunto.set(false);
            this.toast.mostrar({ tipo: 'exito', mensaje: 'Adjunto cargado.' });
          }
        },
        error: () => {
          this.subiendoAdjunto.set(false);
          this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el adjunto.' });
        },
      });
    input.value = '';
  }

  protected esValorSemaforo(valor: string): ValorSemaforo {
    return valor as ValorSemaforo;
  }

  private mensajeError(error: unknown, porDefecto: string): string {
    if (error instanceof HttpErrorResponse) {
      const cuerpo = error.error as Partial<ErrorApi> | null;
      return cuerpo?.error?.mensaje ?? porDefecto;
    }
    return porDefecto;
  }
}
