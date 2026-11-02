import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth/auth.service';
import { ErrorApi } from '../../core/models';
import { Boton } from '../../shared/ui/boton/boton';
import { Input } from '../../shared/ui/input/input';

/** Obligatoria cuando `usuario.debe_cambiar_clave` es `true` (ver `cambioClaveGuard`). */
@Component({
  selector: 'app-cambiar-clave',
  templateUrl: './cambiar-clave.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Input],
})
export class CambiarClave {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly claveActual = signal('');
  protected readonly claveNueva = signal('');
  protected readonly enviando = signal(false);
  protected readonly mensajeError = signal('');
  protected readonly erroresPorCampo = signal<Record<string, string[]>>({});

  protected async enviar(): Promise<void> {
    this.enviando.set(true);
    this.mensajeError.set('');
    this.erroresPorCampo.set({});
    try {
      await firstValueFrom(
        this.http.post(`${environment.apiBaseUrl}/auth/cambiar-clave/`, {
          clave_actual: this.claveActual(),
          clave_nueva: this.claveNueva(),
        }),
      );
      await this.auth.cargarUsuario();
      await this.router.navigateByUrl('/tablero');
    } catch (error) {
      if (error instanceof HttpErrorResponse) {
        const cuerpo = error.error as Partial<ErrorApi> | null;
        this.mensajeError.set(cuerpo?.error?.mensaje ?? 'No se pudo cambiar la contraseña.');
        this.erroresPorCampo.set(cuerpo?.error?.detalles ?? {});
      }
    } finally {
      this.enviando.set(false);
    }
  }
}
