import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../../environments/environment';
import { MiTrabajo, TareaMiTrabajo } from '../../../core/models';
import { MiTrabajoPagina } from './mi-trabajo';

function tarea(parcial: Partial<TareaMiTrabajo>): TareaMiTrabajo {
  return {
    id: 't',
    codigo: 'T-1',
    clave_jira: null,
    enlace_jira: null,
    nombre: 'Tarea',
    tipo: 'TAREA',
    estado: 'EN_PROGRESO',
    avance: 0,
    horas_estimadas: 10,
    horas_ejecutadas: 4,
    fecha_fin_plan: '2026-12-01',
    vencida: false,
    proyecto_id: 'p1',
    proyecto_codigo: 'P-1',
    proyecto_nombre: 'Portal',
    sprint_nombre: null,
    sprint_activo: false,
    responsable_id: 'r1',
    responsable_nombre: 'Ana',
    ...parcial,
  };
}

const DATOS: MiTrabajo = {
  alcance: 'equipo',
  recurso: null,
  mensaje: '',
  resumen: { total: 4, vencidas: 1, bloqueadas: 1, horas_pendientes: 24 },
  responsables: [
    { id: 'r1', nombre: 'Ana', total: 2 },
    { id: 'r2', nombre: 'Luis', total: 1 },
    { id: null, nombre: 'Sin asignar', total: 1 },
  ],
  tareas: [
    tarea({ id: 'a', proyecto_id: 'p1', responsable_id: 'r1', estado: 'EN_PROGRESO' }),
    tarea({ id: 'b', proyecto_id: 'p2', proyecto_codigo: 'P-2', responsable_id: 'r1', estado: 'BLOQUEADA' }),
    tarea({ id: 'c', proyecto_id: 'p1', responsable_id: 'r2', estado: 'EN_PROGRESO', vencida: true }),
    tarea({ id: 'd', proyecto_id: 'p2', proyecto_codigo: 'P-2', responsable_id: null, responsable_nombre: null, estado: 'PENDIENTE' }),
  ],
};

interface Interno {
  tareas(): TareaMiTrabajo[];
  resumen(): { total: number; vencidas: number; bloqueadas: number; horasPendientes: number };
  opcionesProyecto(): { valor: string; etiqueta: string }[];
  opcionesEstado(): { valor: string; etiqueta: string }[];
  hayFiltros(): boolean;
  proyecto: { set(valor: string | null): void };
  responsable: { set(valor: string | null): void };
  estado: { set(valor: string | null): void };
  limpiarFiltros(): void;
}

describe('MiTrabajoPagina: filtros', () => {
  let pagina: Interno;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    const fixture = TestBed.createComponent(MiTrabajoPagina);
    TestBed.inject(HttpTestingController)
      .expectOne(`${environment.apiBaseUrl}/tablero/mi-trabajo/`)
      .flush(DATOS);
    pagina = fixture.componentInstance as unknown as Interno;
  });

  const ids = () => pagina.tareas().map((t) => t.id);

  it('sin filtros muestra todas las tareas', () => {
    expect(ids()).toEqual(['a', 'b', 'c', 'd']);
    expect(pagina.hayFiltros()).toBe(false);
  });

  it('filtra por proyecto', () => {
    pagina.proyecto.set('p2');
    expect(ids()).toEqual(['b', 'd']);
  });

  it('filtra por responsable, incluidas las tareas sin asignar', () => {
    pagina.responsable.set('r2');
    expect(ids()).toEqual(['c']);
    pagina.responsable.set('sin-asignar');
    expect(ids()).toEqual(['d']);
  });

  it('filtra por estado', () => {
    pagina.estado.set('BLOQUEADA');
    expect(ids()).toEqual(['b']);
  });

  it('combina los tres filtros y las fichas cuadran con la tabla', () => {
    pagina.proyecto.set('p1');
    pagina.responsable.set('r2');
    pagina.estado.set('EN_PROGRESO');

    expect(ids()).toEqual(['c']);
    expect(pagina.resumen()).toEqual({ total: 1, vencidas: 1, bloqueadas: 0, horasPendientes: 6 });
    expect(pagina.hayFiltros()).toBe(true);
  });

  it('limpiar vuelve a mostrar todo', () => {
    pagina.proyecto.set('p1');
    pagina.estado.set('BLOQUEADA');
    expect(ids()).toEqual([]);

    pagina.limpiarFiltros();

    expect(ids()).toEqual(['a', 'b', 'c', 'd']);
  });

  it('las opciones salen de lo que hay: proyectos únicos y solo los estados presentes', () => {
    expect(pagina.opcionesProyecto().map((o) => o.valor)).toEqual(['p1', 'p2']);
    expect(pagina.opcionesEstado().map((o) => o.valor)).toEqual([
      'PENDIENTE',
      'EN_PROGRESO',
      'BLOQUEADA',
    ]);
  });
});
