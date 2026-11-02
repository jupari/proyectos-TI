import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import {
  ETIQUETAS_ESTADO_PROYECTO,
  ETIQUETAS_PRIORIDAD,
  ETIQUETAS_SEMAFORO,
  RespuestaPaginada,
} from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import {
  EtiquetaEnumPipe,
  FechaCortaPipe,
  PorcentajePipe,
} from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Input } from '../../../shared/ui/input/input';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Semaforo, ValorSemaforo } from '../../../shared/ui/semaforo/semaforo';
import { Switch } from '../../../shared/ui/switch/switch';
import { CambioOrden, ColumnaTabla, Tabla } from '../../../shared/ui/tabla/tabla';
import { AreasService, PortafoliosService } from '../../admin/data/catalogos.service';
import { FiltrosProyecto, ProyectoLista } from '../data/proyectos.model';
import { ProyectosService } from '../data/proyectos.service';

@Component({
  selector: 'app-lista-proyectos',
  templateUrl: './lista.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Tabla,
    Boton,
    Badge,
    Progreso,
    Semaforo,
    Select,
    Switch,
    Input,
    EtiquetaEnumPipe,
    FechaCortaPipe,
    PorcentajePipe,
  ],
})
export class ListaProyectos {
  private readonly proyectosService = inject(ProyectosService);
  private readonly areasService = inject(AreasService);
  private readonly portafoliosService = inject(PortafoliosService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected readonly ETIQUETAS_ESTADO_PROYECTO = ETIQUETAS_ESTADO_PROYECTO;

  protected readonly cargando = signal(false);
  protected readonly respuesta = signal<RespuestaPaginada<ProyectoLista> | null>(null);
  protected readonly paginaActual = signal(1);
  protected readonly ordenActual = signal<CambioOrden | null>(null);

  protected readonly busqueda = signal('');
  protected readonly estado = signal<string | null>(null);
  protected readonly prioridad = signal<string | null>(null);
  protected readonly portafolio = signal<string | null>(null);
  protected readonly area = signal<string | null>(null);
  protected readonly semaforo = signal<string | null>(null);
  protected readonly soloMisProyectos = signal(false);

  protected readonly opcionesAreas = signal<OpcionSelect[]>([]);
  protected readonly opcionesPortafolios = signal<OpcionSelect[]>([]);

  protected readonly opcionesEstado: OpcionSelect[] = Object.entries(ETIQUETAS_ESTADO_PROYECTO).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );
  protected readonly opcionesPrioridad: OpcionSelect[] = Object.entries(ETIQUETAS_PRIORIDAD).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );
  protected readonly opcionesSemaforo: OpcionSelect[] = Object.entries(ETIQUETAS_SEMAFORO).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );

  protected readonly puedeCrear = computed(() => this.auth.tienePermiso('proyectos.crear'));

  protected readonly columnas: ColumnaTabla<ProyectoLista>[] = [
    { clave: 'codigo', titulo: 'Código', ordenable: true, ancho: '110px' },
    { clave: 'nombre', titulo: 'Proyecto', ordenable: true },
    { clave: 'area_nombre', titulo: 'Área' },
    { clave: 'gerente_nombre', titulo: 'Gerente' },
    { clave: 'estado', titulo: 'Estado' },
    { clave: 'prioridad', titulo: 'Prioridad' },
    { clave: 'fecha_inicio_plan', titulo: 'Inicio', ordenable: true },
    { clave: 'fecha_fin_plan', titulo: 'Fin', ordenable: true },
    { clave: 'avance', titulo: 'Avance' },
    { clave: 'pct_horas', titulo: '% horas', alinear: 'derecha' },
    { clave: 'pct_dinero', titulo: '% dinero', alinear: 'derecha' },
    { clave: 'semaforo', titulo: 'Semáforo', alinear: 'centro' },
    { clave: 'acciones', titulo: '', alinear: 'derecha' },
  ];

  constructor() {
    const parametros = this.ruta.snapshot.queryParamMap;
    this.busqueda.set(parametros.get('search') ?? '');
    this.estado.set(parametros.get('estado'));
    this.prioridad.set(parametros.get('prioridad'));
    this.portafolio.set(parametros.get('portafolio'));
    this.area.set(parametros.get('area_solicitante'));
    this.semaforo.set(parametros.get('semaforo'));
    this.soloMisProyectos.set(parametros.get('mis_proyectos') === 'true');
    const pagina = Number(parametros.get('page') ?? '1');
    this.paginaActual.set(Number.isFinite(pagina) && pagina > 0 ? pagina : 1);
    const ordering = parametros.get('ordering');
    if (ordering) {
      this.ordenActual.set({
        clave: ordering.replace(/^-/, ''),
        direccion: ordering.startsWith('-') ? 'desc' : 'asc',
      });
    }

    this.cargarCatalogos();
    this.cargar();
  }

  private cargarCatalogos(): void {
    this.areasService
      .listar({ page_size: 200 })
      .subscribe((respuesta) =>
        this.opcionesAreas.set(respuesta.results.map((a) => ({ valor: a.id, etiqueta: a.nombre }))),
      );
    this.portafoliosService
      .listar({ page_size: 200 })
      .subscribe((respuesta) =>
        this.opcionesPortafolios.set(
          respuesta.results.map((p) => ({ valor: p.id, etiqueta: p.nombre })),
        ),
      );
  }

  private filtrosActuales(): FiltrosProyecto {
    const orden = this.ordenActual();
    return {
      search: this.busqueda() || undefined,
      estado: this.estado() ?? undefined,
      prioridad: this.prioridad() ?? undefined,
      portafolio: this.portafolio() ?? undefined,
      area_solicitante: this.area() ?? undefined,
      semaforo: this.semaforo() ?? undefined,
      mis_proyectos: this.soloMisProyectos() || undefined,
      ordering: orden ? `${orden.direccion === 'desc' ? '-' : ''}${orden.clave}` : undefined,
      page: this.paginaActual() > 1 ? this.paginaActual() : undefined,
    };
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.sincronizarUrl();
    this.proyectosService.listarProyectos(this.filtrosActuales()).subscribe({
      next: (respuesta) => {
        this.respuesta.set(respuesta);
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la lista de proyectos.' });
        this.cargando.set(false);
      },
    });
  }

  private sincronizarUrl(): void {
    const filtros = this.filtrosActuales();
    const queryParams: Record<string, string> = {};
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== undefined && valor !== '') {
        queryParams[clave === 'search' ? 'search' : clave] = String(valor);
      }
    }
    void this.router.navigate([], { relativeTo: this.ruta, queryParams });
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
    this.busqueda.set('');
    this.estado.set(null);
    this.prioridad.set(null);
    this.portafolio.set(null);
    this.area.set(null);
    this.semaforo.set(null);
    this.soloMisProyectos.set(false);
    this.aplicarFiltros();
  }

  protected esValorSemaforo(valor: string): ValorSemaforo {
    return valor as ValorSemaforo;
  }

  protected numero(valor: string): number {
    return Number(valor);
  }
}
