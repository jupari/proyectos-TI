import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ErrorApi } from '../../core/models';
import { Boton } from '../../shared/ui/boton/boton';
import { Input } from '../../shared/ui/input/input';

/** Pantalla pública (sin guard) a la que llega el enlace del correo de
 * recuperación, con `uid` y `token` como query params. */
@Component({
  selector: 'app-restablecer-clave',
  templateUrl: './restablecer-clave.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Input, RouterLink],
})
export class RestablecerClave {
  private readonly http = inject(HttpClient);
  private readonly ruta = inject(ActivatedRoute);
  private readonly router = inject(Router);

  private readonly uid = this.ruta.snapshot.queryParamMap.get('uid') ?? '';
  private readonly token = this.ruta.snapshot.queryParamMap.get('token') ?? '';
  protected readonly enlaceInvalido = !this.uid || !this.token;

  protected readonly claveNueva = signal('');
  protected readonly confirmarClave = signal('');
  protected readonly enviando = signal(false);
  protected readonly mensajeError = signal('');
  protected readonly listo = signal(false);

  protected async enviar(): Promise<void> {
    if (this.claveNueva() !== this.confirmarClave()) {
      this.mensajeError.set('Las contraseñas no coinciden.');
      return;
    }

    this.enviando.set(true);
    this.mensajeError.set('');
    try {
      await firstValueFrom(
        this.http.post(`${environment.apiBaseUrl}/auth/restablecer-clave/`, {
          uid: this.uid,
          token: this.token,
          clave_nueva: this.claveNueva(),
        }),
      );
      this.listo.set(true);
      setTimeout(() => void this.router.navigateByUrl('/auth/login'), 2000);
    } catch (error) {
      if (error instanceof HttpErrorResponse) {
        const cuerpo = error.error as Partial<ErrorApi> | null;
        this.mensajeError.set(cuerpo?.error?.mensaje ?? 'No se pudo cambiar la contraseña.');
      } else {
        this.mensajeError.set('No se pudo cambiar la contraseña. Intente de nuevo.');
      }
    } finally {
      this.enviando.set(false);
    }
  }
}
