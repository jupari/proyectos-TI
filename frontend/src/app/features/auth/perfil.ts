import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth/auth.service';
import { ErrorApi, UsuarioActual } from '../../core/models';
import { Boton } from '../../shared/ui/boton/boton';
import { Card } from '../../shared/ui/card/card';
import { Input } from '../../shared/ui/input/input';

@Component({
  selector: 'app-perfil',
  templateUrl: './perfil.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Input, Card],
})
export class Perfil {
  private readonly http = inject(HttpClient);
  protected readonly auth = inject(AuthService);

  protected readonly nombres = signal(this.auth.usuario()?.nombres ?? '');
  protected readonly apellidos = signal(this.auth.usuario()?.apellidos ?? '');
  protected readonly cargo = signal(this.auth.usuario()?.cargo ?? '');
  protected readonly telefono = signal(this.auth.usuario()?.telefono ?? '');

  protected readonly guardando = signal(false);
  protected readonly mensajeError = signal('');
  protected readonly guardadoConExito = signal(false);

  protected async guardar(): Promise<void> {
    this.guardando.set(true);
    this.mensajeError.set('');
    this.guardadoConExito.set(false);
    try {
      const usuario = await firstValueFrom(
        this.http.patch<UsuarioActual>(`${environment.apiBaseUrl}/auth/yo/`, {
          nombres: this.nombres(),
          apellidos: this.apellidos(),
          cargo: this.cargo(),
          telefono: this.telefono(),
        }),
      );
      this.auth.usuario.set(usuario);
      this.guardadoConExito.set(true);
    } catch (error) {
      if (error instanceof HttpErrorResponse) {
        const cuerpo = error.error as Partial<ErrorApi> | null;
        this.mensajeError.set(cuerpo?.error?.mensaje ?? 'No se pudo guardar.');
      }
    } finally {
      this.guardando.set(false);
    }
  }
}
