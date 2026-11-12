import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  WritableSignal,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { ErrorApi, ETIQUETAS_PRIORIDAD } from '../../../core/models';
import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { ToastService } from '../../../core/ui/toast.service';
import { Boton } from '../../../shared/ui/boton/boton';
import { Datepicker } from '../../../shared/ui/datepicker/datepicker';
import { Input } from '../../../shared/ui/input/input';
import { Numero } from '../../../shared/ui/numero/numero';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Textarea } from '../../../shared/ui/textarea/textarea';
import { AreasService, PortafoliosService } from '../../admin/data/catalogos.service';
import { IntegracionesJiraService } from '../../admin/data/integraciones-jira.service';
import { UsuariosService } from '../../admin/data/usuarios.service';
import { ProyectoEscritura } from '../data/proyectos.model';
import { ProyectosService } from '../data/proyectos.service';

@Component({
  selector: 'app-formulario-proyecto',
  templateUrl: './formulario.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Input, Textarea, Select, Datepicker, Numero],
})
export class FormularioProyecto {
  private readonly proyectosService = inject(ProyectosService);
  private readonly areasService = inject(AreasService);
  private readonly portafoliosService = inject(PortafoliosService);
  private readonly usuariosService = inject(UsuariosService);
  private readonly integracionesJiraService = inject(IntegracionesJiraService);
  private readonly auth = inject(AuthService);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly idProyecto = signal<string | null>(this.ruta.snapshot.paramMap.get('id'));
  protected readonly esEdicion = computed(() => this.idProyecto() !== null);

  protected readonly cargandoDetalle = signal(false);
  protected readonly guardando = signal(false);
  protected readonly mensajeError = signal('');
  protected readonly erroresPorCampo = signal<Record<string, string[]>>({});
  protected readonly cambiosSinGuardar = signal(false);

  protected readonly nombre = signal('');
  protected readonly descripcion = signal('');
  protected readonly objetivo = signal('');
  protected readonly areaSolicitante = signal<string | null>(null);
  protected readonly portafolio = signal<string | null>(null);
  protected readonly gerente = signal<string | null>(null);
  protected readonly liderTecnico = signal<string | null>(null);
  protected readonly prioridad = signal('MEDIA');
  protected readonly fechaInicioPlan = signal<string | null>(null);
  protected readonly fechaFinPlan = signal<string | null>(null);
  protected readonly fechaInicioReal = signal<string | null>(null);
  protected readonly fechaFinReal = signal<string | null>(null);
  protected readonly moneda = signal('COP');
  protected readonly presupuestoHoras = signal<number | null>(null);
  protected readonly presupuestoDinero = signal<number | null>(null);
  protected readonly observaciones = signal('');
  protected readonly claveJira = signal<string | null>(null);

  protected readonly puedeMapearJira = computed(
    () => this.auth.tieneRol('ADMIN') || this.auth.tieneRol('PMO'),
  );

  protected readonly opcionesAreas = signal<OpcionSelect[]>([]);
  protected readonly opcionesPortafolios = signal<OpcionSelect[]>([]);
  protected readonly opcionesUsuarios = signal<OpcionSelect[]>([]);
  protected readonly opcionesProyectosJira = signal<OpcionSelect[]>([]);
  protected readonly opcionesPrioridad: OpcionSelect[] = Object.entries(ETIQUETAS_PRIORIDAD).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );

  /** Refleja en cliente la misma regla que valida el servidor
   * (docs/modelo-datos.md §3: `fecha_fin_plan >= fecha_inicio_plan`). */
  protected readonly errorFechaFin = computed(() => {
    const inicio = this.fechaInicioPlan();
    const fin = this.fechaFinPlan();
    if (inicio && fin && fin < inicio) {
      return 'Debe ser igual o posterior a la fecha de inicio plan.';
    }
    return this.erroresPorCampo()['fecha_fin_plan']?.[0] ?? '';
  });

  constructor() {
    this.cargarCatalogos();
    const id = this.idProyecto();
    if (id) {
      this.cargarProyecto(id);
    }
  }

  @HostListener('window:beforeunload', ['$event'])
  protected alSalir(evento: BeforeUnloadEvent): void {
    if (this.cambiosSinGuardar()) {
      evento.preventDefault();
      evento.returnValue = true;
    }
  }

  protected actualizar<T>(destino: WritableSignal<T>, valor: T): void {
    destino.set(valor);
    this.cambiosSinGuardar.set(true);
  }

  private cargarCatalogos(): void {
    this.areasService
      .listar({ page_size: 200 })
      .subscribe((r) => this.opcionesAreas.set(r.results.map((a) => ({ valor: a.id, etiqueta: a.nombre }))));
    this.portafoliosService
      .listar({ page_size: 200 })
      .subscribe((r) =>
        this.opcionesPortafolios.set(r.results.map((p) => ({ valor: p.id, etiqueta: p.nombre }))),
      );
    this.usuariosService
      .listar({ page_size: 200, ordering: 'nombres' })
      .subscribe((r) =>
        this.opcionesUsuarios.set(
          r.results.map((u) => ({ valor: u.id, etiqueta: `${u.nombres} ${u.apellidos}` })),
        ),
      );
    if (this.puedeMapearJira()) {
      this.integracionesJiraService.listarProyectosJira().subscribe({
        next: (proyectos) =>
          this.opcionesProyectosJira.set(
            proyectos.map((p) => ({ valor: p.clave, etiqueta: `${p.clave} — ${p.nombre}` })),
          ),
        error: () =>
          this.toast.mostrar({
            tipo: 'alerta',
            mensaje: 'No se pudo cargar la lista de proyectos de Jira.',
          }),
      });
    }
  }

  private cargarProyecto(id: string): void {
    this.cargandoDetalle.set(true);
    this.proyectosService.obtenerDetalle(id).subscribe({
      next: (proyecto) => {
        this.nombre.set(proyecto.nombre);
        this.descripcion.set(proyecto.descripcion);
        this.objetivo.set(proyecto.objetivo);
        this.areaSolicitante.set(proyecto.area_solicitante);
        this.portafolio.set(proyecto.portafolio);
        this.gerente.set(proyecto.gerente);
        this.liderTecnico.set(proyecto.lider_tecnico);
        this.prioridad.set(proyecto.prioridad);
        this.fechaInicioPlan.set(proyecto.fecha_inicio_plan);
        this.fechaFinPlan.set(proyecto.fecha_fin_plan);
        this.fechaInicioReal.set(proyecto.fecha_inicio_real);
        this.fechaFinReal.set(proyecto.fecha_fin_real);
        this.moneda.set(proyecto.moneda);
        this.presupuestoHoras.set(Number(proyecto.presupuesto_horas));
        this.presupuestoDinero.set(Number(proyecto.presupuesto_dinero));
        this.observaciones.set(proyecto.observaciones);
        this.claveJira.set(proyecto.clave_jira || null);
        this.cargandoDetalle.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el proyecto.' });
        this.cargandoDetalle.set(false);
      },
    });
  }

  protected async cancelar(): Promise<void> {
    if (this.cambiosSinGuardar()) {
      const confirmado = await this.confirmacion.confirmar({
        titulo: 'Descartar cambios',
        mensaje: 'Hay cambios sin guardar. ¿Desea salir de todas formas?',
        variante: 'peligro',
        textoConfirmar: 'Salir sin guardar',
      });
      if (!confirmado) return;
    }
    await this.volver();
  }

  private async volver(): Promise<void> {
    const id = this.idProyecto();
    await this.router.navigateByUrl(id ? `/proyectos/${id}` : '/proyectos');
  }

  protected async guardar(): Promise<void> {
    if (this.errorFechaFin() && this.fechaFinPlan() && this.fechaInicioPlan()) {
      this.toast.mostrar({ tipo: 'error', mensaje: this.errorFechaFin() });
      return;
    }
    if (!this.nombre() || !this.areaSolicitante() || !this.gerente() || !this.fechaInicioPlan() || !this.fechaFinPlan()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete los campos obligatorios.' });
      return;
    }

    const cuerpo: ProyectoEscritura = {
      nombre: this.nombre(),
      descripcion: this.descripcion(),
      objetivo: this.objetivo(),
      portafolio: this.portafolio(),
      area_solicitante: this.areaSolicitante()!,
      gerente: this.gerente()!,
      lider_tecnico: this.liderTecnico(),
      prioridad: this.prioridad(),
      fecha_inicio_plan: this.fechaInicioPlan()!,
      fecha_fin_plan: this.fechaFinPlan()!,
      fecha_inicio_real: this.fechaInicioReal(),
      fecha_fin_real: this.fechaFinReal(),
      moneda: this.moneda(),
      presupuesto_horas: this.presupuestoHoras() ?? 0,
      presupuesto_dinero: this.presupuestoDinero() ?? 0,
      avance_reportado: 0,
      observaciones: this.observaciones(),
      clave_jira: this.claveJira() ?? '',
    };

    this.guardando.set(true);
    this.mensajeError.set('');
    this.erroresPorCampo.set({});

    const id = this.idProyecto();
    const peticion = id
      ? this.proyectosService.actualizarProyecto(id, cuerpo)
      : this.proyectosService.crearProyecto(cuerpo);

    peticion.subscribe({
      next: (proyecto) => {
        this.cambiosSinGuardar.set(false);
        this.guardando.set(false);
        this.toast.mostrar({
          tipo: 'exito',
          mensaje: id ? 'Proyecto actualizado.' : `Proyecto ${proyecto.codigo} creado.`,
        });
        void this.router.navigateByUrl(`/proyectos/${proyecto.id}`);
      },
      error: (error: unknown) => {
        this.guardando.set(false);
        if (error instanceof HttpErrorResponse) {
          const cuerpoError = error.error as Partial<ErrorApi> | null;
          this.mensajeError.set(cuerpoError?.error?.mensaje ?? 'No se pudo guardar el proyecto.');
          this.erroresPorCampo.set(cuerpoError?.error?.detalles ?? {});
        }
      },
    });
  }
}
