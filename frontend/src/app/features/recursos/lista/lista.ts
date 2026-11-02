import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { ETIQUETAS_TIPO_RECURSO, RespuestaPaginada } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, HorasPipe, MonedaPipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Input } from '../../../shared/ui/input/input';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Switch } from '../../../shared/ui/switch/switch';
import { CambioOrden, ColumnaTabla, Tabla } from '../../../shared/ui/tabla/tabla';
import { PerfilesRecursoService } from '../../admin/data/catalogos.service';
import { FiltrosRecurso, RecursoLista } from '../data/recursos.model';
import { RecursosService } from '../data/recursos.service';

@Component({
  selector: 'app-lista-recursos',
  templateUrl: './lista.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Tabla,
    Boton,
    Badge,
    Select,
    Switch,
    Input,
    EtiquetaEnumPipe,
    HorasPipe,
    MonedaPipe,
  ],
})
export class ListaRecursos {
  private readonly recursosService = inject(RecursosService);
  private readonly perfilesService = inject(PerfilesRecursoService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected readonly ETIQUETAS_TIPO_RECURSO = ETIQUETAS_TIPO_RECURSO;

  protected readonly cargando = signal(false);
  protected readonly respuesta = signal<RespuestaPaginada<RecursoLista> | null>(null);
  protected readonly paginaActual = signal(1);
  protected readonly ordenActual = signal<CambioOrden | null>(null);

  protected readonly busqueda = signal('');
  protected readonly tipo = signal<string | null>(null);
  protected readonly perfil = signal<string | null>(null);
  protected readonly sinAsignacion = signal(false);

  protected readonly opcionesPerfiles = signal<OpcionSelect[]>([]);
  protected readonly opcionesTipo: OpcionSelect[] = Object.entries(ETIQUETAS_TIPO_RECURSO).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );

  protected readonly puedeCrear = computed(() => this.auth.tienePermiso('recursos.crear'));

  protected readonly columnas: ColumnaTabla<RecursoLista>[] = [
    { clave: 'nombre', titulo: 'Nombre', ordenable: true },
    { clave: 'tipo', titulo: 'Tipo' },
    { clave: 'perfil_nombre', titulo: 'Perfil' },
    { clave: 'tarifa_vigente', titulo: 'Tarifa vigente', alinear: 'derecha' },
    { clave: 'capacidad_horas_mes', titulo: 'Capacidad', alinear: 'derecha' },
    { clave: 'proyectos_activos', titulo: 'Proyectos activos', alinear: 'centro' },
    { clave: 'activo', titulo: 'Estado' },
    { clave: 'acciones', titulo: '', alinear: 'derecha' },
  ];

  constructor() {
    const parametros = this.ruta.snapshot.queryParamMap;
    this.busqueda.set(parametros.get('search') ?? '');
    this.tipo.set(parametros.get('tipo'));
    this.perfil.set(parametros.get('perfil'));
    this.sinAsignacion.set(parametros.get('sin_asignacion') === 'true');

    this.perfilesService
      .listar({ page_size: 200 })
      .subscribe((r) =>
        this.opcionesPerfiles.set(r.results.map((p) => ({ valor: p.id, etiqueta: p.nombre }))),
      );
    this.cargar();
  }

  private filtrosActuales(): FiltrosRecurso {
    return {
      search: this.busqueda() || undefined,
      tipo: this.tipo() ?? undefined,
      perfil: this.perfil() ?? undefined,
      sin_asignacion: this.sinAsignacion() || undefined,
      page: this.paginaActual() > 1 ? this.paginaActual() : undefined,
    };
  }

  protected cargar(): void {
    this.cargando.set(true);
    const filtros = this.filtrosActuales();
    const queryParams: Record<string, string> = {};
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== undefined && valor !== '') queryParams[clave] = String(valor);
    }
    void this.router.navigate([], { relativeTo: this.ruta, queryParams });

    this.recursosService.listarRecursos(filtros).subscribe({
      next: (respuesta) => {
        this.respuesta.set(respuesta);
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la lista de recursos.' });
        this.cargando.set(false);
      },
    });
  }

  protected aplicarFiltros(): void {
    this.paginaActual.set(1);
    this.cargar();
  }

  protected alCambiarPagina(pagina: number): void {
    this.paginaActual.set(pagina);
    this.cargar();
  }
}
