import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { ErrorApi } from '../../core/models';
import { Boton } from '../../shared/ui/boton/boton';
import { Input } from '../../shared/ui/input/input';

@Component({
  selector: 'app-login',
  templateUrl: './login.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Input],
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly email = signal('');
  protected readonly clave = signal('');
  protected readonly enviando = signal(false);
  protected readonly mensajeError = signal('');
  protected readonly erroresPorCampo = signal<Record<string, string[]>>({});
  protected readonly googleDisponible = signal(false);

  constructor() {
    void this.auth.googleDisponible().then((disponible) => this.googleDisponible.set(disponible));
  }

  private returnUrl(): string {
    return this.ruta.snapshot.queryParamMap.get('returnUrl') ?? '/tablero';
  }

  protected async enviar(): Promise<void> {
    this.enviando.set(true);
    this.mensajeError.set('');
    this.erroresPorCampo.set({});
    try {
      await this.auth.login(this.email(), this.clave());
      await this.router.navigateByUrl(this.returnUrl());
    } catch (error) {
      this.mostrarError(error);
    } finally {
      this.enviando.set(false);
    }
  }

  protected async continuarConGoogle(): Promise<void> {
    try {
      const url = await this.auth.loginGoogle(this.returnUrl());
      window.location.href = url;
    } catch (error) {
      this.mostrarError(error);
    }
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
