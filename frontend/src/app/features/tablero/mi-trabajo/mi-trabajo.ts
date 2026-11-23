import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ETIQUETAS_ESTADO_TAREA, EstadoTarea, MiTrabajo } from '../../../core/models';
import { FechaCortaPipe, HorasPipe } from '../../../shared/pipes';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { FichaResumen } from '../../../shared/ui/ficha-resumen/ficha-resumen';
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
  /** Filtro por responsable (solo administrador): vacío todos, `'sin-asignar'` o un id. */
  protected readonly responsable = signal<string | null>(null);

  protected readonly opcionesResponsable = computed<OpcionSelect[]>(() =>
    (this.datos()?.responsables ?? []).map((r) => ({
      valor: r.id ?? 'sin-asignar',
      etiqueta: `${r.nombre} (${r.total})`,
    })),
  );

  protected readonly tareas = computed(() => {
    const filtro = this.responsable();
    const todas = this.datos()?.tareas ?? [];
    if (!filtro) return todas;
    return todas.filter((t) => (t.responsable_id ?? 'sin-asignar') === filtro);
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

  protected etiquetaEstado(estado: string): string {
    return ETIQUETAS_ESTADO_TAREA[estado as EstadoTarea] ?? estado;
  }
}
