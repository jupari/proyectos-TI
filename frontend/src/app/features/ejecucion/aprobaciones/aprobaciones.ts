import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { RegistroEjecucion, RespuestaPaginada } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { FechaCortaPipe, HorasPipe, MonedaPipe } from '../../../shared/pipes';
import { Boton } from '../../../shared/ui/boton/boton';
import { Modal } from '../../../shared/ui/modal/modal';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { CambioOrden, ColumnaTabla, Tabla } from '../../../shared/ui/tabla/tabla';
import { Textarea } from '../../../shared/ui/textarea/textarea';
import { ProyectosService } from '../../proyectos/data/proyectos.service';
import { RecursosService } from '../../recursos/data/recursos.service';
import { FiltrosRegistroEjecucion } from '../data/registros.service';
import { RegistrosEjecucionService } from '../data/registros.service';

@Component({
  selector: 'app-aprobaciones',
  templateUrl: './aprobaciones.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Tabla, Boton, Modal, Select, Textarea, FechaCortaPipe, HorasPipe, MonedaPipe],
})
export class Aprobaciones {
  private readonly registrosService = inject(RegistrosEjecucionService);
  private readonly proyectosService = inject(ProyectosService);
  private readonly recursosService = inject(RecursosService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly cargando = signal(false);
  protected readonly respuesta = signal<RespuestaPaginada<RegistroEjecucion> | null>(null);
  protected readonly paginaActual = signal(1);
  protected readonly ordenActual = signal<CambioOrden | null>(null);
  protected readonly seleccion = signal<string[]>([]);

  protected readonly proyecto = signal<string | null>(null);
  protected readonly recurso = signal<string | null>(null);
  protected readonly periodoDesde = signal<string | null>(null);
  protected readonly periodoHasta = signal<string | null>(null);

  protected readonly opcionesProyectos = signal<OpcionSelect[]>([]);
  protected readonly opcionesRecursos = signal<OpcionSelect[]>([]);

  protected readonly procesando = signal(false);
  protected readonly dialogoRechazoAbierto = signal(false);
  protected readonly motivoRechazo = signal('');

  protected readonly columnas: ColumnaTabla<RegistroEjecucion>[] = [
    { clave: 'proyecto_codigo', titulo: 'Proyecto' },
    { clave: 'recurso_nombre', titulo: 'Recurso' },
    { clave: 'periodicidad', titulo: 'Periodicidad' },
    { clave: 'periodo_inicio', titulo: 'Periodo' },
    { clave: 'horas', titulo: 'Horas', alinear: 'derecha' },
    { clave: 'costo', titulo: 'Costo', alinear: 'derecha' },
    { clave: 'descripcion', titulo: 'Descripción' },
  ];

  constructor() {
    const parametros = this.ruta.snapshot.queryParamMap;
    this.proyecto.set(parametros.get('proyecto'));
    this.recurso.set(parametros.get('recurso'));
    this.periodoDesde.set(parametros.get('periodo_inicio__gte'));
    this.periodoHasta.set(parametros.get('periodo_fin__lte'));

    this.proyectosService
      .listarProyectos({ page_size: 200 })
      .subscribe((r) =>
        this.opcionesProyectos.set(r.results.map((p) => ({ valor: p.id, etiqueta: `${p.codigo} — ${p.nombre}` }))),
      );
    this.recursosService
      .listarRecursos({ page_size: 200 })
      .subscribe((r) => this.opcionesRecursos.set(r.results.map((x) => ({ valor: x.id, etiqueta: x.nombre }))));

    this.cargar();
  }

  private filtrosActuales(): FiltrosRegistroEjecucion {
    const orden = this.ordenActual();
    return {
      estado_aprobacion: 'ENVIADO',
      proyecto: this.proyecto() ?? undefined,
      recurso: this.recurso() ?? undefined,
      periodo_inicio__gte: this.periodoDesde() ?? undefined,
      periodo_fin__lte: this.periodoHasta() ?? undefined,
      ordering: orden ? `${orden.direccion === 'desc' ? '-' : ''}${orden.clave}` : undefined,
      page: this.paginaActual() > 1 ? this.paginaActual() : undefined,
    };
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.sincronizarUrl();
    this.registrosService.listar(this.filtrosActuales()).subscribe({
      next: (respuesta) => {
        this.respuesta.set(respuesta);
        this.seleccion.set([]);
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la lista de aprobaciones.' });
        this.cargando.set(false);
      },
    });
  }

  private sincronizarUrl(): void {
    const filtros = this.filtrosActuales();
    const queryParams: Record<string, string> = {};
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== undefined && valor !== '' && clave !== 'estado_aprobacion') {
        queryParams[clave] = String(valor);
      }
    }
    void this.router.navigate([], { relativeTo: this.ruta, queryParams });
  }

  protected aplicarFiltros(): void {
    this.paginaActual.set(1);
    this.cargar();
  }

  protected limpiarFiltros(): void {
    this.proyecto.set(null);
    this.recurso.set(null);
    this.periodoDesde.set(null);
    this.periodoHasta.set(null);
    this.aplicarFiltros();
  }

  protected alCambiarOrden(orden: CambioOrden): void {
    this.ordenActual.set(orden);
    this.cargar();
  }

  protected alCambiarPagina(pagina: number): void {
    this.paginaActual.set(pagina);
    this.cargar();
  }

  protected alCambiarSeleccion(seleccion: string[]): void {
    this.seleccion.set(seleccion);
  }

  protected aprobarSeleccionados(): void {
    const ids = this.seleccion();
    if (ids.length === 0) return;
    this.procesando.set(true);
    let pendientes = ids.length;
    let errores = 0;
    for (const id of ids) {
      this.registrosService.aprobar(id).subscribe({
        next: () => {
          pendientes -= 1;
          if (pendientes === 0) this.alTerminarLote(errores);
        },
        error: () => {
          errores += 1;
          pendientes -= 1;
          if (pendientes === 0) this.alTerminarLote(errores);
        },
      });
    }
  }

  protected abrirDialogoRechazo(): void {
    if (this.seleccion().length === 0) return;
    this.motivoRechazo.set('');
    this.dialogoRechazoAbierto.set(true);
  }

  protected cerrarDialogoRechazo(): void {
    this.dialogoRechazoAbierto.set(false);
  }

  protected confirmarRechazoSeleccionados(): void {
    const motivo = this.motivoRechazo().trim();
    if (!motivo) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Escriba el motivo del rechazo.' });
      return;
    }
    const ids = this.seleccion();
    this.procesando.set(true);
    this.dialogoRechazoAbierto.set(false);
    let pendientes = ids.length;
    let errores = 0;
    for (const id of ids) {
      this.registrosService.rechazar(id, motivo).subscribe({
        next: () => {
          pendientes -= 1;
          if (pendientes === 0) this.alTerminarLote(errores);
        },
        error: () => {
          errores += 1;
          pendientes -= 1;
          if (pendientes === 0) this.alTerminarLote(errores);
        },
      });
    }
  }

  private alTerminarLote(errores: number): void {
    this.procesando.set(false);
    this.toast.mostrar({
      tipo: errores > 0 ? 'alerta' : 'exito',
      mensaje: errores > 0 ? `Rechazados con ${errores} error(es).` : 'Registros rechazados.',
    });
    this.cargar();
  }
}
