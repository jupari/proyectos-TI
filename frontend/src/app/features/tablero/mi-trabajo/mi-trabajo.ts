import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ETIQUETAS_ESTADO_TAREA, EstadoTarea, MiTrabajo } from '../../../core/models';
import { FechaCortaPipe, HorasPipe } from '../../../shared/pipes';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { FichaResumen } from '../../../shared/ui/ficha-resumen/ficha-resumen';
import { Boton } from '../../../shared/ui/boton/boton';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { TableroService } from '../data/tablero.service';

/** «Mi trabajo»: las tareas abiertas del recurso ligado al usuario. Es de solo
 * lectura: el equipo actualiza sus tareas en Jira y aquí se consultan, con las
 * del sprint activo primero. */
@Component({
  selector: 'app-mi-trabajo',
  templateUrl: './mi-trabajo.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Boton,
    EstadoVacio,
    FichaResumen,
    Progreso,
    Select,
    FechaCortaPipe,
    HorasPipe,
  ],
})
export class MiTrabajoPagina {
  private readonly tableroService = inject(TableroService);

  protected readonly cargando = signal(true);
  protected readonly error = signal(false);
  protected readonly datos = signal<MiTrabajo | null>(null);
  /** Filtros combinables; `null` es «todos». */
  protected readonly proyecto = signal<string | null>(null);
  /** Solo administrador: un id de recurso o `'sin-asignar'`. */
  protected readonly responsable = signal<string | null>(null);
  protected readonly estado = signal<string | null>(null);

  protected readonly opcionesProyecto = computed<OpcionSelect[]>(() => {
    const porId = new Map<string, string>();
    for (const t of this.datos()?.tareas ?? []) {
      porId.set(t.proyecto_id, `${t.proyecto_codigo} — ${t.proyecto_nombre}`);
    }
    return [...porId.entries()]
      .map(([valor, etiqueta]) => ({ valor, etiqueta }))
      .sort((a, b) => a.etiqueta.localeCompare(b.etiqueta, 'es'));
  });

  /** Solo los estados que de verdad tienen tareas, en el orden del ciclo de vida. */
  protected readonly opcionesEstado = computed<OpcionSelect[]>(() => {
    const presentes = new Set((this.datos()?.tareas ?? []).map((t) => t.estado));
    return (Object.keys(ETIQUETAS_ESTADO_TAREA) as EstadoTarea[])
      .filter((estado) => presentes.has(estado))
      .map((estado) => ({ valor: estado, etiqueta: ETIQUETAS_ESTADO_TAREA[estado] }));
  });

  protected readonly hayFiltros = computed(
    () => !!(this.proyecto() || this.responsable() || this.estado()),
  );

  protected readonly opcionesResponsable = computed<OpcionSelect[]>(() =>
    (this.datos()?.responsables ?? []).map((r) => ({
      valor: r.id ?? 'sin-asignar',
      etiqueta: `${r.nombre} (${r.total})`,
    })),
  );

  protected readonly tareas = computed(() => {
    const proyecto = this.proyecto();
    const responsable = this.responsable();
    const estado = this.estado();
    return (this.datos()?.tareas ?? []).filter(
      (t) =>
        (!proyecto || t.proyecto_id === proyecto) &&
        (!responsable || (t.responsable_id ?? 'sin-asignar') === responsable) &&
        (!estado || t.estado === estado),
    );
  });

  /** Se recalcula con el filtro para que las fichas siempre cuadren con la tabla. */
  protected readonly resumen = computed(() => {
    const filas = this.tareas();
    return {
      total: filas.length,
      vencidas: filas.filter((t) => t.vencida).length,
      bloqueadas: filas.filter((t) => t.estado === 'BLOQUEADA').length,
      horasPendientes: filas.reduce(
        (suma, t) => suma + Math.max(t.horas_estimadas - t.horas_ejecutadas, 0),
        0,
      ),
    };
  });

  constructor() {
    this.tableroService.miTrabajo().subscribe({
      next: (datos) => {
        this.datos.set(datos);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set(true);
        this.cargando.set(false);
      },
    });
  }

  protected limpiarFiltros(): void {
    this.proyecto.set(null);
    this.responsable.set(null);
    this.estado.set(null);
  }

  protected etiquetaEstado(estado: string): string {
    return ETIQUETAS_ESTADO_TAREA[estado as EstadoTarea] ?? estado;
  }
}
