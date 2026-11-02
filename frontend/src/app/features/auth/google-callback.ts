import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';

/** Lee `code`/`state` de la URL, canjea en /auth/google/callback/ y navega
 * al `returnUrl` guardado antes de salir hacia Google. */
@Component({
  selector: 'app-google-callback',
  template: `
    <div class="flex min-h-screen items-center justify-center">
      @if (error()) {
        <p class="text-sm text-peligro">{{ error() }}</p>
      } @else {
        <p class="text-sm text-neutro-500">Completando el inicio de sesión con Google…</p>
      }
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GoogleCallback {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly error = signal('');

  constructor() {
    void this.completar();
  }

  private async completar(): Promise<void> {
    const parametros = this.ruta.snapshot.queryParamMap;
    const code = parametros.get('code');
    const state = parametros.get('state');

    if (!code || !state) {
      await this.irALoginConError('Falta el código o el state de Google.');
      return;
    }

    try {
      const returnUrl = await this.auth.completarLoginGoogle(code, state);
      await this.router.navigateByUrl(returnUrl);
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'No se pudo completar el inicio de sesión.';
      await this.irALoginConError(mensaje);
    }
  }

  private async irALoginConError(mensaje: string): Promise<void> {
    this.error.set(mensaje);
    await this.router.navigate(['/auth/login'], { queryParams: { error: mensaje } });
  }
}
