import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { ETIQUETAS_ESTADO_SEGUIMIENTO, RespuestaPaginada, Seguimiento } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, FechaCortaPipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Semaforo, ValorSemaforo } from '../../../shared/ui/semaforo/semaforo';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { CambioOrden, ColumnaTabla, Tabla } from '../../../shared/ui/tabla/tabla';
import { ProyectosService } from '../../proyectos/data/proyectos.service';
import { FiltrosSeguimiento } from '../data/seguimientos.model';
import { SeguimientosService } from '../data/seguimientos.service';

@Component({
  selector: 'app-lista-seguimientos',
  templateUrl: './lista.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Tabla,
    Boton,
    Badge,
    Semaforo,
    Select,
    EtiquetaEnumPipe,
    FechaCortaPipe,
  ],
})
export class ListaSeguimientos {
  private readonly seguimientosService = inject(SeguimientosService);
  private readonly proyectosService = inject(ProyectosService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected readonly ETIQUETAS_ESTADO_SEGUIMIENTO = ETIQUETAS_ESTADO_SEGUIMIENTO;

  protected readonly cargando = signal(false);
  protected readonly respuesta = signal<RespuestaPaginada<Seguimiento> | null>(null);
  protected readonly paginaActual = signal(1);
  protected readonly ordenActual = signal<CambioOrden | null>(null);

  protected readonly proyecto = signal<string | null>(null);
  protected readonly periodicidad = signal<string | null>(null);
  protected readonly estado = signal<string | null>(null);

  protected readonly opcionesProyectos = signal<OpcionSelect[]>([]);
  protected readonly opcionesPeriodicidad: OpcionSelect[] = [
    { valor: 'DIARIA', etiqueta: 'Diaria' },
    { valor: 'SEMANAL', etiqueta: 'Semanal' },
    { valor: 'MENSUAL', etiqueta: 'Mensual' },
  ];
  protected readonly opcionesEstado: OpcionSelect[] = [
    { valor: 'BORRADOR', etiqueta: 'Borrador' },
    { valor: 'PUBLICADO', etiqueta: 'Publicado' },
  ];

  protected readonly puedeCrear = computed(() => this.auth.tienePermiso('seguimientos.crear'));

  protected readonly columnas: ColumnaTabla<Seguimiento>[] = [
    { clave: 'proyecto_codigo', titulo: 'Proyecto', ordenable: false },
    { clave: 'periodicidad', titulo: 'Periodicidad' },
    { clave: 'periodo_inicio', titulo: 'Periodo', ordenable: true },
    { clave: 'fecha_corte', titulo: 'Fecha de corte', ordenable: true },
    { clave: 'avance_reportado', titulo: 'Avance' },
    { clave: 'semaforo', titulo: 'Semáforo' },
    { clave: 'estado', titulo: 'Estado' },
    { clave: 'publicado_por_nombre', titulo: 'Autor' },
    { clave: 'acciones', titulo: '', alinear: 'derecha' },
  ];

  constructor() {
    const parametros = this.ruta.snapshot.queryParamMap;
    this.proyecto.set(parametros.get('proyecto'));
    this.periodicidad.set(parametros.get('periodicidad'));
    this.estado.set(parametros.get('estado'));
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

  private filtrosActuales(): FiltrosSeguimiento {
    const orden = this.ordenActual();
    return {
      proyecto: this.proyecto() ?? undefined,
      periodicidad: this.periodicidad() ?? undefined,
      estado: this.estado() ?? undefined,
      ordering: orden ? `${orden.direccion === 'desc' ? '-' : ''}${orden.clave}` : undefined,
      page: this.paginaActual() > 1 ? this.paginaActual() : undefined,
    };
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.sincronizarUrl();
    this.seguimientosService.listarSeguimientos(this.filtrosActuales()).subscribe({
      next: (respuesta) => {
        this.respuesta.set(respuesta);
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la lista de seguimientos.' });
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
    void this.router.navigate([], { relativeTo: this.ruta, queryParams });
  }

  protected aplicarFiltros(): void {
    this.paginaActual.set(1);
    this.cargar();
  }

  protected limpiarFiltros(): void {
    this.proyecto.set(null);
    this.periodicidad.set(null);
    this.estado.set(null);
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

  protected esValorSemaforo(valor: string): ValorSemaforo {
    return valor as ValorSemaforo;
  }

  protected numero(valor: string): number {
    return Number(valor);
  }
}
