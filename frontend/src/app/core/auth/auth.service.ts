import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { RespuestaLogin, RespuestaSolicitarCodigo, UsuarioActual } from '../models';
import {
  calcularCodeChallenge,
  generarCodeVerifier,
  guardarIntentoGoogle,
  leerIntentoGoogle,
  limpiarIntentoGoogle,
} from './google';

const CLAVE_ACCESS = 'sp_access';
const CLAVE_REFRESH = 'sp_refresh';

interface RespuestaAutorizarGoogle {
  url_autorizacion: string;
  state: string;
}

interface RespuestaRefresh {
  access: string;
  refresh: string;
}

/**
 * Estado de sesión con signals. Los tokens viven en `localStorage`
 * (`sp_access`/`sp_refresh`); `restaurarSesion()` los usa al arrancar la app
 * para recuperar la sesión antes de pintar las rutas protegidas.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  readonly usuario = signal<UsuarioActual | null>(null);
  readonly cargando = signal(false);
  readonly autenticado = computed(() => this.usuario() !== null);

  obtenerAccessToken(): string | null {
    return localStorage.getItem(CLAVE_ACCESS);
  }

  obtenerRefreshToken(): string | null {
    return localStorage.getItem(CLAVE_REFRESH);
  }

  private guardarTokens(access: string, refresh: string): void {
    localStorage.setItem(CLAVE_ACCESS, access);
    localStorage.setItem(CLAVE_REFRESH, refresh);
  }

  private limpiarTokens(): void {
    localStorage.removeItem(CLAVE_ACCESS);
    localStorage.removeItem(CLAVE_REFRESH);
  }

  /** Paso 1 del login local (fase 13): valida email+clave y devuelve el
   * `login_token` del código que se acaba de enviar por correo. No guarda
   * tokens todavía — eso lo hace `verificarCodigo`. */
  async solicitarCodigo(email: string, clave: string): Promise<string> {
    this.cargando.set(true);
    try {
      const respuesta = await firstValueFrom(
        this.http.post<RespuestaSolicitarCodigo>(`${this.base}/auth/login/`, {
          email,
          password: clave,
        }),
      );
      return respuesta.login_token;
    } finally {
      this.cargando.set(false);
    }
  }

  /** Paso 2: confirma el código recibido por correo y recién ahí abre la sesión. */
  async verificarCodigo(loginToken: string, codigo: string): Promise<void> {
    this.cargando.set(true);
    try {
      const respuesta = await firstValueFrom(
        this.http.post<RespuestaLogin>(`${this.base}/auth/verificar-codigo/`, {
          login_token: loginToken,
          codigo,
        }),
      );
      this.guardarTokens(respuesta.access, respuesta.refresh);
      await this.cargarUsuario();
    } finally {
      this.cargando.set(false);
    }
  }

  async reenviarCodigo(loginToken: string): Promise<void> {
    await firstValueFrom(
      this.http.post(`${this.base}/auth/reenviar-codigo/`, { login_token: loginToken }),
    );
  }

  /** Para que el botón "Continuar con Google" se oculte si el backend
   * responde 503 (sin credenciales configuradas), sin iniciar el flujo real. */
  async googleDisponible(): Promise<boolean> {
    try {
      await firstValueFrom(
        this.http.get(`${this.base}/auth/google/autorizar/`, {
          params: { code_challenge: 'verificacion-disponibilidad' },
        }),
      );
      return true;
    } catch (error) {
      if (error instanceof HttpErrorResponse && error.status === 503) {
        return false;
      }
      return true;
    }
  }

  /** Devuelve la URL de Google a la que redirigir, o lanza si el flujo no está configurado. */
  async loginGoogle(returnUrl: string): Promise<string> {
    const codeVerifier = generarCodeVerifier();
    const codeChallenge = await calcularCodeChallenge(codeVerifier);
    const respuesta = await firstValueFrom(
      this.http.get<RespuestaAutorizarGoogle>(`${this.base}/auth/google/autorizar/`, {
        params: { code_challenge: codeChallenge },
      }),
    );
    guardarIntentoGoogle(codeVerifier, respuesta.state, returnUrl);
    return respuesta.url_autorizacion;
  }

  /** Devuelve a dónde navegar tras completar el login con Google. */
  async completarLoginGoogle(code: string, state: string): Promise<string> {
    const intento = leerIntentoGoogle();
    if (!intento.codeVerifier || !intento.state || intento.state !== state) {
      limpiarIntentoGoogle();
      throw new Error('La sesión de inicio con Google venció o no es válida.');
    }

    const respuesta = await firstValueFrom(
      this.http.post<RespuestaLogin>(`${this.base}/auth/google/callback/`, {
        code,
        state,
        code_verifier: intento.codeVerifier,
      }),
    );
    this.guardarTokens(respuesta.access, respuesta.refresh);
    await this.cargarUsuario();

    const returnUrl = intento.returnUrl ?? '/tablero';
    limpiarIntentoGoogle();
    return returnUrl;
  }

  async cargarUsuario(): Promise<void> {
    const usuario = await firstValueFrom(this.http.get<UsuarioActual>(`${this.base}/auth/yo/`));
    this.usuario.set(usuario);
  }

  /** Único punto de refresh; lo usa también el interceptor ante un 401. */
  async refrescar(): Promise<string> {
    const refresh = this.obtenerRefreshToken();
    if (!refresh) {
      throw new Error('No hay sesión para refrescar.');
    }
    const respuesta = await firstValueFrom(
      this.http.post<RespuestaRefresh>(`${this.base}/auth/refresh/`, { refresh }),
    );
    this.guardarTokens(respuesta.access, respuesta.refresh);
    return respuesta.access;
  }

  async logout(): Promise<void> {
    const refresh = this.obtenerRefreshToken();
    try {
      if (refresh) {
        await firstValueFrom(this.http.post(`${this.base}/auth/logout/`, { refresh }));
      }
    } finally {
      this.limpiarSesion();
    }
  }

  limpiarSesion(): void {
    this.limpiarTokens();
    this.usuario.set(null);
  }

  /** Se llama una vez al arrancar la app (ver provideAppInitializer en app.config.ts). */
  async restaurarSesion(): Promise<void> {
    if (!this.obtenerRefreshToken()) {
      return;
    }
    this.cargando.set(true);
    try {
      await this.refrescar();
      await this.cargarUsuario();
    } catch {
      this.limpiarSesion();
    } finally {
      this.cargando.set(false);
    }
  }

  tieneRol(codigo: string): boolean {
    return this.usuario()?.roles.includes(codigo) ?? false;
  }

  tienePermiso(codigo: string): boolean {
    return this.usuario()?.permisos_ui.includes(codigo) ?? false;
  }
}
