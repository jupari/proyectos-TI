import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../../environments/environment';
import { RecursosService } from './recursos.service';

describe('RecursosService', () => {
  let servicio: RecursosService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    servicio = TestBed.inject(RecursosService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('listarRecursos pasa los filtros como query params', () => {
    servicio.listarRecursos({ tipo: 'INTERNO', sin_asignacion: true }).subscribe();

    const peticion = httpMock.expectOne(
      (r) =>
        r.url === `${environment.apiBaseUrl}/recursos/` &&
        r.params.get('tipo') === 'INTERNO' &&
        r.params.get('sin_asignacion') === 'true',
    );
    peticion.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('carga pasa desde y hasta como query params al sub-recurso', () => {
    servicio.carga('abc-123', '2026-02-01', '2026-03-31').subscribe();

    const peticion = httpMock.expectOne(
      (r) =>
        r.url === `${environment.apiBaseUrl}/recursos/abc-123/carga/` &&
        r.params.get('desde') === '2026-02-01' &&
        r.params.get('hasta') === '2026-03-31',
    );
    expect(peticion.request.method).toBe('GET');
    peticion.flush([]);
  });

  it('tarifas consulta el sub-recurso de solo lectura con GET', () => {
    servicio.tarifas('abc-123').subscribe();

    const peticion = httpMock.expectOne(`${environment.apiBaseUrl}/recursos/abc-123/tarifas/`);
    expect(peticion.request.method).toBe('GET');
    peticion.flush([]);
  });
});
