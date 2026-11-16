import { NgTemplateOutlet } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import {
  CompromisoSeguimiento,
  DocumentoExpediente,
  ETIQUETAS_CATEGORIA_DOCUMENTO,
  ETIQUETAS_ESTADO_COMPROMISO,
  ETIQUETAS_ESTADO_SEGUIMIENTO,
  ETIQUETAS_PERIODICIDAD,
  Seguimiento,
} from '../../../core/models';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, FechaCortaPipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Modal } from '../../../shared/ui/modal/modal';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Semaforo, ValorSemaforo } from '../../../shared/ui/semaforo/semaforo';
import { DocumentosService } from '../../expediente/data/documentos.service';
import { ProyectosService } from '../../proyectos/data/proyectos.service';
import { CompromisosService } from '../data/compromisos.service';
import { FiltrosSeguimiento } from '../data/seguimientos.model';
import { SeguimientosService } from '../data/seguimientos.service';
import { sincronizarQueryParams } from '../../../core/ui/query-params';

/** Tope de seguimientos que se traen de una vez para agrupar en el
 * cliente por proyecto (no hay endpoint de agregación en el backend).
 * Coincide con `PaginacionEstandar.max_page_size` (backend): pedir más no
 * sirve, la API lo recorta en silencio a ese valor. A este ritmo de uso
 * (semanal/mensual) alcanza para bastante histórico; si algún día se
 * supera, se avisa en vez de agrupar mal por datos faltantes. */
const TOPE_SEGUIMIENTOS = 200;

interface GrupoProyecto {
  proyecto: string;
  proyecto_codigo: string;
  proyecto_nombre: string;
  ultimo: Seguimiento;
  historial: Seguimiento[];
}

@Component({
  selector: 'app-lista-seguimientos',
  templateUrl: './lista.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    NgTemplateOutlet,
    RouterLink,
    Boton,
    Badge,
    Semaforo,
    Select,
    EstadoVacio,
    Modal,
    EtiquetaEnumPipe,
    FechaCortaPipe,
  ],
})
export class ListaSeguimientos {
  private readonly seguimientosService = inject(SeguimientosService);
  private readonly proyectosService = inject(ProyectosService);
  private readonly compromisosService = inject(CompromisosService);
  private readonly documentosService = inject(DocumentosService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected readonly ETIQUETAS_ESTADO_SEGUIMIENTO = ETIQUETAS_ESTADO_SEGUIMIENTO;
  protected readonly ETIQUETAS_PERIODICIDAD = ETIQUETAS_PERIODICIDAD;
  protected readonly ETIQUETAS_ESTADO_COMPROMISO = ETIQUETAS_ESTADO_COMPROMISO;
  protected readonly ETIQUETAS_CATEGORIA_DOCUMENTO = ETIQUETAS_CATEGORIA_DOCUMENTO;

  protected readonly cargando = signal(false);
  protected readonly grupos = signal<GrupoProyecto[]>([]);
  protected readonly expandidos = signal<ReadonlySet<string>>(new Set());

  protected readonly proyecto = signal<string | null>(null);
  protected readonly periodicidad = signal<string | null>(null);
  protected readonly estado = signal<string | null>(null);

  protected readonly opcionesProyectos = signal<OpcionSelect[]>([]);
  protected readonly opcionesPeriodicidad: OpcionSelect[] = [
    { valor: 'DIARIA', etiqueta: 'Diaria' },
    { valor: 'SEMANAL', etiqueta: 'Semanal' },
    { valor: 'MENSUAL', etiqueta: 'Mensual' },
  ];
  protected readonly opcionesEstado: OpcionSelect[] = [
    { valor: 'BORRADOR', etiqueta: 'Borrador' },
    { valor: 'PUBLICADO', etiqueta: 'Publicado' },
  ];

  protected readonly puedeCrear = computed(() => this.auth.tienePermiso('seguimientos.crear'));

  protected readonly detalleAbierto = signal(false);
  protected readonly detalleSeguimiento = signal<Seguimiento | null>(null);
  protected readonly detalleCompromisos = signal<CompromisoSeguimiento[]>([]);
  protected readonly detalleDocumentos = signal<DocumentoExpediente[]>([]);
  protected readonly cargandoDetalle = signal(false);

  constructor() {
    const parametros = this.ruta.snapshot.queryParamMap;
    this.proyecto.set(parametros.get('proyecto'));
    this.periodicidad.set(parametros.get('periodicidad'));
    this.estado.set(parametros.get('estado'));

    this.proyectosService
      .listarProyectos({ page_size: 200 })
      .subscribe((r) =>
        this.opcionesProyectos.set(
          r.results.map((p) => ({ valor: p.id, etiqueta: `${p.codigo} — ${p.nombre}` })),
        ),
      );
    this.cargar();
  }

  private filtrosActuales(): FiltrosSeguimiento {
    return {
      proyecto: this.proyecto() ?? undefined,
      periodicidad: this.periodicidad() ?? undefined,
      estado: this.estado() ?? undefined,
      ordering: '-fecha_corte',
      page_size: TOPE_SEGUIMIENTOS,
    };
  }

  protected cargar(): void {
    this.cargando.set(true);
    this.sincronizarUrl();
    this.seguimientosService.listarSeguimientos(this.filtrosActuales()).subscribe({
      next: (respuesta) => {
        this.grupos.set(this.agrupar(respuesta.results));
        this.expandidos.set(new Set());
        this.cargando.set(false);
        if (respuesta.count > TOPE_SEGUIMIENTOS) {
          this.toast.mostrar({
            tipo: 'alerta',
            mensaje:
              `Hay ${respuesta.count} seguimientos y solo se muestran los ${TOPE_SEGUIMIENTOS} ` +
              'más recientes; use el filtro de proyecto para acotar.',
          });
        }
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la lista de seguimientos.' });
        this.cargando.set(false);
      },
    });
  }

  private agrupar(seguimientos: Seguimiento[]): GrupoProyecto[] {
    const porProyecto = new Map<string, Seguimiento[]>();
    for (const s of seguimientos) {
      const lista = porProyecto.get(s.proyecto) ?? [];
      lista.push(s);
      porProyecto.set(s.proyecto, lista);
    }

    const grupos: GrupoProyecto[] = [];
    for (const [proyectoId, lista] of porProyecto) {
      const [ultimo, ...historial] = lista;
      grupos.push({
        proyecto: proyectoId,
        proyecto_codigo: ultimo.proyecto_codigo,
        proyecto_nombre: ultimo.proyecto_nombre,
        ultimo,
        historial,
      });
    }
    grupos.sort((a, b) => a.proyecto_nombre.localeCompare(b.proyecto_nombre));
    return grupos;
  }

  private sincronizarUrl(): void {
    const queryParams: Record<string, string> = {};
    if (this.proyecto()) queryParams['proyecto'] = this.proyecto()!;
    if (this.periodicidad()) queryParams['periodicidad'] = this.periodicidad()!;
    if (this.estado()) queryParams['estado'] = this.estado()!;
    sincronizarQueryParams(this.router, this.ruta, queryParams);
  }

  protected aplicarFiltros(): void {
    this.cargar();
  }

  protected limpiarFiltros(): void {
    this.proyecto.set(null);
    this.periodicidad.set(null);
    this.estado.set(null);
    this.aplicarFiltros();
  }

  protected estaExpandido(proyectoId: string): boolean {
    return this.expandidos().has(proyectoId);
  }

  protected alternarExpandido(proyectoId: string): void {
    this.expandidos.update((actual) => {
      const nuevo = new Set(actual);
      if (nuevo.has(proyectoId)) {
        nuevo.delete(proyectoId);
      } else {
        nuevo.add(proyectoId);
      }
      return nuevo;
    });
  }

  protected esValorSemaforo(valor: string): ValorSemaforo {
    return valor as ValorSemaforo;
  }

  protected abrirDetalle(seguimiento: Seguimiento): void {
    this.detalleSeguimiento.set(seguimiento);
    this.detalleCompromisos.set([]);
    this.detalleDocumentos.set([]);
    this.detalleAbierto.set(true);
    this.cargandoDetalle.set(true);

    forkJoin({
      compromisos: this.compromisosService.listar({ seguimiento: seguimiento.id, page_size: 200 }),
      documentos: this.documentosService.listar({ seguimiento: seguimiento.id, page_size: 200 }),
    }).subscribe({
      next: ({ compromisos, documentos }) => {
        this.detalleCompromisos.set(compromisos.results);
        this.detalleDocumentos.set(documentos.results);
        this.cargandoDetalle.set(false);
      },
      error: () => {
        this.cargandoDetalle.set(false);
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el detalle del seguimiento.' });
      },
    });
  }

  protected cerrarDetalle(): void {
    this.detalleAbierto.set(false);
  }

  protected descargarAdjunto(documento: DocumentoExpediente): void {
    this.documentosService.descargar(documento.id).subscribe((blob) => {
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = documento.nombre_original;
      enlace.click();
      URL.revokeObjectURL(url);
    });
  }
}
