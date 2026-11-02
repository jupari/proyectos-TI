import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { ToastService } from '../../../core/ui/toast.service';
import { Badge } from '../badge/badge';
import { Boton } from '../boton/boton';
import { Card } from '../card/card';
import { Datepicker } from '../datepicker/datepicker';
import { Drawer } from '../drawer/drawer';
import { EstadoVacio } from '../estado-vacio/estado-vacio';
import { Input } from '../input/input';
import { Modal } from '../modal/modal';
import { Numero } from '../numero/numero';
import { Progreso } from '../progreso/progreso';
import { OpcionSelect, Select } from '../select/select';
import { Semaforo } from '../semaforo/semaforo';
import { Switch } from '../switch/switch';
import { CambioOrden, ColumnaTabla, Tabla } from '../tabla/tabla';
import { PestanaTab, Tabs } from '../tabs/tabs';
import { Textarea } from '../textarea/textarea';

interface FilaDemo {
  id: string;
  codigo: string;
  nombre: string;
  estado: string;
}

const FILAS_DEMO: FilaDemo[] = [
  { id: '1', codigo: 'PRY-001', nombre: 'Modernización ERP', estado: 'EJECUCION' },
  { id: '2', codigo: 'PRY-002', nombre: 'Portal de autoservicio', estado: 'PLANEACION' },
  { id: '3', codigo: 'PRY-003', nombre: 'Migración a la nube', estado: 'CERRADO' },
];

const OPCIONES_POCAS: OpcionSelect[] = [
  { valor: 'BAJA', etiqueta: 'Baja' },
  { valor: 'MEDIA', etiqueta: 'Media' },
  { valor: 'ALTA', etiqueta: 'Alta' },
];

const OPCIONES_MUCHAS: OpcionSelect[] = Array.from({ length: 15 }, (_, i) => ({
  valor: `opcion-${i}`,
  etiqueta: `Opción ${i + 1}`,
}));

/** Ruta interna /dev/catalogo (solo con DEBUG): prueba visual de los 18
 * componentes de shared/ui en todos sus estados. */
@Component({
  selector: 'app-catalogo',
  templateUrl: './catalogo.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    Badge,
    Boton,
    Card,
    Datepicker,
    Drawer,
    EstadoVacio,
    Input,
    Modal,
    Numero,
    Progreso,
    Select,
    Semaforo,
    Switch,
    Tabla,
    Tabs,
    Textarea,
  ],
})
export class Catalogo {
  private readonly toast = inject(ToastService);
  private readonly confirmacion = inject(ConfirmacionService);

  protected readonly textoInput = signal('');
  protected readonly textoConError = signal('valor inválido');
  protected readonly textoArea = signal('');
  protected readonly opcionesPocas = OPCIONES_POCAS;
  protected readonly opcionesMuchas = OPCIONES_MUCHAS;
  protected readonly seleccionPocas = signal<string | null>(null);
  protected readonly seleccionMuchas = signal<string | null>(null);
  protected readonly fecha = signal<string | null>(null);
  protected readonly montoMoneda = signal<number | null>(1250000);
  protected readonly horas = signal<number | null>(8.5);
  protected readonly interruptor = signal(false);

  protected readonly modalAbierto = signal(false);
  protected readonly drawerAbierto = signal(false);

  protected readonly columnas: ColumnaTabla<FilaDemo>[] = [
    { clave: 'codigo', titulo: 'Código', ordenable: true },
    { clave: 'nombre', titulo: 'Nombre', ordenable: true },
    { clave: 'estado', titulo: 'Estado' },
  ];
  protected readonly filasTabla = signal(FILAS_DEMO);
  protected readonly cargandoTabla = signal(false);
  protected readonly ordenTabla = signal<CambioOrden | null>(null);
  protected readonly seleccionTabla = signal<string[]>([]);

  protected readonly pestanas: PestanaTab[] = [
    { id: 'uno', etiqueta: 'Pestaña uno' },
    { id: 'dos', etiqueta: 'Pestaña dos' },
    { id: 'tres', etiqueta: 'Pestaña tres' },
  ];
  protected readonly pestanaActiva = signal('uno');

  protected mostrarToast(tipo: 'exito' | 'alerta' | 'error' | 'info'): void {
    this.toast.mostrar({ tipo, mensaje: `Notificación de tipo "${tipo}".` });
  }

  protected async pedirConfirmacion(): Promise<void> {
    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Borrar proyecto',
      mensaje: '¿Seguro que quiere borrar este proyecto? Esta acción no se puede deshacer.',
      variante: 'peligro',
    });
    this.toast.mostrar({
      tipo: confirmado ? 'exito' : 'info',
      mensaje: confirmado ? 'Confirmado.' : 'Cancelado.',
    });
  }

  protected alternarCargandoTabla(): void {
    this.cargandoTabla.update((valor) => !valor);
  }

  protected alternarFilasVacias(): void {
    this.filasTabla.update((filas) => (filas.length > 0 ? [] : FILAS_DEMO));
  }
}
