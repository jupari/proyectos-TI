import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ErrorApi } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { FechaCortaPipe, HorasPipe } from '../../../shared/pipes';
import { Boton } from '../../../shared/ui/boton/boton';
import { CabeceraAdmin } from '../../../shared/ui/cabecera-admin/cabecera-admin';
import { Card } from '../../../shared/ui/card/card';
import { FichaResumen } from '../../../shared/ui/ficha-resumen/ficha-resumen';
import { Datepicker } from '../../../shared/ui/datepicker/datepicker';
import { Input } from '../../../shared/ui/input/input';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Switch } from '../../../shared/ui/switch/switch';
import { RecursosService } from '../../recursos/data/recursos.service';
import {
  IntegracionesJiraService,
  PersonaJiraSinMapear,
  ResumenImportacionJira,
  ResumenTareasJira,
} from '../data/integraciones-jira.service';

@Component({
  selector: 'app-integraciones',
  templateUrl: './integraciones.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    Boton,
    CabeceraAdmin,
    Card,
    FichaResumen,
    Datepicker,
    Input,
    Select,
    Switch,
    FechaCortaPipe,
    HorasPipe,
  ],
})
export class Integraciones {
  private readonly integracionesJiraService = inject(IntegracionesJiraService);
  private readonly recursosService = inject(RecursosService);
  private readonly toast = inject(ToastService);

  protected readonly cargando = signal(true);
  protected readonly guardando = signal(false);
  protected readonly autoAprobarImportados = signal(false);

  protected readonly fechaDesde = signal<string | null>(null);
  protected readonly fechaHasta = signal<string | null>(null);
  protected readonly modoAprobacion = signal<'ENVIADO' | 'APROBADO'>('ENVIADO');
  protected readonly soloSimular = signal(false);
  protected readonly importando = signal(false);
  protected readonly resumen = signal<ResumenImportacionJira | null>(null);

  protected readonly opcionesAprobacion: OpcionSelect[] = [
    { valor: 'ENVIADO', etiqueta: 'Pendientes de aprobación' },
    { valor: 'APROBADO', etiqueta: 'Aprobadas automáticamente' },
  ];

  protected readonly claveProyectoJira = signal('');
  protected readonly desdeTareas = signal<string | null>(null);
  protected readonly simulandoTareas = signal(false);
  protected readonly resumenTareas = signal<ResumenTareasJira | null>(null);
  protected readonly clavesPorTipo = (resumen: ResumenTareasJira): [string, number][] =>
    Object.entries(resumen.por_tipo);

  protected readonly TAMANO_PAGINA_TAREAS = 25;
  protected readonly paginaTareas = signal(1);
  protected readonly totalPaginasTareas = computed(() =>
    Math.max(
      1,
      Math.ceil((this.resumenTareas()?.detalle.length ?? 0) / this.TAMANO_PAGINA_TAREAS),
    ),
  );
  protected readonly filasPaginaTareas = computed(() => {
    const inicio = (this.paginaTareas() - 1) * this.TAMANO_PAGINA_TAREAS;
    return (this.resumenTareas()?.detalle ?? []).slice(inicio, inicio + this.TAMANO_PAGINA_TAREAS);
  });

  protected irAPaginaTareas(pagina: number): void {
    this.paginaTareas.set(Math.min(Math.max(1, pagina), this.totalPaginasTareas()));
  }

  protected readonly buscandoPersonas = signal(false);
  protected readonly personasSinMapear = signal<PersonaJiraSinMapear[] | null>(null);
  protected readonly opcionesRecursos = signal<OpcionSelect[]>([]);
  protected readonly recursoElegidoPorCuenta = signal<Record<string, string>>({});
  protected readonly asociandoCuenta = signal<string | null>(null);

  constructor() {
    this.integracionesJiraService.obtenerConfiguracion().subscribe({
      next: (configuracion) => {
        this.autoAprobarImportados.set(configuracion.auto_aprobar_importados);
        this.modoAprobacion.set(configuracion.auto_aprobar_importados ? 'APROBADO' : 'ENVIADO');
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la configuración.' });
        this.cargando.set(false);
      },
    });
  }

  protected cambiarAutoAprobar(valor: boolean): void {
    const anterior = this.autoAprobarImportados();
    this.autoAprobarImportados.set(valor);
    this.guardando.set(true);
    this.integracionesJiraService.actualizarConfiguracion({ auto_aprobar_importados: valor }).subscribe({
      next: () => {
        this.guardando.set(false);
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Configuración guardada.' });
      },
      error: () => {
        this.guardando.set(false);
        this.autoAprobarImportados.set(anterior);
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo guardar la configuración.' });
      },
    });
  }

  protected importarAhora(): void {
    const desde = this.fechaDesde();
    const hasta = this.fechaHasta();
    if (!desde || !hasta) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Elija la fecha desde y hasta.' });
      return;
    }
    if (hasta < desde) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'La fecha hasta debe ser igual o posterior a desde.' });
      return;
    }

    this.importando.set(true);
    this.resumen.set(null);
    this.integracionesJiraService
      .importarHoras({
        desde,
        hasta,
        dry_run: this.soloSimular(),
        auto_aprobar: this.modoAprobacion() === 'APROBADO',
      })
      .subscribe({
        next: (resumen) => {
          this.importando.set(false);
          this.resumen.set(resumen);
          this.toast.mostrar({
            tipo: 'exito',
            mensaje: this.soloSimular()
              ? 'Simulación terminada: no se escribió nada.'
              : `Importación terminada: ${resumen.creados} creados, ${resumen.actualizados} actualizados.`,
          });
        },
        error: (error: unknown) => {
          this.importando.set(false);
          let mensaje = 'No se pudo completar la importación.';
          if (error instanceof HttpErrorResponse) {
            const cuerpoError = error.error as Partial<ErrorApi> | null;
            mensaje = cuerpoError?.error?.mensaje ?? mensaje;
          }
          this.toast.mostrar({ tipo: 'error', mensaje });
        },
      });
  }

  protected simularTareas(): void {
    const clave = this.claveProyectoJira().trim();
    if (!clave) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Escriba la clave del proyecto de Jira.' });
      return;
    }
    this.simulandoTareas.set(true);
    this.resumenTareas.set(null);
    this.paginaTareas.set(1);
    this.integracionesJiraService
      .simularImportacionTareas(clave, this.desdeTareas() ?? undefined)
      .subscribe({
        next: (resumen) => {
          this.simulandoTareas.set(false);
          this.resumenTareas.set(resumen);
        },
        error: (error: unknown) => {
          this.simulandoTareas.set(false);
          let mensaje = 'No se pudo leer el proyecto de Jira.';
          if (error instanceof HttpErrorResponse) {
            const cuerpoError = error.error as Partial<ErrorApi> | null;
            mensaje = cuerpoError?.error?.mensaje ?? mensaje;
          }
          this.toast.mostrar({ tipo: 'error', mensaje });
        },
      });
  }

  protected buscarPersonasSinMapear(): void {
    const desde = this.fechaDesde();
    const hasta = this.fechaHasta();
    if (!desde || !hasta) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Elija la fecha desde y hasta.' });
      return;
    }
    if (hasta < desde) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'La fecha hasta debe ser igual o posterior a desde.' });
      return;
    }

    if (this.opcionesRecursos().length === 0) {
      this.recursosService
        .listarRecursos({ page_size: 200 })
        .subscribe((r) =>
          this.opcionesRecursos.set(r.results.map((x) => ({ valor: x.id, etiqueta: x.nombre }))),
        );
    }

    this.buscandoPersonas.set(true);
    this.personasSinMapear.set(null);
    this.integracionesJiraService.listarPersonasSinMapear(desde, hasta).subscribe({
      next: (personas) => {
        this.buscandoPersonas.set(false);
        this.personasSinMapear.set(personas);
      },
      error: (error: unknown) => {
        this.buscandoPersonas.set(false);
        let mensaje = 'No se pudo buscar las personas sin asociar.';
        if (error instanceof HttpErrorResponse) {
          const cuerpoError = error.error as Partial<ErrorApi> | null;
          mensaje = cuerpoError?.error?.mensaje ?? mensaje;
        }
        this.toast.mostrar({ tipo: 'error', mensaje });
      },
    });
  }

  protected elegirRecursoPara(cuentaJira: string, recursoId: string): void {
    this.recursoElegidoPorCuenta.update((actual) => ({ ...actual, [cuentaJira]: recursoId }));
  }

  protected asociar(persona: PersonaJiraSinMapear): void {
    const recursoId = this.recursoElegidoPorCuenta()[persona.jira_account_id];
    if (!recursoId) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Elija a qué recurso corresponde.' });
      return;
    }

    this.asociandoCuenta.set(persona.jira_account_id);
    this.recursosService
      .actualizarRecurso(recursoId, { jira_account_id: persona.jira_account_id })
      .subscribe({
        next: () => {
          this.asociandoCuenta.set(null);
          this.personasSinMapear.set(
            (this.personasSinMapear() ?? []).filter(
              (p) => p.jira_account_id !== persona.jira_account_id,
            ),
          );
          this.toast.mostrar({
            tipo: 'exito',
            mensaje: `«${persona.nombre}» quedó asociado. Vuelva a importar para traer sus horas.`,
          });
        },
        error: (error: unknown) => {
          this.asociandoCuenta.set(null);
          let mensaje = 'No se pudo guardar la asociación.';
          if (error instanceof HttpErrorResponse) {
            const cuerpoError = error.error as Partial<ErrorApi> | null;
            mensaje = cuerpoError?.error?.mensaje ?? mensaje;
          }
          this.toast.mostrar({ tipo: 'error', mensaje });
        },
      });
  }
}
