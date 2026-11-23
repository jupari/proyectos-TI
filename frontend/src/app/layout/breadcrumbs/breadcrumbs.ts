import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { RutaActualService } from '../../core/ui/ruta-actual.service';

interface MigaPan {
  etiqueta: string;
  ruta: string;
}

const ETIQUETAS_SEGMENTO: Record<string, string> = {
  tablero: 'Tablero',
  proyectos: 'Proyectos',
  tareas: 'Tareas',
  ejecucion: 'Ejecución',
  registros: 'Registros',
  aprobaciones: 'Aprobaciones',
  'proyectos-por-periodo': 'Proyectos por periodo',
  'mi-trabajo': 'Mi trabajo',
  seguimientos: 'Seguimientos',
  recursos: 'Recursos',
  asignaciones: 'Asignaciones',
  admin: 'Administración',
  usuarios: 'Usuarios',
  roles: 'Roles',
  catalogos: 'Catálogos',
  perfil: 'Mi perfil',
};

@Component({
  selector: 'app-breadcrumbs',
  templateUrl: './breadcrumbs.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
})
export class Breadcrumbs {
  private readonly ruta = inject(RutaActualService);

  protected readonly migas = computed(() => this.construir(this.ruta.url()));

  private construir(url: string): MigaPan[] {
    const segmentos = url.split('?')[0].split('/').filter(Boolean);
    let acumulado = '';
    return segmentos.map((segmento) => {
      acumulado += `/${segmento}`;
      return { etiqueta: ETIQUETAS_SEGMENTO[segmento] ?? segmento, ruta: acumulado };
    });
  }
}
