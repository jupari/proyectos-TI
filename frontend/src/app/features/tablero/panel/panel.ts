import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ChartData, ChartOptions, ScriptableContext } from 'chart.js';
import { colorTema } from '../../../shared/ui/grafico/colores-tema';

import {
  ETIQUETAS_ESTADO_PROYECTO,
  FilaTableroProyecto,
  FiltrosTablero,
  OcupacionRecurso,
  PuntoEjecucionMensual,
  ResumenGlobalTablero,
} from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { HorasPipe, MonedaPipe, PorcentajePipe } from '../../../shared/pipes';
import { Boton } from '../../../shared/ui/boton/boton';
import { Card } from '../../../shared/ui/card/card';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Grafico } from '../../../shared/ui/grafico/grafico';
import { Input } from '../../../shared/ui/input/input';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Semaforo, ValorSemaforo } from '../../../shared/ui/semaforo/semaforo';
import { Switch } from '../../../shared/ui/switch/switch';
import { CambioOrden, ColumnaTabla, Tabla } from '../../../shared/ui/tabla/tabla';
import { AreasService, PortafoliosService } from '../../admin/data/catalogos.service';
import { UsuariosService } from '../../admin/data/usuarios.service';
import { TableroService } from '../data/tablero.service';

// Paleta validada con la skill `dataviz` (fase 10): subconjunto de 4 pasos
// de `marca` que pasa las seis comprobaciones (los 10 pasos completos no
// pasan el piso de contraste del extremo claro). Nunca colores por defecto
// de Chart.js.
const MARCA_400 = () => colorTema('primario-400');
const MARCA_900 = () => colorTema('primario-800');
const SEMAFORO_VERDE = '#16a34a';
const SEMAFORO_AMARILLO = '#eab308';
const SEMAFORO_ROJO = '#dc2626';
const PELIGRO = '#dc2626';

@Component({
  selector: 'app-panel-tablero',
  templateUrl: './panel.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Boton,
    Card,
    EstadoVacio,
    Grafico,
    Input,
    Progreso,
    Select,
    Semaforo,
    Switch,
    Tabla,
    HorasPipe,
    MonedaPipe,
    PorcentajePipe,
  ],
})
export class PanelTablero {
  private readonly tableroService = inject(TableroService);
  private readonly areasService = inject(AreasService);
  private readonly portafoliosService = inject(PortafoliosService);
  private readonly usuariosService = inject(UsuariosService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected readonly ETIQUETAS_ESTADO_PROYECTO = ETIQUETAS_ESTADO_PROYECTO;

  protected readonly estado = signal<string | null>(null);
  protected readonly portafolio = signal<string | null>(null);
  protected readonly area = signal<string | null>(null);
  protected readonly gerente = signal<string | null>(null);
  protected readonly desde = signal<string | null>(null);
  protected readonly hasta = signal<string | null>(null);
  protected readonly soloMisProyectos = signal(false);

  protected readonly opcionesEstado: OpcionSelect[] = Object.entries(ETIQUETAS_ESTADO_PROYECTO).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );
  protected readonly opcionesAreas = signal<OpcionSelect[]>([]);
  protected readonly opcionesPortafolios = signal<OpcionSelect[]>([]);
  protected readonly opcionesGerentes = signal<OpcionSelect[]>([]);

  protected readonly cargandoResumen = signal(false);
  protected readonly errorResumen = signal(false);
  protected readonly resumen = signal<ResumenGlobalTablero | null>(null);

  protected readonly cargandoTabla = signal(false);
  protected readonly errorTabla = signal(false);
  protected readonly filas = signal<FilaTableroProyecto[]>([]);
  protected readonly ordenActual = signal<CambioOrden | null>(null);

  protected readonly cargandoGraficos = signal(false);
  protected readonly errorGraficos = signal(false);
  protected readonly serieMensual = signal<PuntoEjecucionMensual[]>([]);
  protected readonly ocupacion = signal<OcupacionRecurso[]>([]);

  protected readonly exportando = signal(false);
  protected readonly ahora = signal(Date.now());

  protected readonly columnas: ColumnaTabla<FilaTableroProyecto>[] = [
    { clave: 'codigo', titulo: 'Código', ordenable: true, ancho: '110px' },
    { clave: 'nombre', titulo: 'Proyecto', ordenable: true },
    { clave: 'gerente', titulo: 'Gerente' },
    { clave: 'estado', titulo: 'Estado' },
    { clave: 'avance', titulo: 'Avance' },
    { clave: 'pct_horas', titulo: '% horas', alinear: 'derecha', ordenable: true },
    { clave: 'pct_dinero', titulo: '% dinero', alinear: 'derecha', ordenable: true },
    { clave: 'spi', titulo: 'SPI', alinear: 'derecha', ordenable: true },
    { clave: 'cpi', titulo: 'CPI', alinear: 'derecha', ordenable: true },
    { clave: 'desviacion', titulo: 'Desviación', alinear: 'derecha', ordenable: true },
    { clave: 'semaforo', titulo: 'Semáforo', alinear: 'centro' },
  ];

  protected readonly filasOrdenadas = computed(() => {
    const orden = this.ordenActual();
    const filas = [...this.filas()];
    if (!orden) return filas;

    const valorDe = (fila: FilaTableroProyecto): string | number => {
      switch (orden.clave) {
        case 'codigo':
          return fila.codigo;
        case 'nombre':
          return fila.nombre;
        case 'pct_horas':
          return fila.resumen_ejecucion.pct_horas ?? -Infinity;
        case 'pct_dinero':
          return fila.resumen_ejecucion.pct_dinero ?? -Infinity;
        case 'spi':
          return fila.resumen_ejecucion.spi ?? -Infinity;
        case 'cpi':
          return fila.resumen_ejecucion.cpi ?? -Infinity;
        case 'desviacion':
          return fila.resumen_ejecucion.desviacion_presupuestal;
        default:
          return '';
      }
    };

    return filas.sort((a, b) => {
      const va = valorDe(a);
      const vb = valorDe(b);
      const comparacion = va < vb ? -1 : va > vb ? 1 : 0;
      return orden.direccion === 'asc' ? comparacion : -comparacion;
    });
  });

  protected readonly calculadoHaceSegundos = computed(() => {
    const calculadoEn = this.resumen()?.calculado_en;
    if (!calculadoEn) return null;
    const segundos = Math.max(0, Math.round((this.ahora() - new Date(calculadoEn).getTime()) / 1000));
    if (segundos < 5) return 'hace un momento';
    if (segundos < 60) return `hace ${segundos} segundos`;
    return `hace ${Math.round(segundos / 60)} min`;
  });

  protected readonly graficoSemaforo = computed<ChartData>(() => {
    const porSemaforo = this.resumen()?.por_semaforo ?? {};
    return {
      labels: ['Verde', 'Amarillo', 'Rojo'],
      datasets: [
        {
          label: 'Proyectos',
          data: [porSemaforo['VERDE'] ?? 0, porSemaforo['AMARILLO'] ?? 0, porSemaforo['ROJO'] ?? 0],
          backgroundColor: [SEMAFORO_VERDE, SEMAFORO_AMARILLO, SEMAFORO_ROJO],
        },
      ],
    };
  });

  protected readonly opcionesGraficoSemaforo: ChartOptions = {
    indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
  };

  protected readonly top10PorPresupuesto = computed(() =>
    [...this.filas()]
      .sort(
        (a, b) => Number(b.resumen_ejecucion.costo_planeado) - Number(a.resumen_ejecucion.costo_planeado),
      )
      .slice(0, 10),
  );

  protected readonly graficoHoras = computed<ChartData>(() => {
    const top = this.top10PorPresupuesto();
    return {
      labels: top.map((fila) => fila.nombre),
      datasets: [
        {
          label: 'Horas planeadas',
          data: top.map((fila) => fila.resumen_ejecucion.horas_planeadas),
          backgroundColor: MARCA_400,
        },
        {
          label: 'Horas ejecutadas',
          data: top.map((fila) => fila.resumen_ejecucion.horas_ejecutadas),
          backgroundColor: MARCA_900,
        },
      ],
    };
  });

  protected readonly opcionesGraficoHoras: ChartOptions = {
    scales: { y: { beginAtZero: true } },
  };

  protected readonly filasTablaHoras = computed(() =>
    this.top10PorPresupuesto().map((fila) => [
      fila.nombre,
      fila.resumen_ejecucion.horas_planeadas,
      fila.resumen_ejecucion.horas_ejecutadas,
    ]),
  );

  private planAcumuladoPorMes(): number[] {
    let acumuladoPlan = 0;
    return this.serieMensual().map((punto) => (acumuladoPlan += punto.costo_plan));
  }

  protected readonly graficoCosto = computed<ChartData>(() => {
    const serie = this.serieMensual();
    const planAcumulado = this.planAcumuladoPorMes();
    return {
      labels: serie.map((punto) => punto.mes),
      datasets: [
        {
          label: 'Planeado (acumulado)',
          data: planAcumulado,
          borderColor: MARCA_900,
          borderDash: [6, 4],
          backgroundColor: 'transparent',
        },
        {
          label: 'Ejecutado (acumulado)',
          data: serie.map((punto) => punto.costo_ejec_acum),
          borderColor: MARCA_900,
          backgroundColor: 'transparent',
        },
      ],
    };
  });

  protected readonly filasTablaCosto = computed(() => {
    const serie = this.serieMensual();
    const planAcumulado = this.planAcumuladoPorMes();
    return serie.map((punto, indice) => [punto.mes, planAcumulado[indice], punto.costo_ejec_acum]);
  });

  protected readonly opcionesGraficoCosto: ChartOptions = {
    scales: { y: { beginAtZero: true } },
  };

  protected readonly promediosPorRecurso = computed(() => {
    const porRecurso = new Map<string, { suma: number; total: number }>();
    for (const fila of this.ocupacion()) {
      const entrada = porRecurso.get(fila.recurso_nombre) ?? { suma: 0, total: 0 };
      entrada.suma += fila.pct_ocupacion ?? 0;
      entrada.total += 1;
      porRecurso.set(fila.recurso_nombre, entrada);
    }
    return [...porRecurso.entries()].map(([nombre, { suma, total }]) => ({
      nombre,
      promedio: total > 0 ? suma / total : 0,
    }));
  });

  protected readonly graficoOcupacion = computed<ChartData>(() => {
    const datos = this.promediosPorRecurso();
    return {
      labels: datos.map((d) => d.nombre),
      datasets: [
        {
          label: '% ocupación promedio',
          data: datos.map((d) => d.promedio),
          backgroundColor: (contexto: ScriptableContext<'bar'>) => ((datos[contexto.dataIndex]?.promedio ?? 0) > 100 ? PELIGRO : MARCA_400()),
        },
      ],
    };
  });

  protected readonly filasTablaOcupacion = computed(() =>
    this.promediosPorRecurso().map((d) => [d.nombre, Math.round(d.promedio * 10) / 10]),
  );

  protected readonly opcionesGraficoOcupacion: ChartOptions = {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true } },
  };

  constructor() {
    const parametros = this.ruta.snapshot.queryParamMap;
    this.estado.set(parametros.get('estado'));
    this.portafolio.set(parametros.get('portafolio'));
    this.area.set(parametros.get('area_solicitante'));
    this.gerente.set(parametros.get('gerente'));
    this.desde.set(parametros.get('desde'));
    this.hasta.set(parametros.get('hasta'));
    this.soloMisProyectos.set(parametros.get('mis_proyectos') === 'true');

    setInterval(() => this.ahora.set(Date.now()), 5000);

    this.cargarCatalogos();
    this.cargarTodo();
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
        this.opcionesPortafolios.set(respuesta.results.map((p) => ({ valor: p.id, etiqueta: p.nombre }))),
      );
    // El listado de usuarios exige ADMIN o PMO (docs/api-contrato.md §8); el
    // resto de roles simplemente no ve el filtro por gerente poblado.
    this.usuariosService.listar({ page_size: 200 }).subscribe({
      next: (respuesta) =>
        this.opcionesGerentes.set(
          respuesta.results.map((u) => ({ valor: u.id, etiqueta: `${u.nombres} ${u.apellidos}` })),
        ),
      error: () => this.opcionesGerentes.set([]),
    });
  }

  private filtrosProyecto(): FiltrosTablero {
    return {
      estado: this.estado() ?? undefined,
      portafolio: this.portafolio() ?? undefined,
      area_solicitante: this.area() ?? undefined,
      gerente: this.gerente() ?? undefined,
      mis_proyectos: this.soloMisProyectos() || undefined,
    };
  }

  /** `ejecucion-mensual` y `recursos` sí usan el rango de fechas; el resto
   * de bloques del tablero no tiene un filtro de fechas natural (a
   * diferencia de `/proyectos/`, ver Evidencia de la fase). Sin rango
   * explícito se usan los últimos 3 meses, igual que el precondicionado de
   * `seed_demo`. */
  private rangoFechas(): { desde: string; hasta: string } {
    if (this.desde() && this.hasta()) {
      return { desde: this.desde()!, hasta: this.hasta()! };
    }
    const hastaDefecto = new Date();
    const desdeDefecto = new Date();
    desdeDefecto.setMonth(desdeDefecto.getMonth() - 3);
    return { desde: this.aIso(desdeDefecto), hasta: this.aIso(hastaDefecto) };
  }

  private aIso(fecha: Date): string {
    return fecha.toISOString().slice(0, 10);
  }

  private sincronizarUrl(): void {
    const queryParams: Record<string, string> = {};
    const filtros = { ...this.filtrosProyecto(), desde: this.desde() ?? undefined, hasta: this.hasta() ?? undefined };
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== undefined && valor !== '') queryParams[clave] = String(valor);
    }
    void this.router.navigate([], { relativeTo: this.ruta, queryParams });
  }

  protected cargarTodo(refrescar = false): void {
    this.sincronizarUrl();
    this.cargarResumen(refrescar);
    this.cargarTabla(refrescar);
    this.cargarGraficos(refrescar);
  }

  private cargarResumen(refrescar: boolean): void {
    this.cargandoResumen.set(true);
    this.errorResumen.set(false);
    const filtros = { ...this.filtrosProyecto(), refrescar: refrescar || undefined };
    this.tableroService.resumen(filtros).subscribe({
      next: (respuesta) => {
        this.resumen.set(respuesta);
        this.ahora.set(Date.now());
        this.cargandoResumen.set(false);
      },
      error: () => {
        this.errorResumen.set(true);
        this.cargandoResumen.set(false);
      },
    });
  }

  private cargarTabla(refrescar: boolean): void {
    this.cargandoTabla.set(true);
    this.errorTabla.set(false);
    const filtros = { ...this.filtrosProyecto(), refrescar: refrescar || undefined };
    this.tableroService.proyectos(filtros).subscribe({
      next: (respuesta) => {
        this.filas.set(respuesta.filas);
        this.cargandoTabla.set(false);
      },
      error: () => {
        this.errorTabla.set(true);
        this.cargandoTabla.set(false);
      },
    });
  }

  private cargarGraficos(refrescar: boolean): void {
    this.cargandoGraficos.set(true);
    this.errorGraficos.set(false);
    const { desde, hasta } = this.rangoFechas();
    const filtrosMensual = { ...this.filtrosProyecto(), desde, hasta, refrescar: refrescar || undefined };
    const filtrosRecursos = { ...this.filtrosProyecto(), desde, hasta, refrescar: refrescar || undefined };

    this.tableroService.ejecucionMensual(filtrosMensual).subscribe({
      next: (respuesta) => this.serieMensual.set(respuesta.serie),
      error: () => this.errorGraficos.set(true),
    });
    this.tableroService.recursos(filtrosRecursos).subscribe({
      next: (respuesta) => {
        this.ocupacion.set(respuesta.recursos);
        this.cargandoGraficos.set(false);
      },
      error: () => {
        this.errorGraficos.set(true);
        this.cargandoGraficos.set(false);
      },
    });
  }

  protected aplicarFiltros(): void {
    this.cargarTodo();
  }

  protected limpiarFiltros(): void {
    this.estado.set(null);
    this.portafolio.set(null);
    this.area.set(null);
    this.gerente.set(null);
    this.desde.set(null);
    this.hasta.set(null);
    this.soloMisProyectos.set(false);
    this.cargarTodo();
  }

  protected refrescar(): void {
    this.cargarTodo(true);
  }

  protected alCambiarOrden(orden: CambioOrden): void {
    this.ordenActual.set(orden);
  }

  protected exportarCsv(): void {
    this.exportando.set(true);
    this.tableroService.exportarCsv('proyectos', this.filtrosProyecto()).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = 'tablero-proyectos.csv';
        enlace.click();
        URL.revokeObjectURL(url);
        this.exportando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo exportar el CSV.' });
        this.exportando.set(false);
      },
    });
  }

  protected esValorSemaforo(valor: string): ValorSemaforo {
    return valor as ValorSemaforo;
  }

  protected numero(valor: string): number {
    return Number(valor);
  }
}
