import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ErrorApi } from '../../core/models';
import { Boton } from '../../shared/ui/boton/boton';
import { Input } from '../../shared/ui/input/input';

/** Pantalla pública (sin guard): pide el correo y siempre muestra el mismo
 * mensaje de confirmación, exista o no la cuenta — el backend responde igual
 * en ambos casos a propósito, para no revelar qué correos existen. */
@Component({
  selector: 'app-recuperar-clave',
  templateUrl: './recuperar-clave.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Input, RouterLink],
})
export class RecuperarClave {
  private readonly http = inject(HttpClient);

  protected readonly email = signal('');
  protected readonly enviando = signal(false);
  protected readonly enviado = signal(false);
  protected readonly mensajeError = signal('');

  protected async enviar(): Promise<void> {
    this.enviando.set(true);
    this.mensajeError.set('');
    try {
      await firstValueFrom(
        this.http.post(`${environment.apiBaseUrl}/auth/recuperar-clave/`, { email: this.email() }),
      );
      this.enviado.set(true);
    } catch (error) {
      if (error instanceof HttpErrorResponse) {
        const cuerpo = error.error as Partial<ErrorApi> | null;
        this.mensajeError.set(cuerpo?.error?.mensaje ?? 'No se pudo procesar la solicitud.');
      } else {
        this.mensajeError.set('No se pudo procesar la solicitud. Intente de nuevo.');
      }
    } finally {
      this.enviando.set(false);
    }
  }
}
