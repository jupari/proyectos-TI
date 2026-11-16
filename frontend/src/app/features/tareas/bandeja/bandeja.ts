import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import {
  ETIQUETAS_ESTADO_TAREA,
  ETIQUETAS_PRIORIDAD,
  ETIQUETAS_TIPO_TAREA,
  RespuestaPaginada,
} from '../../../core/models';
import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { ToastService } from '../../../core/ui/toast.service';
import { FechaCortaPipe, HorasPipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Modal } from '../../../shared/ui/modal/modal';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Switch } from '../../../shared/ui/switch/switch';
import { CambioOrden, ColumnaTabla, Tabla } from '../../../shared/ui/tabla/tabla';
import { Textarea } from '../../../shared/ui/textarea/textarea';
import { ProyectosService } from '../../proyectos/data/proyectos.service';
import { FiltrosTarea, TareaLista } from '../data/tareas.model';
import { TareasService } from '../data/tareas.service';
import { sincronizarQueryParams } from '../../../core/ui/query-params';

@Component({
  selector: 'app-bandeja-tareas',
  templateUrl: './bandeja.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Tabla,
    Boton,
    Badge,
    Progreso,
    Select,
    Switch,
    Modal,
    Textarea,
    FechaCortaPipe,
    HorasPipe,
  ],
})
export class BandejaTareas {
  private readonly tareasService = inject(TareasService);
  private readonly proyectosService = inject(ProyectosService);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly ETIQUETAS_ESTADO_TAREA = ETIQUETAS_ESTADO_TAREA;

  protected readonly cargando = signal(false);
  protected readonly respuesta = signal<RespuestaPaginada<TareaLista> | null>(null);
  protected readonly paginaActual = signal(1);
  protected readonly ordenActual = signal<CambioOrden | null>(null);

  protected readonly proyecto = signal<string | null>(null);
  protected readonly estado = signal<string | null>(null);
  protected readonly tipo = signal<string | null>(null);
  protected readonly prioridad = signal<string | null>(null);
  protected readonly soloMisTareas = signal(false);
  protected readonly soloVencidas = signal(false);
  protected readonly soloCreadasDuranteEjecucion = signal(false);

  protected readonly opcionesProyectos = signal<OpcionSelect[]>([]);

  protected readonly opcionesEstado: OpcionSelect[] = Object.entries(ETIQUETAS_ESTADO_TAREA).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );
  protected readonly opcionesTipo: OpcionSelect[] = Object.entries(ETIQUETAS_TIPO_TAREA).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );
  protected readonly opcionesPrioridad: OpcionSelect[] = Object.entries(ETIQUETAS_PRIORIDAD).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );

  protected readonly dialogoBloqueoAbierto = signal(false);
  protected readonly tareaEnBloqueo = signal<TareaLista | null>(null);
  protected readonly notaBloqueo = signal('');

  protected readonly columnaCodigo: ColumnaTabla<TareaLista> = {
    clave: 'codigo',
    titulo: 'Código',
    ordenable: true,
    ancho: '110px',
  };

  constructor() {
    const parametros = this.ruta.snapshot.queryParamMap;
    this.proyecto.set(parametros.get('proyecto'));
    this.estado.set(parametros.get('estado'));
    this.tipo.set(parametros.get('tipo'));
    this.prioridad.set(parametros.get('prioridad'));
    this.soloMisTareas.set(parametros.get('mis_tareas') === 'true');
    this.soloVencidas.set(parametros.get('vencidas') === 'true');
    this.soloCreadasDuranteEjecucion.set(parametros.get('creada_durante_ejecucion') === 'true');
    const pagina = Number(parametros.get('page') ?? '1');
    this.paginaActual.set(Number.isFinite(pagina) && pagina > 0 ? pagina : 1);

    this.proyectosService
      .listarProyectos({ page_size: 200 })
      .subscribe((r) =>
        this.opcionesProyectos.set(
          r.results.map((p) => ({ valor: p.id, etiqueta: `${p.codigo} — ${p.nombre}` })),
        ),
      );
    this.cargar();
  }

  private filtrosActuales(): FiltrosTarea {
    const orden = this.ordenActual();
    return {
      proyecto: this.proyecto() ?? undefined,
      estado: this.estado() ?? undefined,
      tipo: this.tipo() ?? undefined,
      prioridad: this.prioridad() ?? undefined,
      mis_tareas: this.soloMisTareas() || undefined,
      vencidas: this.soloVencidas() || undefined,
      creada_durante_ejecucion: this.soloCreadasDuranteEjecucion() || undefined,
      ordering: orden ? `${orden.direccion === 'desc' ? '-' : ''}${orden.clave}` : undefined,
      page: this.paginaActual() > 1 ? this.paginaActual() : undefined,
    };
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.sincronizarUrl();
    this.tareasService.listarTareas(this.filtrosActuales()).subscribe({
      next: (respuesta) => {
        this.respuesta.set(respuesta);
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la lista de tareas.' });
        this.cargando.set(false);
      },
    });
  }

  private sincronizarUrl(): void {
    const filtros = this.filtrosActuales();
    const queryParams: Record<string, string> = {};
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== undefined && valor !== '') {
        queryParams[clave] = String(valor);
      }
    }
    sincronizarQueryParams(this.router, this.ruta, queryParams);
  }

  protected aplicarFiltros(): void {
    this.paginaActual.set(1);
    this.cargar();
  }

  protected alCambiarOrden(orden: CambioOrden): void {
    this.ordenActual.set(orden);
    this.cargar();
  }

  protected alCambiarPagina(pagina: number): void {
    this.paginaActual.set(pagina);
    this.cargar();
  }

  protected limpiarFiltros(): void {
    this.proyecto.set(null);
    this.estado.set(null);
    this.tipo.set(null);
    this.prioridad.set(null);
    this.soloMisTareas.set(false);
    this.soloVencidas.set(false);
    this.soloCreadasDuranteEjecucion.set(false);
    this.aplicarFiltros();
  }

  protected async alCambiarEstadoRapido(tarea: TareaLista, estadoNuevo: string): Promise<void> {
    if (estadoNuevo === tarea.estado) return;

    if (estadoNuevo === 'BLOQUEADA') {
      this.tareaEnBloqueo.set(tarea);
      this.notaBloqueo.set('');
      this.dialogoBloqueoAbierto.set(true);
      return;
    }

    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Cambiar estado',
      mensaje: `¿Cambiar "${tarea.nombre}" a ${ETIQUETAS_ESTADO_TAREA[estadoNuevo as keyof typeof ETIQUETAS_ESTADO_TAREA]}?`,
    });
    if (!confirmado) return;

    this.aplicarCambioEstado(tarea, { estado: estadoNuevo });
  }

  protected confirmarBloqueo(): void {
    const tarea = this.tareaEnBloqueo();
    if (!tarea || !this.notaBloqueo().trim()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Escriba el motivo del bloqueo.' });
      return;
    }
    this.aplicarCambioEstado(tarea, { estado: 'BLOQUEADA', nota: this.notaBloqueo().trim() });
    this.dialogoBloqueoAbierto.set(false);
  }

  protected cerrarDialogoBloqueo(): void {
    this.dialogoBloqueoAbierto.set(false);
  }

  private aplicarCambioEstado(
    tarea: TareaLista,
    datos: { estado: string; nota?: string },
  ): void {
    this.tareasService.cambiarEstado(tarea.id, datos).subscribe({
      next: () => {
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Estado actualizado.' });
        this.cargar();
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cambiar el estado.' });
      },
    });
  }
}
