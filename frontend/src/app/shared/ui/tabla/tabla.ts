import { NgTemplateOutlet } from '@angular/common';
import { ChangeDetectionStrategy, Component, TemplateRef, computed, input, output } from '@angular/core';

import { RespuestaPaginada } from '../../../core/models';
import { Boton } from '../boton/boton';
import { EstadoVacio } from '../estado-vacio/estado-vacio';

export interface ColumnaTabla<T> {
  clave: string;
  titulo: string;
  ordenable?: boolean;
  plantilla?: TemplateRef<{ $implicit: T }>;
  ancho?: string;
  alinear?: 'izquierda' | 'derecha' | 'centro';
}

export interface CambioOrden {
  clave: string;
  direccion: 'asc' | 'desc';
}

@Component({
  selector: 'app-tabla',
  templateUrl: './tabla.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Boton, EstadoVacio, NgTemplateOutlet],
})
export class Tabla<T extends { id: string }> {
  readonly columnas = input.required<ColumnaTabla<T>[]>();
  readonly filas = input<T[]>([]);
  readonly cargando = input(false);
  readonly respuesta = input<RespuestaPaginada<T> | null>(null);
  readonly pageSize = input(25);
  readonly paginaActual = input(1);
  readonly seleccionable = input(false);
  readonly seleccion = input<readonly string[]>([]);
  readonly ordenActual = input<CambioOrden | null>(null);
  readonly mensajeVacio = input('No hay registros para mostrar.');

  readonly cambioOrden = output<CambioOrden>();
  readonly cambioPagina = output<number>();
  readonly cambioSeleccion = output<string[]>();

  protected readonly filasEsqueleto = [0, 1, 2, 3, 4];

  protected readonly totalPaginas = computed(() => {
    const respuesta = this.respuesta();
    if (!respuesta) return 1;
    return Math.max(1, Math.ceil(respuesta.count / this.pageSize()));
  });

  protected readonly todasSeleccionadas = computed(() => {
    const filas = this.filas();
    return filas.length > 0 && filas.every((fila) => this.seleccion().includes(fila.id));
  });

  protected valorCelda(fila: T, clave: string): unknown {
    return (fila as unknown as Record<string, unknown>)[clave];
  }

  protected alOrdenar(columna: ColumnaTabla<T>): void {
    if (!columna.ordenable) return;
    const actual = this.ordenActual();
    const direccion: 'asc' | 'desc' =
      actual?.clave === columna.clave && actual.direccion === 'asc' ? 'desc' : 'asc';
    this.cambioOrden.emit({ clave: columna.clave, direccion });
  }

  protected alternarFila(id: string): void {
    const actual = this.seleccion();
    const nueva = actual.includes(id) ? actual.filter((x) => x !== id) : [...actual, id];
    this.cambioSeleccion.emit(nueva);
  }

  protected alternarTodas(): void {
    if (this.todasSeleccionadas()) {
      this.cambioSeleccion.emit([]);
    } else {
      this.cambioSeleccion.emit(this.filas().map((fila) => fila.id));
    }
  }

  protected irAPagina(numero: number): void {
    if (numero >= 1 && numero <= this.totalPaginas()) {
      this.cambioPagina.emit(numero);
    }
  }
}
