import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  signal,
  untracked,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChartData, ChartOptions } from 'chart.js';

import {
  BurndownSprint,
  SprintResumen,
  SprintsProyecto as DatosSprints,
} from '../../../../core/models';
import { FechaCortaPipe, HorasPipe } from '../../../../shared/pipes';
import { EstadoVacio } from '../../../../shared/ui/estado-vacio/estado-vacio';
import { colorTema } from '../../../../shared/ui/grafico/colores-tema';
import { Grafico } from '../../../../shared/ui/grafico/grafico';
import { Progreso } from '../../../../shared/ui/progreso/progreso';
import { OpcionSelect, Select } from '../../../../shared/ui/select/select';
import { TableroService } from '../../../tablero/data/tablero.service';

const ETIQUETAS_ESTADO: Record<SprintResumen['estado'], string> = {
  FUTURO: 'Futuro',
  ACTIVO: 'Activo',
  CERRADO: 'Cerrado',
};

/** Pestaña «Sprints» del proyecto: burndown del sprint elegido, velocidad por
 * sprint y la lista con su avance. Todo es de solo lectura sobre lo que se
 * importa de Jira. */
@Component({
  selector: 'app-sprints-proyecto',
  templateUrl: './sprints.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, EstadoVacio, Grafico, Progreso, Select, FechaCortaPipe, HorasPipe],
})
export class SprintsProyecto {
  private readonly tableroService = inject(TableroService);

  readonly proyectoId = input.required<string>();

  protected readonly cargando = signal(true);
  protected readonly error = signal(false);
  protected readonly datos = signal<DatosSprints | null>(null);
  protected readonly sprintElegido = signal<string | null>(null);
  protected readonly burndown = signal<BurndownSprint | null>(null);
  protected readonly cargandoBurndown = signal(false);

  protected readonly ETIQUETAS_ESTADO = ETIQUETAS_ESTADO;

  protected readonly opcionesSprint = computed<OpcionSelect[]>(() =>
    (this.datos()?.sprints ?? []).map((s) => ({
      valor: s.id,
      etiqueta: `${s.nombre} · ${ETIQUETAS_ESTADO[s.estado]}`,
    })),
  );

  /** Del más antiguo al más reciente, para leer la velocidad de izquierda a derecha. */
  private readonly cronologicos = computed(() => [...(this.datos()?.sprints ?? [])].reverse());

  protected readonly graficoVelocidad = computed<ChartData>(() => ({
    labels: this.cronologicos().map((s) => s.nombre),
    datasets: [
      {
        label: 'Horas comprometidas',
        data: this.cronologicos().map((s) => s.horas_comprometidas),
        backgroundColor: colorTema('neutro-300'),
      },
      {
        label: 'Horas completadas',
        data: this.cronologicos().map((s) => s.horas_completadas),
        backgroundColor: colorTema('primario-500'),
      },
    ],
  }));

  protected readonly opcionesVelocidad: ChartOptions = {
    scales: { y: { beginAtZero: true, title: { display: true, text: 'Horas' } } },
  };

  protected readonly filasTablaVelocidad = computed(() =>
    this.cronologicos().map((s) => [s.nombre, s.horas_comprometidas, s.horas_completadas]),
  );

  protected readonly graficoBurndown = computed<ChartData>(() => {
    const datos = this.burndown();
    const fechas = datos?.fechas ?? [];
    return {
      labels: fechas.map((f) => `${f.slice(8, 10)}/${f.slice(5, 7)}`),
      datasets: [
        {
          label: 'Ideal',
          data: datos?.ideal ?? [],
          borderColor: colorTema('neutro-400'),
          borderDash: [6, 4],
          pointRadius: 0,
          backgroundColor: 'transparent',
        },
        {
          label: 'Trabajo restante',
          data: datos?.real ?? [],
          borderColor: colorTema('primario-600'),
          backgroundColor: colorTema('primario-600'),
          spanGaps: false,
        },
      ],
    };
  });

  protected readonly opcionesBurndown: ChartOptions = {
    scales: { y: { beginAtZero: true, title: { display: true, text: 'Horas por hacer' } } },
  };

  protected readonly filasTablaBurndown = computed(() => {
    const datos = this.burndown();
    return (datos?.fechas ?? []).map((fecha, i) => [
      fecha,
      datos?.ideal?.[i] ?? 0,
      datos?.real?.[i] ?? '—',
    ]);
  });

  constructor() {
    effect(() => {
      const id = this.proyectoId();
      untracked(() => this.cargar(id));
    });
  }

  private cargar(proyectoId: string): void {
    this.cargando.set(true);
    this.error.set(false);
    this.tableroService.sprintsDelProyecto(proyectoId).subscribe({
      next: (datos) => {
        this.datos.set(datos);
        this.cargando.set(false);
        const inicial = datos.sprints.find((s) => s.estado === 'ACTIVO') ?? datos.sprints[0];
        if (inicial) this.elegirSprint(inicial.id);
      },
      error: () => {
        this.error.set(true);
        this.cargando.set(false);
      },
    });
  }

  protected elegirSprint(sprintId: string | null): void {
    this.sprintElegido.set(sprintId);
    this.burndown.set(null);
    if (!sprintId) return;
    this.cargandoBurndown.set(true);
    this.tableroService.burndownDelSprint(sprintId).subscribe({
      next: (burndown) => {
        this.burndown.set(burndown);
        this.cargandoBurndown.set(false);
      },
      error: () => this.cargandoBurndown.set(false),
    });
  }
}
