import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { ErrorApi, ETIQUETAS_TIPO_RECURSO, TarifaRecurso } from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, FechaCortaPipe, HorasPipe, MonedaPipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Card } from '../../../shared/ui/card/card';
import { Datepicker } from '../../../shared/ui/datepicker/datepicker';
import { Modal } from '../../../shared/ui/modal/modal';
import { Numero } from '../../../shared/ui/numero/numero';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { PestanaTab, Tabs } from '../../../shared/ui/tabs/tabs';
import { CargaMensual, RecursoLista } from '../data/recursos.model';
import { RecursosService } from '../data/recursos.service';
import { TarifasRecursoService } from '../data/tarifas.service';

const PESTANAS: PestanaTab[] = [
  { id: 'datos', etiqueta: 'Datos' },
  { id: 'tarifas', etiqueta: 'Tarifas' },
  { id: 'carga', etiqueta: 'Carga' },
];

function mesIso(desplazamiento: number): string {
  const fecha = new Date();
  fecha.setDate(1);
  fecha.setMonth(fecha.getMonth() + desplazamiento);
  return fecha.toISOString().slice(0, 10);
}

@Component({
  selector: 'app-detalle-recurso',
  templateUrl: './detalle.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    Tabs,
    Card,
    Badge,
    Boton,
    Progreso,
    Numero,
    Datepicker,
    Modal,
    EtiquetaEnumPipe,
    FechaCortaPipe,
    HorasPipe,
    MonedaPipe,
  ],
})
export class DetalleRecurso {
  private readonly recursosService = inject(RecursosService);
  private readonly tarifasService = inject(TarifasRecursoService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly ETIQUETAS_TIPO_RECURSO = ETIQUETAS_TIPO_RECURSO;
  protected readonly pestanas = PESTANAS;

  private readonly id = this.ruta.snapshot.paramMap.get('id')!;
  protected readonly cargando = signal(true);
  protected readonly recurso = signal<RecursoLista | null>(null);
  protected readonly pestanaActiva = signal('datos');

  protected readonly tarifas = signal<TarifaRecurso[]>([]);
  protected readonly carga = signal<CargaMensual[]>([]);
  protected readonly cargandoCarga = signal(false);

  protected readonly puedeEditar = computed(() => this.auth.tienePermiso('recursos.editar'));

  protected readonly dialogoTarifaAbierto = signal(false);
  protected readonly nuevoValorHora = signal<number | null>(null);
  protected readonly nuevaMoneda = signal('COP');
  protected readonly nuevaVigenteDesde = signal<string | null>(null);
  protected readonly guardandoTarifa = signal(false);

  /** Solo informativo en el diálogo: valor_hora x capacidad_horas_mes del
   * recurso, el mismo cálculo que hace el backend al mostrar `valor_mes`. */
  protected readonly nuevoValorMesEstimado = computed(() => {
    const valorHora = this.nuevoValorHora();
    const capacidad = Number(this.recurso()?.capacidad_horas_mes ?? 0);
    return valorHora != null ? valorHora * capacidad : null;
  });

  protected readonly hayTarifaAbierta = computed(() =>
    this.tarifas().some((t) => !t.vigente_hasta),
  );

  constructor() {
    this.cargar();
    this.cargarCarga();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.recursosService.obtenerDetalle(this.id).subscribe({
      next: (recurso) => {
        this.recurso.set(recurso);
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el recurso.' });
        this.cargando.set(false);
      },
    });
    this.recursosService
      .tarifas(this.id)
      .subscribe((tarifas) =>
        this.tarifas.set(
          [...tarifas].sort((a, b) => (a.vigente_desde < b.vigente_desde ? 1 : -1)),
        ),
      );
  }

  private cargarCarga(): void {
    this.cargandoCarga.set(true);
    this.recursosService.carga(this.id, mesIso(-1), mesIso(4)).subscribe({
      next: (carga) => {
        this.carga.set(carga);
        this.cargandoCarga.set(false);
      },
      error: () => this.cargandoCarga.set(false),
    });
  }

  protected cambiarPestana(id: string): void {
    this.pestanaActiva.set(id);
  }

  protected nombreMes(mes: CargaMensual): string {
    const nombres = [
      'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
      'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
    ];
    return `${nombres[mes.mes - 1]} ${mes.anio}`;
  }

  protected abrirDialogoTarifa(): void {
    this.nuevoValorHora.set(null);
    this.nuevaMoneda.set('COP');
    this.nuevaVigenteDesde.set(null);
    this.dialogoTarifaAbierto.set(true);
  }

  protected cerrarDialogoTarifa(): void {
    this.dialogoTarifaAbierto.set(false);
  }

  protected confirmarNuevaTarifa(): void {
    const valorHora = this.nuevoValorHora();
    const vigenteDesde = this.nuevaVigenteDesde();
    if (!valorHora || !vigenteDesde) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Indique el valor por hora y la vigencia.' });
      return;
    }

    this.guardandoTarifa.set(true);
    this.tarifasService
      .crear({
        recurso: this.id,
        valor_hora: valorHora,
        moneda: this.nuevaMoneda(),
        vigente_desde: vigenteDesde,
        vigente_hasta: null,
      })
      .subscribe({
        next: (respuesta) => {
          this.guardandoTarifa.set(false);
          this.dialogoTarifaAbierto.set(false);
          this.cargar();
          for (const aviso of respuesta.avisos) {
            this.toast.mostrar({ tipo: 'alerta', mensaje: aviso });
          }
          this.toast.mostrar({ tipo: 'exito', mensaje: 'Tarifa creada.' });
        },
        error: (error: unknown) => {
          this.guardandoTarifa.set(false);
          let mensaje = 'No se pudo crear la tarifa.';
          if (error instanceof HttpErrorResponse) {
            const cuerpo = error.error as Partial<ErrorApi> | null;
            mensaje = cuerpo?.error?.mensaje ?? mensaje;
          }
          this.toast.mostrar({ tipo: 'error', mensaje });
        },
      });
  }
}
