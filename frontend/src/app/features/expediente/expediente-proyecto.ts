import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { PanelExpediente } from './panel/panel-expediente';

/** Envoltura delgada para la ruta `/proyectos/:id/expediente`: lee el id
 * de la ruta y delega todo en `PanelExpediente`, el mismo componente que
 * usa la pestaña "Expediente" del detalle de proyecto. */
@Component({
  selector: 'app-expediente-proyecto',
  template: `
    <div class="flex flex-col gap-4">
      <a [routerLink]="['/proyectos', id]" class="text-sm text-teal-700 hover:underline">
        ← Volver al proyecto
      </a>
      <app-panel-expediente [proyectoId]="id" />
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, PanelExpediente],
})
export class ExpedienteProyecto {
  private readonly ruta = inject(ActivatedRoute);
  protected readonly id = this.ruta.snapshot.paramMap.get('id')!;
}
