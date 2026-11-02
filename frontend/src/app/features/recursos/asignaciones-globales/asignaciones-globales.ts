import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AsignacionRecurso, RespuestaPaginada } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { FechaCortaPipe, MonedaPipe, PorcentajePipe } from '../../../shared/pipes';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Tabla } from '../../../shared/ui/tabla/tabla';
import { ProyectosService } from '../../proyectos/data/proyectos.service';
import { AsignacionesService } from '../data/asignaciones.service';
import { RecursosService } from '../data/recursos.service';

@Component({
  selector: 'app-asignaciones-globales',
  templateUrl: './asignaciones-globales.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Select, Tabla, FechaCortaPipe, MonedaPipe, PorcentajePipe],
})
export class AsignacionesGlobales {
  private readonly asignacionesService = inject(AsignacionesService);
  private readonly recursosService = inject(RecursosService);
  private readonly proyectosService = inject(ProyectosService);
  private readonly toast = inject(ToastService);

  protected readonly cargando = signal(false);
  protected readonly respuesta = signal<RespuestaPaginada<AsignacionRecurso> | null>(null);

  protected readonly recurso = signal<string | null>(null);
  protected readonly proyecto = signal<string | null>(null);

  protected readonly opcionesRecursos = signal<OpcionSelect[]>([]);
  protected readonly opcionesProyectos = signal<OpcionSelect[]>([]);

  constructor() {
    this.recursosService
      .listarRecursos({ page_size: 200 })
      .subscribe((r) => this.opcionesRecursos.set(r.results.map((x) => ({ valor: x.id, etiqueta: x.nombre }))));
    this.proyectosService
      .listarProyectos({ page_size: 200 })
      .subscribe((r) =>
        this.opcionesProyectos.set(r.results.map((p) => ({ valor: p.id, etiqueta: `${p.codigo} — ${p.nombre}` }))),
      );
    this.cargar();
  }

  protected nombreRecurso(id: string): string {
    return this.opcionesRecursos().find((o) => o.valor === id)?.etiqueta ?? id;
  }

  protected nombreProyecto(id: string): string {
    return this.opcionesProyectos().find((o) => o.valor === id)?.etiqueta ?? id;
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.asignacionesService
      .listar({ recurso: this.recurso() ?? undefined, proyecto: this.proyecto() ?? undefined })
      .subscribe({
        next: (respuesta) => {
          this.respuesta.set(respuesta);
          this.cargando.set(false);
        },
        error: () => {
          this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar las asignaciones.' });
          this.cargando.set(false);
        },
      });
  }
}
