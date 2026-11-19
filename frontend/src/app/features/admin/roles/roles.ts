import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ErrorApi, RolMeta } from '../../../core/models';
import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { ToastService } from '../../../core/ui/toast.service';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { CabeceraAdmin } from '../../../shared/ui/cabecera-admin/cabecera-admin';
import { FichaResumen } from '../../../shared/ui/ficha-resumen/ficha-resumen';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Input } from '../../../shared/ui/input/input';
import { Modal } from '../../../shared/ui/modal/modal';
import { Numero } from '../../../shared/ui/numero/numero';
import { RolesService } from '../data/roles.service';

@Component({
  selector: 'app-roles',
  templateUrl: './roles.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Badge, Boton, CabeceraAdmin, FichaResumen, EstadoVacio, Input, Modal, Numero],
})
export class Roles {
  private readonly rolesService = inject(RolesService);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly toast = inject(ToastService);

  protected readonly cargando = signal(false);
  protected readonly roles = signal<RolMeta[]>([]);
  protected readonly resumen = computed(() => {
    const lista = this.roles();
    const sistema = lista.filter((r) => r.es_sistema).length;
    return { total: lista.length, sistema, personalizados: lista.length - sistema };
  });

  protected readonly modalAbierto = signal(false);
  protected readonly idEnEdicion = signal<string | null>(null);
  protected readonly esSistemaEnEdicion = signal(false);
  protected readonly guardando = signal(false);
  protected readonly erroresPorCampo = signal<Record<string, string[]>>({});

  protected readonly codigo = signal('');
  protected readonly descripcion = signal('');
  protected readonly orden = signal<number | null>(0);

  constructor() {
    this.cargar();
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.rolesService.listar({ page_size: 200, ordering: 'orden' }).subscribe({
      next: (respuesta) => {
        this.roles.set(respuesta.results);
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudieron cargar los roles.' });
        this.cargando.set(false);
      },
    });
  }

  protected abrirNuevo(): void {
    this.idEnEdicion.set(null);
    this.esSistemaEnEdicion.set(false);
    this.codigo.set('');
    this.descripcion.set('');
    this.orden.set(this.roles().length);
    this.erroresPorCampo.set({});
    this.modalAbierto.set(true);
  }

  protected abrirEditar(rol: RolMeta): void {
    this.idEnEdicion.set(rol.id);
    this.esSistemaEnEdicion.set(rol.es_sistema);
    this.codigo.set(rol.codigo);
    this.descripcion.set(rol.descripcion);
    this.orden.set(rol.orden);
    this.erroresPorCampo.set({});
    this.modalAbierto.set(true);
  }

  protected cerrarModal(): void {
    this.modalAbierto.set(false);
  }

  protected guardar(): void {
    if (!this.codigo() || !this.descripcion()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete el código y la descripción.' });
      return;
    }

    const id = this.idEnEdicion();
    const cuerpo = {
      codigo: this.codigo(),
      descripcion: this.descripcion(),
      orden: this.orden() ?? 0,
    };

    this.guardando.set(true);
    this.erroresPorCampo.set({});
    const peticion = id ? this.rolesService.actualizar(id, cuerpo) : this.rolesService.crear(cuerpo);

    peticion.subscribe({
      next: () => {
        this.guardando.set(false);
        this.modalAbierto.set(false);
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Rol guardado.' });
        this.cargar();
      },
      error: (error: unknown) => {
        this.guardando.set(false);
        if (error instanceof HttpErrorResponse) {
          const cuerpoError = error.error as Partial<ErrorApi> | null;
          this.erroresPorCampo.set(cuerpoError?.error?.detalles ?? {});
          this.toast.mostrar({
            tipo: 'error',
            mensaje: cuerpoError?.error?.mensaje ?? 'No se pudo guardar el rol.',
          });
        }
      },
    });
  }

  protected async eliminar(rol: RolMeta): Promise<void> {
    if (rol.es_sistema) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Un rol del sistema no se puede borrar.' });
      return;
    }
    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Desactivar rol',
      mensaje: `¿Desactivar el rol «${rol.descripcion}»?`,
      variante: 'peligro',
      textoConfirmar: 'Desactivar',
    });
    if (!confirmado) return;

    this.rolesService.eliminar(rol.id).subscribe({
      next: () => {
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Rol desactivado.' });
        this.cargar();
      },
      error: () => this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo desactivar el rol.' }),
    });
  }
}
