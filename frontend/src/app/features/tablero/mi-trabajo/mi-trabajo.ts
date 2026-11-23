import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ETIQUETAS_ESTADO_TAREA, EstadoTarea, MiTrabajo } from '../../../core/models';
import { FechaCortaPipe, HorasPipe } from '../../../shared/pipes';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { FichaResumen } from '../../../shared/ui/ficha-resumen/ficha-resumen';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { TableroService } from '../data/tablero.service';

/** «Mi trabajo»: las tareas abiertas del recurso ligado al usuario. Es de solo
 * lectura: el equipo actualiza sus tareas en Jira y aquí se consultan, con las
 * del sprint activo primero. */
@Component({
  selector: 'app-mi-trabajo',
  templateUrl: './mi-trabajo.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, EstadoVacio, FichaResumen, Progreso, FechaCortaPipe, HorasPipe],
})
export class MiTrabajoPagina {
  private readonly tableroService = inject(TableroService);

  protected readonly cargando = signal(true);
  protected readonly error = signal(false);
  protected readonly datos = signal<MiTrabajo | null>(null);

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
