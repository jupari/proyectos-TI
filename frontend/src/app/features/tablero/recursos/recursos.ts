import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ChartData, ChartOptions, ScriptableContext } from 'chart.js';
import { colorTema } from '../../../shared/ui/grafico/colores-tema';


import { OcupacionRecurso } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { HorasPipe, PorcentajePipe } from '../../../shared/pipes';
import { Boton } from '../../../shared/ui/boton/boton';
import { Card } from '../../../shared/ui/card/card';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Grafico } from '../../../shared/ui/grafico/grafico';
import { Input } from '../../../shared/ui/input/input';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { ColumnaTabla, Tabla } from '../../../shared/ui/tabla/tabla';
import { PerfilesRecursoService } from '../../admin/data/catalogos.service';
import { TableroService } from '../data/tablero.service';
import { sincronizarQueryParams } from '../../../core/ui/query-params';

const MARCA_400 = () => colorTema('primario-400');
const PELIGRO = '#dc2626';

interface FilaOcupacion extends OcupacionRecurso {
  id: string;
}

@Component({
  selector: 'app-recursos-tablero',
  templateUrl: './recursos.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Card, EstadoVacio, Grafico, Input, Select, Tabla, HorasPipe, PorcentajePipe],
})
export class RecursosTablero {
  private readonly tableroService = inject(TableroService);
  private readonly perfilesService = inject(PerfilesRecursoService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected readonly desde = signal<string>(this.hace(3));
  protected readonly hasta = signal<string>(this.hoy());
  protected readonly perfil = signal<string | null>(null);
  protected readonly opcionesPerfiles = signal<OpcionSelect[]>([]);

  protected readonly cargando = signal(false);
  protected readonly error = signal(false);
  protected readonly exportando = signal(false);
  protected readonly filas = signal<FilaOcupacion[]>([]);

  protected readonly columnas: ColumnaTabla<FilaOcupacion>[] = [
    { clave: 'recurso_nombre', titulo: 'Recurso' },
    { clave: 'anio', titulo: 'Año' },
    { clave: 'mes', titulo: 'Mes' },
    { clave: 'horas_planeadas', titulo: 'Horas planeadas', alinear: 'derecha' },
    { clave: 'horas_ejecutadas', titulo: 'Horas ejecutadas', alinear: 'derecha' },
    { clave: 'capacidad', titulo: 'Capacidad', alinear: 'derecha' },
    { clave: 'pct_ocupacion', titulo: '% ocupación', alinear: 'derecha' },
  ];

  protected readonly grafico = computed<ChartData>(() => {
    const filas = this.filas();
    return {
      labels: filas.map((fila) => `${fila.recurso_nombre} (${fila.anio}-${String(fila.mes).padStart(2, '0')})`),
      datasets: [
        {
          label: '% ocupación',
          data: filas.map((fila) => fila.pct_ocupacion ?? 0),
          backgroundColor: (contexto: ScriptableContext<'bar'>) => ((filas[contexto.dataIndex]?.pct_ocupacion ?? 0) > 100 ? PELIGRO : MARCA_400()),
        },
      ],
    };
  });

  protected readonly opcionesGrafico: ChartOptions = {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true } },
  };

  protected readonly filasTablaGrafico = computed(() =>
    this.filas().map((fila) => [
      fila.recurso_nombre,
      `${fila.anio}-${String(fila.mes).padStart(2, '0')}`,
      fila.pct_ocupacion ?? '—',
    ]),
  );

  constructor() {
    const parametros = this.ruta.snapshot.queryParamMap;
    this.desde.set(parametros.get('desde') ?? this.hace(3));
    this.hasta.set(parametros.get('hasta') ?? this.hoy());
    this.perfil.set(parametros.get('perfil'));

    this.perfilesService
      .listar({ page_size: 200 })
      .subscribe((respuesta) =>
        this.opcionesPerfiles.set(respuesta.results.map((p) => ({ valor: p.id, etiqueta: p.nombre }))),
      );

    this.cargar();
  }

  private hoy(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private hace(meses: number): string {
    const fecha = new Date();
    fecha.setMonth(fecha.getMonth() - meses);
    return fecha.toISOString().slice(0, 10);
  }

  private sincronizarUrl(): void {
    const queryParams: Record<string, string> = { desde: this.desde(), hasta: this.hasta() };
    if (this.perfil()) queryParams['perfil'] = this.perfil()!;
    sincronizarQueryParams(this.router, this.ruta, queryParams);
  }

  protected cargar(refrescar = false): void {
    this.sincronizarUrl();
    this.cargando.set(true);
    this.error.set(false);
    this.tableroService
      .recursos({
        desde: this.desde(),
        hasta: this.hasta(),
        perfil: this.perfil() ?? undefined,
        refrescar: refrescar || undefined,
      })
      .subscribe({
        next: (respuesta) => {
          this.filas.set(
            respuesta.recursos.map((fila, indice) => ({ ...fila, id: `${fila.recurso}-${indice}` })),
          );
          this.cargando.set(false);
        },
        error: () => {
          this.error.set(true);
          this.cargando.set(false);
        },
      });
  }

  protected exportarCsv(): void {
    this.exportando.set(true);
    this.tableroService
      .exportarCsv('recursos', { desde: this.desde(), hasta: this.hasta(), perfil: this.perfil() ?? undefined })
      .subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const enlace = document.createElement('a');
          enlace.href = url;
          enlace.download = 'tablero-recursos.csv';
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
}
