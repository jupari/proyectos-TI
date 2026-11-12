import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ErrorApi } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { FechaCortaPipe, HorasPipe } from '../../../shared/pipes';
import { Boton } from '../../../shared/ui/boton/boton';
import { Card } from '../../../shared/ui/card/card';
import { Datepicker } from '../../../shared/ui/datepicker/datepicker';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Switch } from '../../../shared/ui/switch/switch';
import {
  IntegracionesJiraService,
  ResumenImportacionJira,
} from '../data/integraciones-jira.service';

@Component({
  selector: 'app-integraciones',
  templateUrl: './integraciones.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, Card, Datepicker, Select, Switch, FechaCortaPipe, HorasPipe],
})
export class Integraciones {
  private readonly integracionesJiraService = inject(IntegracionesJiraService);
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
}
