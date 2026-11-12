import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ErrorApi, RolMeta, Usuario } from '../../../core/models';
import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { ToastService } from '../../../core/ui/toast.service';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Input } from '../../../shared/ui/input/input';
import { Modal } from '../../../shared/ui/modal/modal';
import { Switch } from '../../../shared/ui/switch/switch';
import { RolesService } from '../data/roles.service';
import { UsuariosService } from '../data/usuarios.service';

@Component({
  selector: 'app-usuarios',
  templateUrl: './usuarios.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Badge, Boton, EstadoVacio, Input, Modal, Switch],
})
export class Usuarios {
  private readonly usuariosService = inject(UsuariosService);
  private readonly rolesService = inject(RolesService);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly toast = inject(ToastService);

  protected readonly cargando = signal(false);
  protected readonly usuarios = signal<Usuario[]>([]);
  protected readonly roles = signal<RolMeta[]>([]);
  protected readonly busqueda = signal('');

  protected readonly modalAbierto = signal(false);
  protected readonly idEnEdicion = signal<string | null>(null);
  protected readonly guardando = signal(false);
  protected readonly erroresPorCampo = signal<Record<string, string[]>>({});

  protected readonly email = signal('');
  protected readonly nombres = signal('');
  protected readonly apellidos = signal('');
  protected readonly cargo = signal('');
  protected readonly telefono = signal('');
  protected readonly estaActivo = signal(true);
  protected readonly rolesSeleccionados = signal<string[]>([]);

  // Se muestra una sola vez, justo tras crear la cuenta: no hay envío de
  // correo en esta versión (PLAN.md §10), así que es la única oportunidad de
  // comunicar la clave inicial a quien la va a usar.
  protected readonly claveTemporalCreada = signal<string | null>(null);
  protected readonly correoClaveTemporal = signal('');

  constructor() {
    this.rolesService
      .listar({ page_size: 200, ordering: 'orden' })
      .subscribe((respuesta) => this.roles.set(respuesta.results));
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.usuariosService
      .listar({ search: this.busqueda() || undefined, page_size: 200, ordering: 'nombres' })
      .subscribe({
        next: (respuesta) => {
          this.usuarios.set(respuesta.results);
          this.cargando.set(false);
        },
        error: () => {
          this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudieron cargar los usuarios.' });
          this.cargando.set(false);
        },
      });
  }

  protected abrirNuevo(): void {
    this.idEnEdicion.set(null);
    this.email.set('');
    this.nombres.set('');
    this.apellidos.set('');
    this.cargo.set('');
    this.telefono.set('');
    this.estaActivo.set(true);
    this.rolesSeleccionados.set([]);
    this.erroresPorCampo.set({});
    this.modalAbierto.set(true);
  }

  protected abrirEditar(usuario: Usuario): void {
    this.idEnEdicion.set(usuario.id);
    this.email.set(usuario.email);
    this.nombres.set(usuario.nombres);
    this.apellidos.set(usuario.apellidos);
    this.cargo.set(usuario.cargo);
    this.telefono.set(usuario.telefono);
    this.estaActivo.set(usuario.is_active);
    this.rolesSeleccionados.set([...usuario.roles]);
    this.erroresPorCampo.set({});
    this.modalAbierto.set(true);
  }

  protected cerrarModal(): void {
    this.modalAbierto.set(false);
  }

  protected tieneRol(codigo: string): boolean {
    return this.rolesSeleccionados().includes(codigo);
  }

  protected alternarRol(codigo: string): void {
    const actuales = this.rolesSeleccionados();
    this.rolesSeleccionados.set(
      actuales.includes(codigo) ? actuales.filter((c) => c !== codigo) : [...actuales, codigo],
    );
  }

  protected guardar(): void {
    if (!this.email() || !this.nombres() || !this.apellidos()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete el correo, nombres y apellidos.' });
      return;
    }

    const id = this.idEnEdicion();
    const cuerpo = {
      email: this.email(),
      nombres: this.nombres(),
      apellidos: this.apellidos(),
      cargo: this.cargo(),
      telefono: this.telefono(),
      is_active: this.estaActivo(),
      roles: this.rolesSeleccionados(),
    };

    this.guardando.set(true);
    this.erroresPorCampo.set({});

    const alTerminar = (): void => {
      this.guardando.set(false);
      this.modalAbierto.set(false);
      this.cargar();
    };
    const alFallar = (error: unknown): void => {
      this.guardando.set(false);
      if (error instanceof HttpErrorResponse) {
        const cuerpoError = error.error as Partial<ErrorApi> | null;
        this.erroresPorCampo.set(cuerpoError?.error?.detalles ?? {});
        this.toast.mostrar({
          tipo: 'error',
          mensaje: cuerpoError?.error?.mensaje ?? 'No se pudo guardar el usuario.',
        });
      }
    };

    if (id) {
      this.usuariosService.actualizarUsuario(id, cuerpo).subscribe({
        next: () => {
          alTerminar();
          this.toast.mostrar({ tipo: 'exito', mensaje: 'Usuario guardado.' });
        },
        error: alFallar,
      });
      return;
    }

    this.usuariosService.crearUsuario(cuerpo).subscribe({
      next: (resultado) => {
        alTerminar();
        this.correoClaveTemporal.set(cuerpo.email);
        this.claveTemporalCreada.set(resultado.clave_temporal);
      },
      error: alFallar,
    });
  }

  protected cerrarClaveTemporal(): void {
    this.claveTemporalCreada.set(null);
  }

  protected async copiarClaveTemporal(): Promise<void> {
    const clave = this.claveTemporalCreada();
    if (!clave) return;
    try {
      await navigator.clipboard.writeText(clave);
      this.toast.mostrar({ tipo: 'exito', mensaje: 'Clave copiada al portapapeles.' });
    } catch {
      // Sin permiso de portapapeles (p. ej. contexto no seguro): la clave
      // sigue visible en el modal para copiarla a mano.
    }
  }

  protected async alternarActivo(usuario: Usuario): Promise<void> {
    if (usuario.is_active) {
      const confirmado = await this.confirmacion.confirmar({
        titulo: 'Desactivar usuario',
        mensaje: `¿Desactivar a «${usuario.nombres} ${usuario.apellidos}»? No podrá iniciar sesión.`,
        variante: 'peligro',
        textoConfirmar: 'Desactivar',
      });
      if (!confirmado) return;
      this.usuariosService.desactivar(usuario.id).subscribe({
        next: () => {
          this.toast.mostrar({ tipo: 'exito', mensaje: 'Usuario desactivado.' });
          this.cargar();
        },
        error: () => this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo desactivar.' }),
      });
    } else {
      this.usuariosService.activar(usuario.id).subscribe({
        next: () => {
          this.toast.mostrar({ tipo: 'exito', mensaje: 'Usuario activado.' });
          this.cargar();
        },
        error: () => this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo activar.' }),
      });
    }
  }
}
