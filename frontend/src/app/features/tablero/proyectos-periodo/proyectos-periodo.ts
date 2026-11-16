import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { FilaTableroProyectoPeriodo, TotalesTableroProyectoPeriodo } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { HorasPipe, PorcentajePipe } from '../../../shared/pipes';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { TableroService } from '../data/tablero.service';
import { sincronizarQueryParams } from '../../../core/ui/query-params';

type Periodicidad = 'SEMANAL' | 'MENSUAL';

const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

function aIso(fecha: Date): string {
  return fecha.toISOString().slice(0, 10);
}

function inicioDeSemana(fecha: Date): Date {
  const copia = new Date(fecha);
  const dia = copia.getDay();
  const desplazamiento = dia === 0 ? 6 : dia - 1;
  copia.setDate(copia.getDate() - desplazamiento);
  copia.setHours(0, 0, 0, 0);
  return copia;
}

@Component({
  selector: 'app-proyectos-periodo-tablero',
  templateUrl: './proyectos-periodo.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Boton, EstadoVacio, Select, RouterLink, HorasPipe, PorcentajePipe],
})
export class ProyectosPeriodoTablero {
  private readonly tableroService = inject(TableroService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected readonly periodicidad = signal<Periodicidad>('SEMANAL');
  protected readonly fechaReferencia = signal<Date>(new Date());

  protected readonly cargando = signal(false);
  protected readonly error = signal(false);
  protected readonly exportando = signal(false);
  protected readonly filas = signal<FilaTableroProyectoPeriodo[]>([]);
  protected readonly totales = signal<TotalesTableroProyectoPeriodo | null>(null);

  protected readonly opcionesPeriodicidad: OpcionSelect[] = [
    { valor: 'SEMANAL', etiqueta: 'Semanal' },
    { valor: 'MENSUAL', etiqueta: 'Mensual' },
  ];

  protected readonly rango = computed<{ desde: Date; hasta: Date }>(() => {
    const ref = this.fechaReferencia();
    if (this.periodicidad() === 'MENSUAL') {
      return {
        desde: new Date(ref.getFullYear(), ref.getMonth(), 1),
        hasta: new Date(ref.getFullYear(), ref.getMonth() + 1, 0),
      };
    }
    const desde = inicioDeSemana(ref);
    const hasta = new Date(desde);
    hasta.setDate(hasta.getDate() + 6);
    return { desde, hasta };
  });

  protected readonly rangoTexto = computed(() => {
    const { desde, hasta } = this.rango();
    if (this.periodicidad() === 'MENSUAL') {
      return `${MESES[desde.getMonth()]} de ${desde.getFullYear()}`;
    }
    const fmt = (f: Date) => `${f.getDate()} de ${MESES[f.getMonth()].toLowerCase()}`;
    return `Semana del ${fmt(desde)} al ${fmt(hasta)} de ${hasta.getFullYear()}`;
  });

  constructor() {
    const parametros = this.ruta.snapshot.queryParamMap;
    const periodicidadUrl = parametros.get('periodicidad');
    if (periodicidadUrl === 'MENSUAL' || periodicidadUrl === 'SEMANAL') {
      this.periodicidad.set(periodicidadUrl);
    }
    const fechaUrl = parametros.get('fecha');
    if (fechaUrl) {
      this.fechaReferencia.set(new Date(`${fechaUrl}T00:00:00`));
    }
    this.cargar();
  }

  protected navegar(direccion: -1 | 0 | 1): void {
    if (direccion === 0) {
      this.fechaReferencia.set(new Date());
    } else if (this.periodicidad() === 'MENSUAL') {
      const ref = this.fechaReferencia();
      this.fechaReferencia.set(new Date(ref.getFullYear(), ref.getMonth() + direccion, 1));
    } else {
      const ref = new Date(this.fechaReferencia());
      ref.setDate(ref.getDate() + direccion * 7);
      this.fechaReferencia.set(ref);
    }
    this.cargar();
  }

  protected alCambiarPeriodicidad(valor: string | null): void {
    this.periodicidad.set((valor as Periodicidad) ?? 'SEMANAL');
    this.cargar();
  }

  private sincronizarUrl(): void {
    sincronizarQueryParams(this.router, this.ruta, {
      periodicidad: this.periodicidad(),
      fecha: aIso(this.fechaReferencia()),
    });
  }

  protected cargar(refrescar = false): void {
    this.sincronizarUrl();
    const { desde, hasta } = this.rango();
    this.cargando.set(true);
    this.error.set(false);
    this.tableroService
      .proyectosPorPeriodo({ desde: aIso(desde), hasta: aIso(hasta), refrescar: refrescar || undefined })
      .subscribe({
        next: (respuesta) => {
          this.filas.set(respuesta.filas);
          this.totales.set(respuesta.totales);
          this.cargando.set(false);
        },
        error: () => {
          this.error.set(true);
          this.cargando.set(false);
        },
      });
  }

  protected exportarCsv(): void {
    const { desde, hasta } = this.rango();
    this.exportando.set(true);
    this.tableroService
      .exportarCsv('proyectos-por-periodo', { desde: aIso(desde), hasta: aIso(hasta) })
      .subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const enlace = document.createElement('a');
          enlace.href = url;
          enlace.download = 'tablero-proyectos-por-periodo.csv';
          enlace.click();
          URL.revokeObjectURL(url);
          this.exportando.set(false);
        },
        error: () => {
          this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo exportar el CSV.' });
          this.exportando.set(false);
        },
      });
  }
}
