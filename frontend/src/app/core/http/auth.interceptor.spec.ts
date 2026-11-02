import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { authInterceptor } from './auth.interceptor';

/** Deja correr los microtasks pendientes entre un `flush()` y la
 * continuación de la cadena de promesas que dispara (p. ej. el reintento
 * tras refrescar el token). */
const esperarMicrotareas = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('añade el header Authorization cuando hay un access token', () => {
    localStorage.setItem('sp_access', 'token-de-prueba');

    http.get('/api/v1/algo/').subscribe();

    const peticion = httpMock.expectOne('/api/v1/algo/');
    expect(peticion.request.headers.get('Authorization')).toBe('Bearer token-de-prueba');
    peticion.flush({});
  });

  it('no añade Authorization a /auth/login/ (ruta pública)', () => {
    localStorage.setItem('sp_access', 'token-de-prueba');

    http.post(`${environment.apiBaseUrl}/auth/login/`, {}).subscribe();

    const peticion = httpMock.expectOne(`${environment.apiBaseUrl}/auth/login/`);
    expect(peticion.request.headers.get('Authorization')).toBeNull();
    peticion.flush({});
  });

  it('ante dos 401 concurrentes, solo refresca una vez y reintenta ambas peticiones', async () => {
    localStorage.setItem('sp_access', 'token-vencido');
    localStorage.setItem('sp_refresh', 'token-refresco');

    let resultadoUno: unknown;
    let resultadoDos: unknown;
    http.get('/api/v1/uno/').subscribe((r) => (resultadoUno = r));
    http.get('/api/v1/dos/').subscribe((r) => (resultadoDos = r));

    httpMock.expectOne('/api/v1/uno/').flush({}, { status: 401, statusText: 'Unauthorized' });
    httpMock.expectOne('/api/v1/dos/').flush({}, { status: 401, statusText: 'Unauthorized' });

    const peticionRefresh = httpMock.expectOne(`${environment.apiBaseUrl}/auth/refresh/`);
    peticionRefresh.flush({ access: 'token-nuevo', refresh: 'token-refresco-nuevo' });
    await esperarMicrotareas();

    const reintentoUno = httpMock.expectOne('/api/v1/uno/');
    const reintentoDos = httpMock.expectOne('/api/v1/dos/');
    expect(reintentoUno.request.headers.get('Authorization')).toBe('Bearer token-nuevo');
    expect(reintentoDos.request.headers.get('Authorization')).toBe('Bearer token-nuevo');
    reintentoUno.flush({ ok: 1 });
    reintentoDos.flush({ ok: 2 });

    expect(resultadoUno).toEqual({ ok: 1 });
    expect(resultadoDos).toEqual({ ok: 2 });
    // Un solo refresh para las dos peticiones: no debe quedar ninguno pendiente.
    httpMock.expectNone(`${environment.apiBaseUrl}/auth/refresh/`);
  });

  it('si el refresh falla, no reintenta en bucle (una sola llamada a /auth/refresh/)', async () => {
    localStorage.setItem('sp_access', 'token-vencido');
    localStorage.setItem('sp_refresh', 'token-refresco');

    let error: unknown;
    http.get('/api/v1/algo/').subscribe({ error: (e: unknown) => (error = e) });

    httpMock.expectOne('/api/v1/algo/').flush({}, { status: 401, statusText: 'Unauthorized' });
    httpMock
      .expectOne(`${environment.apiBaseUrl}/auth/refresh/`)
      .flush({}, { status: 401, statusText: 'Unauthorized' });
    await esperarMicrotareas();

    expect(error).toBeTruthy();
    expect(localStorage.getItem('sp_access')).toBeNull();
    expect(localStorage.getItem('sp_refresh')).toBeNull();
    httpMock.expectNone(`${environment.apiBaseUrl}/auth/refresh/`);
  });
});
