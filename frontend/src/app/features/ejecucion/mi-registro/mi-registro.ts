import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { ErrorApi, RegistroEjecucion } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { Boton } from '../../../shared/ui/boton/boton';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { AsignacionesService } from '../../recursos/data/asignaciones.service';
import { RecursosService } from '../../recursos/data/recursos.service';
import { TareasService } from '../../tareas/data/tareas.service';
import { ProyectosService } from '../../proyectos/data/proyectos.service';
import { RegistroEjecucionEscritura, RegistrosEjecucionService } from '../data/registros.service';

type Periodicidad = 'DIARIA' | 'SEMANAL' | 'MENSUAL';

interface FilaCaptura {
  clave: string;
  proyecto: string;
  proyectoCodigo: string;
  tarea: string | null;
  tareaCodigo: string | null;
  nombre: string;
}

interface CeldaCaptura {
  valor: number | null;
  valorOriginal: number | null;
  registroId: string | null;
  estado: string | null;
  motivoRechazo: string | null;
  guardando: boolean;
}

const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

function aIso(fecha: Date): string {
  return fecha.toISOString().slice(0, 10);
}

function inicioDeSemana(fecha: Date): Date {
  const copia = new Date(fecha);
  const dia = copia.getDay();
  const desplazamiento = dia === 0 ? 6 : dia - 1;
  copia.setDate(copia.getDate() - desplazamiento);
  copia.setHours(0, 0, 0, 0);
  return copia;
}

@Component({
  selector: 'app-mi-registro',
  templateUrl: './mi-registro.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Select],
})
export class MiRegistro {
  private readonly auth = inject(AuthService);
  private readonly recursosService = inject(RecursosService);
  private readonly asignacionesService = inject(AsignacionesService);
  private readonly tareasService = inject(TareasService);
  private readonly proyectosService = inject(ProyectosService);
  private readonly registrosService = inject(RegistrosEjecucionService);
  private readonly toast = inject(ToastService);

  protected readonly cargando = signal(true);
  protected readonly guardandoTodo = signal(false);
  protected readonly enviando = signal(false);

  protected readonly miRecursoId = signal<string | null>(null);
  protected readonly periodicidad = signal<Periodicidad>('DIARIA');
  protected readonly fechaReferencia = signal<Date>(new Date());

  protected readonly filas = signal<FilaCaptura[]>([]);
  protected readonly celdas = signal<Record<string, CeldaCaptura>>({});
  protected readonly filasGuardando = signal<Set<string>>(new Set());

  protected readonly opcionesPeriodicidad: OpcionSelect[] = [
    { valor: 'DIARIA', etiqueta: 'Diaria' },
    { valor: 'SEMANAL', etiqueta: 'Semanal' },
    { valor: 'MENSUAL', etiqueta: 'Mensual' },
  ];

  protected readonly dias = computed<Date[]>(() => {
    if (this.periodicidad() === 'MENSUAL') {
      const ref = this.fechaReferencia();
      return [new Date(ref.getFullYear(), ref.getMonth(), 1)];
    }
    const inicio = inicioDeSemana(this.fechaReferencia());
    return Array.from({ length: 7 }, (_, i) => {
      const dia = new Date(inicio);
      dia.setDate(dia.getDate() + i);
      return dia;
    });
  });

  protected readonly rangoTexto = computed(() => {
    if (this.periodicidad() === 'MENSUAL') {
      const ref = this.fechaReferencia();
      return `${MESES[ref.getMonth()]} de ${ref.getFullYear()}`;
    }
    const dias = this.dias();
    const primero = dias[0];
    const ultimo = dias[dias.length - 1];
    const fmt = (f: Date) => `${f.getDate()} de ${MESES[f.getMonth()].toLowerCase()}`;
    return `Semana del ${fmt(primero)} al ${fmt(ultimo)} de ${ultimo.getFullYear()}`;
  });

  constructor() {
    this.cargarRecursoYFilas();
  }

  protected etiquetaDia(fecha: Date): string {
    if (this.periodicidad() === 'MENSUAL') return 'Mes';
    return `${DIAS_SEMANA[fecha.getDay() === 0 ? 6 : fecha.getDay() - 1]} ${fecha.getDate()}`;
  }

  private claveCelda(filaClave: string, fecha: Date): string {
    return `${filaClave}__${aIso(fecha)}`;
  }

  protected celda(filaClave: string, fecha: Date): CeldaCaptura {
    const clave = this.claveCelda(filaClave, fecha);
    return (
      this.celdas()[clave] ?? {
        valor: null,
        valorOriginal: null,
        registroId: null,
        estado: null,
        motivoRechazo: null,
        guardando: false,
      }
    );
  }

  protected alCambiarValor(filaClave: string, fecha: Date, valor: number | null): void {
    const clave = this.claveCelda(filaClave, fecha);
    const actual = this.celda(filaClave, fecha);
    this.celdas.update((mapa) => ({ ...mapa, [clave]: { ...actual, valor } }));
  }

  protected estaBloqueada(celda: CeldaCaptura): boolean {
    return celda.estado === 'APROBADO' || celda.estado === 'ENVIADO';
  }

  protected totalFila(fila: FilaCaptura): number {
    return this.dias().reduce((total, dia) => total + (this.celda(fila.clave, dia).valor ?? 0), 0);
  }

  protected totalColumna(fecha: Date): number {
    return this.filas().reduce(
      (total, fila) => total + (this.celda(fila.clave, fecha).valor ?? 0),
      0,
    );
  }

  protected totalGeneral(): number {
    return this.filas().reduce((total, fila) => total + this.totalFila(fila), 0);
  }

  private cargarRecursoYFilas(): void {
    const miId = this.auth.usuario()?.id;
    if (!miId) {
      this.cargando.set(false);
      return;
    }

    this.recursosService.listarRecursos({ usuario: miId }).subscribe({
      next: (respuesta) => {
        const miRecurso = respuesta.results[0];
        if (!miRecurso) {
          this.toast.mostrar({
            tipo: 'error',
            mensaje: 'Su usuario no tiene un recurso asociado; no puede registrar horas.',
          });
          this.cargando.set(false);
          return;
        }
        this.miRecursoId.set(miRecurso.id);
        this.cargarFilas(miRecurso.id);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo identificar su recurso.' });
        this.cargando.set(false);
      },
    });
  }

  private cargarFilas(recursoId: string): void {
    this.proyectosService.listarProyectos({ page_size: 200 }).subscribe((respuestaProyectos) => {
      const codigoPorProyecto = new Map(respuestaProyectos.results.map((p) => [p.id, p.codigo]));

      this.asignacionesService.listar({ recurso: recursoId }).subscribe((respuestaAsig) => {
        this.tareasService.listarTareas({ responsable: recursoId, page_size: 200 }).subscribe({
          next: (respuestaTareas) => {
            const filas: FilaCaptura[] = [];
            for (const asignacion of respuestaAsig.results) {
              filas.push({
                clave: `proy-${asignacion.proyecto}`,
                proyecto: asignacion.proyecto,
                proyectoCodigo: codigoPorProyecto.get(asignacion.proyecto) ?? '',
                tarea: null,
                tareaCodigo: null,
                nombre: '(sin tarea específica)',
              });
            }
            for (const tarea of respuestaTareas.results) {
              filas.push({
                clave: `tarea-${tarea.id}`,
                proyecto: tarea.proyecto,
                proyectoCodigo: tarea.proyecto_codigo,
                tarea: tarea.id,
                tareaCodigo: tarea.codigo,
                nombre: tarea.nombre,
              });
            }
            this.filas.set(filas);
            this.cargarRegistrosDeLaVentana();
          },
          error: () => {
            this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudieron cargar sus tareas.' });
            this.cargando.set(false);
          },
        });
      });
    });
  }

  protected cargarRegistrosDeLaVentana(): void {
    const recursoId = this.miRecursoId();
    if (!recursoId) return;
    this.cargando.set(true);
    const dias = this.dias();
    const desde = aIso(dias[0]);
    const hasta = aIso(dias[dias.length - 1]);

    this.registrosService
      .listar({ recurso: recursoId, periodo_inicio__gte: desde, periodo_fin__lte: hasta, page_size: 200 })
      .subscribe({
        next: (respuesta) => {
          this.poblarCeldas(respuesta.results);
          this.cargando.set(false);
        },
        error: () => {
          this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudieron cargar sus registros.' });
          this.cargando.set(false);
        },
      });
  }

  private poblarCeldas(registros: RegistroEjecucion[]): void {
    const nuevo: Record<string, CeldaCaptura> = {};
    for (const fila of this.filas()) {
      for (const dia of this.dias()) {
        const registro = registros.find(
          (r) =>
            r.recurso === this.miRecursoId() &&
            r.proyecto === fila.proyecto &&
            r.tarea === fila.tarea &&
            r.periodo_inicio <= aIso(dia) &&
            r.periodo_fin >= aIso(dia),
        );
        const clave = this.claveCelda(fila.clave, dia);
        if (registro) {
          // Un registro SEMANAL/MENSUAL ocupa varios días: se muestra
          // completo solo en el primer día de su periodo para no repetir
          // el valor en cada columna.
          const esPrimerDia = registro.periodo_inicio === aIso(dia);
          nuevo[clave] = {
            valor: esPrimerDia ? Number(registro.horas) : null,
            valorOriginal: esPrimerDia ? Number(registro.horas) : null,
            registroId: esPrimerDia ? registro.id : null,
            estado: esPrimerDia ? registro.estado_aprobacion : 'OCUPADO',
            motivoRechazo: registro.motivo_rechazo || null,
            guardando: false,
          };
        }
      }
    }
    this.celdas.set(nuevo);
  }

  protected navegar(direccion: -1 | 0 | 1): void {
    if (direccion === 0) {
      this.fechaReferencia.set(new Date());
    } else if (this.periodicidad() === 'MENSUAL') {
      const ref = this.fechaReferencia();
      this.fechaReferencia.set(new Date(ref.getFullYear(), ref.getMonth() + direccion, 1));
    } else {
      const ref = new Date(this.fechaReferencia());
      ref.setDate(ref.getDate() + direccion * 7);
      this.fechaReferencia.set(ref);
    }
    this.cargarRegistrosDeLaVentana();
  }

  protected alCambiarPeriodicidad(valor: string | null): void {
    this.periodicidad.set((valor as Periodicidad) ?? 'DIARIA');
    this.cargarRegistrosDeLaVentana();
  }

  /** Guarda la fila: en DIARIA, un registro por día con valor; en SEMANAL,
   * uno solo con la suma de la semana (periodo_inicio = lunes); en MENSUAL,
   * uno solo con el valor de la única celda. */
  protected guardarFila(fila: FilaCaptura): void {
    const recursoId = this.miRecursoId();
    if (!recursoId) return;

    this.filasGuardando.update((set) => new Set(set).add(fila.clave));
    const peticiones: { clave: string; obs: ReturnType<RegistrosEjecucionService['crear']> }[] = [];

    if (this.periodicidad() === 'DIARIA') {
      for (const dia of this.dias()) {
        const celda = this.celda(fila.clave, dia);
        if (celda.valor === celda.valorOriginal || celda.valor === null) continue;
        if (this.estaBloqueada(celda)) continue;
        const cuerpo: RegistroEjecucionEscritura = {
          proyecto: fila.proyecto,
          tarea: fila.tarea,
          recurso: recursoId,
          periodicidad: 'DIARIA',
          periodo_inicio: aIso(dia),
          horas: celda.valor,
          descripcion: '',
        };
        const clave = this.claveCelda(fila.clave, dia);
        const obs = celda.registroId
          ? (this.registrosService.actualizar(celda.registroId, cuerpo) as ReturnType<
              RegistrosEjecucionService['crear']
            >)
          : this.registrosService.crear(cuerpo);
        peticiones.push({ clave, obs });
      }
    } else {
      const dias = this.dias();
      const primera = dias[0];
      const celdaPrincipal = this.celda(fila.clave, primera);
      const total = this.totalFila(fila);
      if (total > 0 && total !== celdaPrincipal.valorOriginal && !this.estaBloqueada(celdaPrincipal)) {
        const cuerpo: RegistroEjecucionEscritura = {
          proyecto: fila.proyecto,
          tarea: fila.tarea,
          recurso: recursoId,
          periodicidad: this.periodicidad(),
          periodo_inicio: aIso(primera),
          horas: total,
          descripcion: '',
        };
        const clave = this.claveCelda(fila.clave, primera);
        const obs = celdaPrincipal.registroId
          ? (this.registrosService.actualizar(celdaPrincipal.registroId, cuerpo) as ReturnType<
              RegistrosEjecucionService['crear']
            >)
          : this.registrosService.crear(cuerpo);
        peticiones.push({ clave, obs });
      }
    }

    if (peticiones.length === 0) {
      this.filasGuardando.update((set) => {
        const copia = new Set(set);
        copia.delete(fila.clave);
        return copia;
      });
      return;
    }

    let pendientes = peticiones.length;
    const advertencias: string[] = [];
    for (const { clave, obs } of peticiones) {
      obs.subscribe({
        next: (respuesta) => {
          this.celdas.update((mapa) => ({
            ...mapa,
            [clave]: {
              valor: Number(respuesta.horas),
              valorOriginal: Number(respuesta.horas),
              registroId: respuesta.id,
              estado: respuesta.estado_aprobacion,
              motivoRechazo: respuesta.motivo_rechazo || null,
              guardando: false,
            },
          }));
          advertencias.push(...respuesta.advertencias);
          pendientes -= 1;
          if (pendientes === 0) this.alTerminarGuardadoFila(fila.clave, advertencias);
        },
        error: (error: unknown) => {
          pendientes -= 1;
          this.toast.mostrar({ tipo: 'error', mensaje: this.mensajeError(error) });
          if (pendientes === 0) this.alTerminarGuardadoFila(fila.clave, advertencias);
        },
      });
    }
  }

  private alTerminarGuardadoFila(filaClave: string, advertencias: string[]): void {
    this.filasGuardando.update((set) => {
      const copia = new Set(set);
      copia.delete(filaClave);
      return copia;
    });
    for (const advertencia of advertencias) {
      this.toast.mostrar({ tipo: 'alerta', mensaje: advertencia });
    }
    this.toast.mostrar({ tipo: 'exito', mensaje: 'Fila guardada.' });
  }

  protected filaGuardando(clave: string): boolean {
    return this.filasGuardando().has(clave);
  }

  /** "Guardar todo": agrupa las celdas nuevas (sin `registroId`) de todas
   * las filas en un solo `POST /registros-ejecucion/lote/`; las que ya
   * existían y cambiaron se actualizan aparte con `PATCH`, porque el lote
   * es solo para altas (docs/api-contrato.md §6). */
  protected guardarTodo(): void {
    const recursoId = this.miRecursoId();
    if (!recursoId) return;

    const nuevos: RegistroEjecucionEscritura[] = [];
    const actualizaciones: { id: string; cuerpo: RegistroEjecucionEscritura }[] = [];

    for (const fila of this.filas()) {
      if (this.periodicidad() === 'DIARIA') {
        for (const dia of this.dias()) {
          const celda = this.celda(fila.clave, dia);
          if (celda.valor === null || celda.valor === celda.valorOriginal) continue;
          if (this.estaBloqueada(celda)) continue;
          const cuerpo: RegistroEjecucionEscritura = {
            proyecto: fila.proyecto,
            tarea: fila.tarea,
            recurso: recursoId,
            periodicidad: 'DIARIA',
            periodo_inicio: aIso(dia),
            horas: celda.valor,
            descripcion: '',
          };
          if (celda.registroId) {
            actualizaciones.push({ id: celda.registroId, cuerpo });
          } else {
            nuevos.push(cuerpo);
          }
        }
      } else {
        const primera = this.dias()[0];
        const celdaPrincipal = this.celda(fila.clave, primera);
        const total = this.totalFila(fila);
        if (total <= 0 || total === celdaPrincipal.valorOriginal || this.estaBloqueada(celdaPrincipal)) {
          continue;
        }
        const cuerpo: RegistroEjecucionEscritura = {
          proyecto: fila.proyecto,
          tarea: fila.tarea,
          recurso: recursoId,
          periodicidad: this.periodicidad(),
          periodo_inicio: aIso(primera),
          horas: total,
          descripcion: '',
        };
        if (celdaPrincipal.registroId) {
          actualizaciones.push({ id: celdaPrincipal.registroId, cuerpo });
        } else {
          nuevos.push(cuerpo);
        }
      }
    }

    if (nuevos.length === 0 && actualizaciones.length === 0) {
      this.toast.mostrar({ tipo: 'alerta', mensaje: 'No hay cambios para guardar.' });
      return;
    }

    this.guardandoTodo.set(true);
    let pendientes = actualizaciones.length + (nuevos.length > 0 ? 1 : 0);
    const terminar = () => {
      pendientes -= 1;
      if (pendientes <= 0) {
        this.guardandoTodo.set(false);
        this.cargarRegistrosDeLaVentana();
      }
    };

    if (nuevos.length > 0) {
      this.registrosService.lote(nuevos).subscribe({
        next: (respuesta) => {
          this.toast.mostrar({
            tipo: respuesta.errores.length > 0 ? 'alerta' : 'exito',
            mensaje: `${respuesta.creados} registros creados, ${respuesta.errores.length} con error.`,
          });
          terminar();
        },
        error: () => {
          this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo guardar el lote.' });
          terminar();
        },
      });
    }
    for (const { id, cuerpo } of actualizaciones) {
      this.registrosService.actualizar(id, cuerpo).subscribe({
        next: terminar,
        error: () => {
          this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo actualizar un registro.' });
          terminar();
        },
      });
    }
  }

  /** Envía a aprobación todo lo que esté en `BORRADOR` dentro de la
   * ventana visible actualmente. */
  protected enviarAAprobacion(): void {
    const idsBorrador = Object.values(this.celdas())
      .filter((c) => c.estado === 'BORRADOR' && c.registroId)
      .map((c) => c.registroId as string);

    if (idsBorrador.length === 0) {
      this.toast.mostrar({ tipo: 'alerta', mensaje: 'No hay registros en borrador para enviar.' });
      return;
    }

    this.enviando.set(true);
    let pendientes = idsBorrador.length;
    let errores = 0;
    for (const id of idsBorrador) {
      this.registrosService.enviar(id).subscribe({
        next: () => {
          pendientes -= 1;
          if (pendientes === 0) this.alTerminarEnvio(errores);
        },
        error: () => {
          errores += 1;
          pendientes -= 1;
          if (pendientes === 0) this.alTerminarEnvio(errores);
        },
      });
    }
  }

  private alTerminarEnvio(errores: number): void {
    this.enviando.set(false);
    this.toast.mostrar({
      tipo: errores > 0 ? 'alerta' : 'exito',
      mensaje: errores > 0 ? `Enviados con ${errores} error(es).` : 'Enviado a aprobación.',
    });
    this.cargarRegistrosDeLaVentana();
  }

  private mensajeError(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const cuerpo = error.error as Partial<ErrorApi> | null;
      return cuerpo?.error?.mensaje ?? 'No se pudo guardar.';
    }
    return 'No se pudo guardar.';
  }
}
