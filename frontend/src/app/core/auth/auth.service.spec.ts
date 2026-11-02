import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { UsuarioActual } from '../models';
import { AuthService } from './auth.service';

/** Deja correr los microtasks pendientes (p. ej. la continuación de un
 * `await firstValueFrom(...)` tras un `flush()` síncrono de HttpTestingController). */
const esperarMicrotareas = () => new Promise((resolve) => setTimeout(resolve, 0));

const USUARIO_DEMO: UsuarioActual = {
  id: '1',
  email: 'lider@demo.local',
  nombres: 'Laura',
  apellidos: 'Idárraga',
  cargo: '',
  telefono: '',
  avatar_url: null,
  proveedor_auth: 'LOCAL',
  debe_cambiar_clave: false,
  roles: ['LIDER'],
  permisos_ui: ['proyectos.ver'],
  proyectos_liderados: [],
};

describe('AuthService', () => {
  let servicio: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    servicio = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('login guarda los tokens y carga el usuario', async () => {
    const promesa = servicio.login('lider@demo.local', 'demo12345');

    const peticionLogin = httpMock.expectOne(`${environment.apiBaseUrl}/auth/login/`);
    expect(peticionLogin.request.body).toEqual({ email: 'lider@demo.local', password: 'demo12345' });
    peticionLogin.flush({ access: 'token-acceso', refresh: 'token-refresco', usuario: USUARIO_DEMO });
    await esperarMicrotareas();

    const peticionYo = httpMock.expectOne(`${environment.apiBaseUrl}/auth/yo/`);
    peticionYo.flush(USUARIO_DEMO);

    await promesa;

    expect(servicio.obtenerAccessToken()).toBe('token-acceso');
    expect(servicio.obtenerRefreshToken()).toBe('token-refresco');
    expect(servicio.autenticado()).toBe(true);
    expect(servicio.usuario()?.email).toBe('lider@demo.local');
  });

  it('refrescar reemplaza ambos tokens', async () => {
    localStorage.setItem('sp_refresh', 'refresco-viejo');

    const promesa = servicio.refrescar();
    const peticion = httpMock.expectOne(`${environment.apiBaseUrl}/auth/refresh/`);
    expect(peticion.request.body).toEqual({ refresh: 'refresco-viejo' });
    peticion.flush({ access: 'nuevo-acceso', refresh: 'nuevo-refresco' });

    const token = await promesa;

    expect(token).toBe('nuevo-acceso');
    expect(servicio.obtenerAccessToken()).toBe('nuevo-acceso');
    expect(servicio.obtenerRefreshToken()).toBe('nuevo-refresco');
  });

  it('refrescar sin refresh token guardado lanza sin llamar a la API', async () => {
    await expect(servicio.refrescar()).rejects.toBeTruthy();
    httpMock.expectNone(`${environment.apiBaseUrl}/auth/refresh/`);
  });

  it('logout pone el refresh en la blacklist y limpia la sesión', async () => {
    localStorage.setItem('sp_access', 'token-acceso');
    localStorage.setItem('sp_refresh', 'token-refresco');

    const promesa = servicio.logout();
    const peticion = httpMock.expectOne(`${environment.apiBaseUrl}/auth/logout/`);
    expect(peticion.request.body).toEqual({ refresh: 'token-refresco' });
    peticion.flush(null);

    await promesa;

    expect(servicio.obtenerAccessToken()).toBeNull();
    expect(servicio.obtenerRefreshToken()).toBeNull();
    expect(servicio.autenticado()).toBe(false);
  });

  it('logout limpia la sesión incluso si la petición al backend falla', async () => {
    localStorage.setItem('sp_access', 'token-acceso');
    localStorage.setItem('sp_refresh', 'token-refresco');

    const promesa = servicio.logout();
    const peticion = httpMock.expectOne(`${environment.apiBaseUrl}/auth/logout/`);
    peticion.flush({ error: { codigo: 'ERROR_INTERNO' } }, { status: 500, statusText: 'Error' });

    await expect(promesa).rejects.toBeTruthy();
    expect(servicio.obtenerAccessToken()).toBeNull();
    expect(servicio.obtenerRefreshToken()).toBeNull();
  });
});
