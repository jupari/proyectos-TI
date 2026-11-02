import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { ErrorApi, ETIQUETAS_TIPO_RECURSO } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { Boton } from '../../../shared/ui/boton/boton';
import { Datepicker } from '../../../shared/ui/datepicker/datepicker';
import { Input } from '../../../shared/ui/input/input';
import { Numero } from '../../../shared/ui/numero/numero';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { PerfilesRecursoService } from '../../admin/data/catalogos.service';
import { UsuariosService } from '../../admin/data/usuarios.service';
import { RecursoEscritura } from '../data/recursos.model';
import { RecursosService } from '../data/recursos.service';

@Component({
  selector: 'app-formulario-recurso',
  templateUrl: './formulario.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Input, Select, Numero, Datepicker],
})
export class FormularioRecurso {
  private readonly recursosService = inject(RecursosService);
  private readonly perfilesService = inject(PerfilesRecursoService);
  private readonly usuariosService = inject(UsuariosService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly idRecurso = signal<string | null>(this.ruta.snapshot.paramMap.get('id'));
  protected readonly esEdicion = computed(() => this.idRecurso() !== null);

  protected readonly cargandoDetalle = signal(false);
  protected readonly guardando = signal(false);
  protected readonly mensajeError = signal('');
  protected readonly erroresPorCampo = signal<Record<string, string[]>>({});

  protected readonly tipo = signal('INTERNO');
  protected readonly nombre = signal('');
  protected readonly usuario = signal<string | null>(null);
  protected readonly perfil = signal<string | null>(null);
  protected readonly email = signal('');
  protected readonly capacidadHorasMes = signal<number | null>(160);
  protected readonly fechaIngreso = signal<string | null>(null);
  protected readonly fechaRetiro = signal<string | null>(null);

  protected readonly opcionesPerfiles = signal<OpcionSelect[]>([]);
  protected readonly opcionesUsuarios = signal<OpcionSelect[]>([]);
  protected readonly opcionesTipo: OpcionSelect[] = Object.entries(ETIQUETAS_TIPO_RECURSO).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );

  constructor() {
    this.perfilesService
      .listar({ page_size: 200 })
      .subscribe((r) =>
        this.opcionesPerfiles.set(r.results.map((p) => ({ valor: p.id, etiqueta: p.nombre }))),
      );
    this.usuariosService
      .listar({ page_size: 200, ordering: 'nombres' })
      .subscribe((r) =>
        this.opcionesUsuarios.set(
          r.results.map((u) => ({ valor: u.id, etiqueta: `${u.nombres} ${u.apellidos}` })),
        ),
      );

    const id = this.idRecurso();
    if (id) this.cargarRecurso(id);
  }

  private cargarRecurso(id: string): void {
    this.cargandoDetalle.set(true);
    this.recursosService.obtenerDetalle(id).subscribe({
      next: (recurso) => {
        this.tipo.set(recurso.tipo);
        this.nombre.set(recurso.nombre);
        this.usuario.set(recurso.usuario);
        this.perfil.set(recurso.perfil);
        this.email.set(recurso.email ?? '');
        this.capacidadHorasMes.set(Number(recurso.capacidad_horas_mes));
        this.fechaIngreso.set(recurso.fecha_ingreso);
        this.fechaRetiro.set(recurso.fecha_retiro);
        this.cargandoDetalle.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el recurso.' });
        this.cargandoDetalle.set(false);
      },
    });
  }

  protected async cancelar(): Promise<void> {
    const id = this.idRecurso();
    await this.router.navigateByUrl(id ? `/recursos/${id}` : '/recursos');
  }

  protected guardar(): void {
    if (!this.nombre()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete el nombre del recurso.' });
      return;
    }

    const cuerpo: RecursoEscritura = {
      tipo: this.tipo(),
      nombre: this.nombre(),
      usuario: this.usuario(),
      perfil: this.perfil(),
      email: this.email() || null,
      capacidad_horas_mes: this.capacidadHorasMes() ?? 160,
      fecha_ingreso: this.fechaIngreso(),
      fecha_retiro: this.fechaRetiro(),
    };

    this.guardando.set(true);
    this.mensajeError.set('');
    this.erroresPorCampo.set({});

    const id = this.idRecurso();
    const peticion = id
      ? this.recursosService.actualizarRecurso(id, cuerpo)
      : this.recursosService.crearRecurso(cuerpo);

    peticion.subscribe({
      next: (recurso) => {
        this.guardando.set(false);
        this.toast.mostrar({
          tipo: 'exito',
          mensaje: id ? 'Recurso actualizado.' : 'Recurso creado.',
        });
        void this.router.navigateByUrl(`/recursos/${recurso.id}`);
      },
      error: (error: unknown) => {
        this.guardando.set(false);
        if (error instanceof HttpErrorResponse) {
          const cuerpoError = error.error as Partial<ErrorApi> | null;
          this.mensajeError.set(cuerpoError?.error?.mensaje ?? 'No se pudo guardar el recurso.');
          this.erroresPorCampo.set(cuerpoError?.error?.detalles ?? {});
        }
      },
    });
  }
}
