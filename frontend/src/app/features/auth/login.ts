import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { ErrorApi } from '../../core/models';

const SEGUNDOS_ESPERA_REENVIO = 30;

@Component({
  selector: 'app-login',
  templateUrl: './login.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected email = signal('');
  protected clave = signal('');
  protected enviando = signal(false);
  protected mensajeError = signal('');
  protected erroresPorCampo = signal<Record<string, string[]>>({});

  /** Paso 1 (credenciales) o paso 2 (código recibido por correo) — fase 13. */
  protected paso = signal<'credenciales' | 'codigo'>('credenciales');
  protected loginToken = signal('');
  protected codigo = signal('');
  protected reenviando = signal(false);
  protected segundosParaReenviar = signal(0);
  private intervaloReenvio?: ReturnType<typeof setInterval>;

  private returnUrl(): string {
    return this.ruta.snapshot.queryParamMap.get('returnUrl') ?? '/tablero';
  }

  protected async enviar(): Promise<void> {
    this.enviando.set(true);
    this.mensajeError.set('');
    this.erroresPorCampo.set({});
    try {
      const loginToken = await this.auth.solicitarCodigo(this.email(), this.clave());
      this.loginToken.set(loginToken);
      this.paso.set('codigo');
      this.iniciarEsperaReenvio();
    } catch (error) {
      this.mostrarError(error);
    } finally {
      this.enviando.set(false);
    }
  }

  protected async confirmarCodigo(): Promise<void> {
    this.enviando.set(true);
    this.mensajeError.set('');
    try {
      await this.auth.verificarCodigo(this.loginToken(), this.codigo());
      await this.router.navigateByUrl(this.returnUrl());
    } catch (error) {
      this.mostrarError(error);
    } finally {
      this.enviando.set(false);
    }
  }

  protected async reenviarCodigo(): Promise<void> {
    this.reenviando.set(true);
    this.mensajeError.set('');
    try {
      await this.auth.reenviarCodigo(this.loginToken());
      this.iniciarEsperaReenvio();
    } catch (error) {
      this.mostrarError(error);
    } finally {
      this.reenviando.set(false);
    }
  }

  protected volverACredenciales(): void {
    this.paso.set('credenciales');
    this.codigo.set('');
    this.mensajeError.set('');
    clearInterval(this.intervaloReenvio);
  }

  private iniciarEsperaReenvio(): void {
    clearInterval(this.intervaloReenvio);
    this.segundosParaReenviar.set(SEGUNDOS_ESPERA_REENVIO);
    this.intervaloReenvio = setInterval(() => {
      const restantes = this.segundosParaReenviar() - 1;
      this.segundosParaReenviar.set(restantes);
      if (restantes <= 0) {
        clearInterval(this.intervaloReenvio);
      }
    }, 1000);
  }

  private mostrarError(error: unknown): void {
    if (error instanceof HttpErrorResponse) {
      const cuerpo = error.error as Partial<ErrorApi> | null;
      this.mensajeError.set(cuerpo?.error?.mensaje ?? 'No se pudo iniciar sesión.');
      this.erroresPorCampo.set(cuerpo?.error?.detalles ?? {});
    } else {
      this.mensajeError.set('No se pudo iniciar sesión. Intente de nuevo.');
    }
  }
}
