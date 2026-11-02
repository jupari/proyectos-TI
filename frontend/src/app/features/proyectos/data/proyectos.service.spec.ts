import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../../environments/environment';
import { ProyectosService } from './proyectos.service';

describe('ProyectosService', () => {
  let servicio: ProyectosService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    servicio = TestBed.inject(ProyectosService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('listarProyectos pasa los filtros como query params', () => {
    servicio.listarProyectos({ estado: 'EJECUCION', mis_proyectos: true }).subscribe();

    const peticion = httpMock.expectOne(
      (r) =>
        r.url === `${environment.apiBaseUrl}/proyectos/` &&
        r.params.get('estado') === 'EJECUCION' &&
        r.params.get('mis_proyectos') === 'true',
    );
    peticion.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('cambiarEstado llama al endpoint de la acción con el cuerpo esperado', () => {
    servicio.cambiarEstado('abc-123', 'PLANEACION', 'listo').subscribe();

    const peticion = httpMock.expectOne(
      `${environment.apiBaseUrl}/proyectos/abc-123/cambiar-estado/`,
    );
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({ estado: 'PLANEACION', observacion: 'listo' });
    peticion.flush({});
  });

  it('fases consulta el sub-recurso de solo lectura con GET', () => {
    servicio.fases('abc-123').subscribe();

    const peticion = httpMock.expectOne(`${environment.apiBaseUrl}/proyectos/abc-123/fases/`);
    expect(peticion.request.method).toBe('GET');
    peticion.flush([]);
  });
});
