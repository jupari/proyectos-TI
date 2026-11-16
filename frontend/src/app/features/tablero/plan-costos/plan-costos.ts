import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { PlanCostosProyecto, ValoresPlanCostosMes } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { ProyectosService } from '../../proyectos/data/proyectos.service';
import { HorasPipe, MonedaPipe } from '../../../shared/pipes';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { TableroService } from '../data/tablero.service';
import { sincronizarQueryParams } from '../../../core/ui/query-params';

type Vista = 'plan' | 'ejecutado';

const MESES_CORTOS = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
];

function formatoMes(claveIso: string): string {
  const [anio, mes] = claveIso.split('-');
  return `${MESES_CORTOS[Number(mes) - 1]} ${anio}`;
}

/** Plan de costos de UN proyecto (fase 15): costo planeado vs. ejecutado,
 * mes a mes, en un bloque "Personal" (horas + valor) y un bloque por cada
 * categoría de rubro con datos (solo valor). Inspirado en una plantilla de
 * flujo de pagos que compartió el usuario, generalizada a las categorías
 * reales de `RubroPresupuesto` en vez de las 3-4 fijas de esa plantilla. */
@Component({
  selector: 'app-plan-costos-tablero',
  templateUrl: './plan-costos.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, EstadoVacio, Select, RouterLink, HorasPipe, MonedaPipe],
})
export class PlanCostosTablero {
  private readonly tableroService = inject(TableroService);
  private readonly proyectosService = inject(ProyectosService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected readonly opcionesProyectos = signal<OpcionSelect[]>([]);
  protected readonly proyectoId = signal<string | null>(null);
  protected readonly vista = signal<Vista>('plan');

  protected readonly cargando = signal(false);
  protected readonly error = signal(false);
  protected readonly exportando = signal(false);
  protected readonly datos = signal<PlanCostosProyecto | null>(null);

  protected readonly opcionesVista: OpcionSelect[] = [
    { valor: 'plan', etiqueta: 'Planeado' },
    { valor: 'ejecutado', etiqueta: 'Ejecutado' },
  ];

  protected readonly meses = computed(() => this.datos()?.meses ?? []);
  protected readonly totalColumnas = computed(() => 3 + this.meses().length * 2 + 2);
  protected readonly formatoMes = formatoMes;

  constructor() {
    this.proyectosService.listarProyectos({ page_size: 200 }).subscribe((r) => {
      this.opcionesProyectos.set(
        r.results.map((p) => ({ valor: p.id, etiqueta: `${p.codigo} — ${p.nombre}` })),
      );
    });

    const proyectoUrl = this.ruta.snapshot.queryParamMap.get('proyecto');
    if (proyectoUrl) {
      this.proyectoId.set(proyectoUrl);
      this.cargar();
    }
  }

  protected alCambiarProyecto(id: string | null): void {
    this.proyectoId.set(id);
    sincronizarQueryParams(this.router, this.ruta, { proyecto: id });
    if (id) this.cargar();
  }

  protected horasDe(valores: ValoresPlanCostosMes): number | undefined {
    return this.vista() === 'plan' ? valores.horas_plan : valores.horas_ejec;
  }

  protected valorDe(valores: ValoresPlanCostosMes): number {
    return this.vista() === 'plan' ? valores.valor_plan : valores.valor_ejec;
  }

  protected cargar(refrescar = false): void {
    const proyecto = this.proyectoId();
    if (!proyecto) return;
    this.cargando.set(true);
    this.error.set(false);
    this.tableroService.planCostos({ proyecto, refrescar: refrescar || undefined }).subscribe({
      next: (respuesta) => {
        this.datos.set(respuesta);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set(true);
        this.cargando.set(false);
      },
    });
  }

  protected exportarCsv(): void {
    const proyecto = this.proyectoId();
    if (!proyecto) return;
    this.exportando.set(true);
    this.tableroService.exportarCsv('plan-costos', { proyecto }).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = 'tablero-plan-costos.csv';
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
