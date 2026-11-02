import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { UrlTree, provideRouter } from '@angular/router';

import { UsuarioActual } from '../models';
import { AuthService } from '../auth/auth.service';
import { autenticadoGuard } from './autenticado.guard';
import { cambioClaveGuard } from './cambio-clave.guard';
import { permisoGuard } from './permiso.guard';
import { rolGuard } from './rol.guard';

const USUARIO_BASE: UsuarioActual = {
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

describe('guards', () => {
  let auth: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    auth = TestBed.inject(AuthService);
  });

  describe('autenticadoGuard', () => {
    it('permite el paso si hay sesión', () => {
      auth.usuario.set(USUARIO_BASE);
      const resultado = TestBed.runInInjectionContext(() =>
        autenticadoGuard({} as never, { url: '/x' } as never),
      );
      expect(resultado).toBe(true);
    });

    it('redirige a /auth/login con returnUrl si no hay sesión', () => {
      const resultado = TestBed.runInInjectionContext(() =>
        autenticadoGuard({} as never, { url: '/proyectos' } as never),
      );
      expect(resultado).not.toBe(true);
      const arbol = resultado as UrlTree;
      expect(arbol.toString()).toContain('/auth/login');
      expect(arbol.toString()).toContain('returnUrl');
    });
  });

  describe('rolGuard', () => {
    it('permite el paso si el usuario tiene uno de los roles pedidos', () => {
      auth.usuario.set(USUARIO_BASE);
      const guardia = rolGuard(['ADMIN', 'LIDER']);
      const resultado = TestBed.runInInjectionContext(() => guardia({} as never, {} as never));
      expect(resultado).toBe(true);
    });

    it('redirige a /403 si el usuario no tiene ninguno de los roles pedidos', () => {
      auth.usuario.set(USUARIO_BASE);
      const guardia = rolGuard(['ADMIN']);
      const resultado = TestBed.runInInjectionContext(() => guardia({} as never, {} as never));
      expect((resultado as UrlTree).toString()).toBe('/403');
    });
  });

  describe('permisoGuard', () => {
    it('permite el paso si el usuario tiene el permiso', () => {
      auth.usuario.set(USUARIO_BASE);
      const guardia = permisoGuard('proyectos.ver');
      const resultado = TestBed.runInInjectionContext(() => guardia({} as never, {} as never));
      expect(resultado).toBe(true);
    });

    it('redirige a /403 si el usuario no tiene el permiso', () => {
      auth.usuario.set(USUARIO_BASE);
      const guardia = permisoGuard('admin.usuarios');
      const resultado = TestBed.runInInjectionContext(() => guardia({} as never, {} as never));
      expect((resultado as UrlTree).toString()).toBe('/403');
    });
  });

  describe('cambioClaveGuard', () => {
    it('deja pasar si no debe cambiar la clave', () => {
      auth.usuario.set({ ...USUARIO_BASE, debe_cambiar_clave: false });
      const resultado = TestBed.runInInjectionContext(() =>
        cambioClaveGuard({} as never, { url: '/tablero' } as never),
      );
      expect(resultado).toBe(true);
    });

    it('fuerza /auth/cambiar-clave si debe_cambiar_clave es true', () => {
      auth.usuario.set({ ...USUARIO_BASE, debe_cambiar_clave: true });
      const resultado = TestBed.runInInjectionContext(() =>
        cambioClaveGuard({} as never, { url: '/tablero' } as never),
      );
      expect((resultado as UrlTree).toString()).toBe('/auth/cambiar-clave');
    });

    it('no redirige en bucle si ya está en /auth/cambiar-clave', () => {
      auth.usuario.set({ ...USUARIO_BASE, debe_cambiar_clave: true });
      const resultado = TestBed.runInInjectionContext(() =>
        cambioClaveGuard({} as never, { url: '/auth/cambiar-clave' } as never),
      );
      expect(resultado).toBe(true);
    });
  });
});
