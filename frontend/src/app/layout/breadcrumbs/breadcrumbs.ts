import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter } from 'rxjs';

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
  private readonly router = inject(Router);

  protected readonly migas = signal<MigaPan[]>(this.construir(this.router.url));

  constructor() {
    this.router.events.pipe(filter((evento) => evento instanceof NavigationEnd)).subscribe(() => {
      this.migas.set(this.construir(this.router.url));
    });
  }

  private construir(url: string): MigaPan[] {
    const segmentos = url.split('?')[0].split('/').filter(Boolean);
    let acumulado = '';
    return segmentos.map((segmento) => {
      acumulado += `/${segmento}`;
      return { etiqueta: ETIQUETAS_SEGMENTO[segmento] ?? segmento, ruta: acumulado };
    });
  }
}
