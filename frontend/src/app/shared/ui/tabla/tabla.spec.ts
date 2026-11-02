import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { RespuestaPaginada } from '../../../core/models';
import { CambioOrden, ColumnaTabla, Tabla } from './tabla';

interface FilaPrueba {
  id: string;
  nombre: string;
}

@Component({
  template: `
    <app-tabla
      [columnas]="columnas"
      [filas]="filas"
      [cargando]="cargando"
      [respuesta]="respuesta"
      [ordenActual]="ordenActual"
      (cambioOrden)="ordenRecibido = $event"
      (cambioPagina)="paginaRecibida = $event"
    />
  `,
  imports: [Tabla],
})
class AnfitrionPrueba {
  columnas: ColumnaTabla<FilaPrueba>[] = [{ clave: 'nombre', titulo: 'Nombre', ordenable: true }];
  filas: FilaPrueba[] = [];
  cargando = false;
  respuesta: RespuestaPaginada<FilaPrueba> | null = null;
  ordenActual: CambioOrden | null = null;
  ordenRecibido: CambioOrden | null = null;
  paginaRecibida: number | null = null;
}

describe('Tabla', () => {
  let fixture: ComponentFixture<AnfitrionPrueba>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [AnfitrionPrueba] });
    fixture = TestBed.createComponent(AnfitrionPrueba);
  });

  it('muestra el estado vacío cuando no hay filas y no está cargando', () => {
    fixture.detectChanges();
    const vacio = fixture.debugElement.query(By.css('app-estado-vacio'));
    expect(vacio).not.toBeNull();
  });

  it('pinta una fila por cada elemento de filas', () => {
    fixture.componentInstance.filas = [
      { id: '1', nombre: 'Uno' },
      { id: '2', nombre: 'Dos' },
    ];
    fixture.detectChanges();

    const filas = fixture.debugElement.queryAll(By.css('tbody tr'));
    expect(filas.length).toBe(2);
    expect(filas[0].nativeElement.textContent).toContain('Uno');
    expect(filas[1].nativeElement.textContent).toContain('Dos');
  });

  it('al hacer clic en una columna ordenable sin orden previo, emite dirección asc', () => {
    fixture.componentInstance.filas = [{ id: '1', nombre: 'Uno' }];
    fixture.detectChanges();

    const encabezado = fixture.debugElement.query(By.css('thead button'));
    encabezado.nativeElement.click();

    expect(fixture.componentInstance.ordenRecibido).toEqual({ clave: 'nombre', direccion: 'asc' });
  });

  it('al hacer clic en una columna ya ordenada asc, emite dirección desc', () => {
    fixture.componentInstance.filas = [{ id: '1', nombre: 'Uno' }];
    fixture.componentInstance.ordenActual = { clave: 'nombre', direccion: 'asc' };
    fixture.detectChanges();

    const encabezado = fixture.debugElement.query(By.css('thead button'));
    encabezado.nativeElement.click();

    expect(fixture.componentInstance.ordenRecibido).toEqual({ clave: 'nombre', direccion: 'desc' });
  });

  it('muestra el conteo y la paginación conectados a RespuestaPaginada', () => {
    fixture.componentInstance.filas = [{ id: '1', nombre: 'Uno' }];
    fixture.componentInstance.respuesta = { count: 60, next: null, previous: null, results: [] };
    fixture.detectChanges();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('60 registro(s)');
    expect(texto).toContain('página 1 de 3');

    const botones = fixture.debugElement.queryAll(By.css('app-boton button'));
    const siguiente = botones.find((b) => b.nativeElement.textContent.includes('Siguiente'))!;
    siguiente.nativeElement.click();

    expect(fixture.componentInstance.paginaRecibida).toBe(2);
  });

  it('muestra filas de esqueleto mientras cargando es true', () => {
    fixture.componentInstance.cargando = true;
    fixture.detectChanges();

    const vacio = fixture.debugElement.query(By.css('app-estado-vacio'));
    expect(vacio).toBeNull();
    const esqueletos = fixture.debugElement.queryAll(By.css('tbody .animate-pulse'));
    expect(esqueletos.length).toBeGreaterThan(0);
  });
});
