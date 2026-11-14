import { JsonPipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  OnInit,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  DocumentoExpediente,
  ETIQUETAS_CATEGORIA_DOCUMENTO,
  ETIQUETAS_TIPO_EVENTO,
} from '../../../core/models';
import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { ToastService } from '../../../core/ui/toast.service';
import { EtiquetaEnumPipe, FechaCortaPipe } from '../../../shared/pipes';
import { Boton } from '../../../shared/ui/boton/boton';
import { Datepicker } from '../../../shared/ui/datepicker/datepicker';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { PestanaTab, Tabs } from '../../../shared/ui/tabs/tabs';
import { ProyectosService } from '../../proyectos/data/proyectos.service';
import { BitacoraService } from '../data/bitacora.service';
import { DocumentosService } from '../data/documentos.service';

const PESTANAS_PRINCIPALES: PestanaTab[] = [
  { id: 'documentos', etiqueta: 'Documentos' },
  { id: 'linea-tiempo', etiqueta: 'Línea de tiempo' },
];

const EXTENSION_PERMITIDA = /\.(pdf|docx|xlsx|pptx|png|jpe?g|msg|txt|csv|zip)$/i;
const TAMANO_MAXIMO_MB = 25;

@Component({
  selector: 'app-panel-expediente',
  templateUrl: './panel-expediente.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    Tabs,
    Boton,
    Select,
    Datepicker,
    EstadoVacio,
    EtiquetaEnumPipe,
    FechaCortaPipe,
    JsonPipe,
  ],
})
export class PanelExpediente implements OnInit {
  readonly proyectoId = input.required<string>();

  private readonly proyectosService = inject(ProyectosService);
  private readonly documentosService = inject(DocumentosService);
  private readonly bitacoraService = inject(BitacoraService);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly toast = inject(ToastService);

  protected readonly ETIQUETAS_TIPO_EVENTO = ETIQUETAS_TIPO_EVENTO;
  protected readonly pestanasPrincipales = PESTANAS_PRINCIPALES;
  protected readonly pestanaActiva = signal('documentos');

  protected readonly cargando = signal(true);
  protected readonly documentosPorCategoria = signal<Record<string, DocumentoExpediente[]>>({});
  protected readonly totales = signal<{
    documentos: number;
    seguimientos_publicados: number;
    horas_acumuladas: number;
    costo_acumulado: number;
    tareas_cerradas: number;
  } | null>(null);

  protected readonly categoriaActiva = signal<string | null>(null);
  protected readonly pestanasCategoria = computed<PestanaTab[]>(() =>
    Object.keys(this.documentosPorCategoria()).map((categoria) => ({
      id: categoria,
      etiqueta:
        ETIQUETAS_CATEGORIA_DOCUMENTO[categoria as keyof typeof ETIQUETAS_CATEGORIA_DOCUMENTO] ??
        categoria,
    })),
  );

  protected readonly arrastrando = signal(false);
  protected readonly subiendo = signal(false);
  protected readonly progreso = signal(0);
  protected readonly categoriaNueva = signal('OTRO');
  protected readonly opcionesCategoria: OpcionSelect[] = Object.entries(
    ETIQUETAS_CATEGORIA_DOCUMENTO,
  ).map(([valor, etiqueta]) => ({ valor, etiqueta }));

  protected readonly cargandoLinea = signal(false);
  protected readonly lineaTiempo = signal<
    { id: string; tipo_evento: string; descripcion: string; ocurrido_en: string; usuario_nombre: string | null; datos_antes: unknown; datos_despues: unknown }[]
  >([]);
  protected readonly filtroTipoEvento = signal<string | null>(null);
  protected readonly filtroDesde = signal<string | null>(null);
  protected readonly filtroHasta = signal<string | null>(null);
  protected readonly opcionesTipoEvento: OpcionSelect[] = Object.entries(ETIQUETAS_TIPO_EVENTO).map(
    ([valor, etiqueta]) => ({ valor, etiqueta }),
  );

  ngOnInit(): void {
    // `proyectoId` es un input required de signal: no está disponible todavía
    // en el constructor (Angular lo asigna después de construir la
    // instancia), por eso la carga inicial se dispara acá y no ahí.
    this.cargarExpediente();
  }

  protected cambiarPestanaPrincipal(id: string): void {
    this.pestanaActiva.set(id);
    if (id === 'linea-tiempo' && this.lineaTiempo().length === 0) {
      this.cargarLineaTiempo();
    }
  }

  protected cambiarCategoria(id: string): void {
    this.categoriaActiva.set(id);
  }

  private cargarExpediente(): void {
    this.cargando.set(true);
    this.proyectosService.expediente(this.proyectoId()).subscribe({
      next: (datos) => {
        this.documentosPorCategoria.set(datos.documentos_por_categoria);
        this.totales.set(datos.totales);
        const categorias = Object.keys(datos.documentos_por_categoria);
        if (categorias.length > 0 && !this.categoriaActiva()) {
          this.categoriaActiva.set(categorias[0]);
        }
        this.cargando.set(false);
      },
      error: () => {
        this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar el expediente.' });
        this.cargando.set(false);
      },
    });
  }

  protected cargarLineaTiempo(): void {
    this.cargandoLinea.set(true);
    this.bitacoraService
      .listar({
        proyecto: this.proyectoId(),
        tipo_evento: this.filtroTipoEvento() ?? undefined,
        desde: this.filtroDesde() ?? undefined,
        hasta: this.filtroHasta() ?? undefined,
        page_size: 100,
      })
      .subscribe({
        next: (respuesta) => {
          this.lineaTiempo.set(
            respuesta.results.map((e) => ({
              id: e.id,
              tipo_evento: e.tipo_evento,
              descripcion: e.descripcion,
              ocurrido_en: e.ocurrido_en,
              usuario_nombre: e.usuario_nombre,
              datos_antes: e.datos_antes,
              datos_despues: e.datos_despues,
            })),
          );
          this.cargandoLinea.set(false);
        },
        error: () => {
          this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo cargar la línea de tiempo.' });
          this.cargandoLinea.set(false);
        },
      });
  }

  protected aplicarFiltrosLinea(): void {
    this.cargarLineaTiempo();
  }

  // --- subida de documentos --------------------------------------------------

  protected alArrastrarEncima(evento: DragEvent): void {
    evento.preventDefault();
    this.arrastrando.set(true);
  }

  protected alSalirDeArrastre(): void {
    this.arrastrando.set(false);
  }

  protected alSoltar(evento: DragEvent): void {
    evento.preventDefault();
    this.arrastrando.set(false);
    const archivos = evento.dataTransfer?.files;
    if (archivos) this.subirVarios(archivos);
  }

  protected alSeleccionarArchivos(evento: Event): void {
    const input = evento.target as HTMLInputElement;
    if (input.files) this.subirVarios(input.files);
    input.value = '';
  }

  private subirVarios(archivos: FileList): void {
    for (const archivo of Array.from(archivos)) {
      this.validarYSubir(archivo);
    }
  }

  private validarYSubir(archivo: File): void {
    if (!EXTENSION_PERMITIDA.test(archivo.name)) {
      this.toast.mostrar({
        tipo: 'error',
        mensaje: `«${archivo.name}»: extensión no permitida.`,
      });
      return;
    }
    if (archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024) {
      this.toast.mostrar({
        tipo: 'error',
        mensaje: `«${archivo.name}» pesa más de ${TAMANO_MAXIMO_MB} MB.`,
      });
      return;
    }

    this.subiendo.set(true);
    this.progreso.set(0);
    this.documentosService
      .subir(
        { proyecto: this.proyectoId(), categoria: this.categoriaNueva(), nombre: archivo.name },
        archivo,
      )
      .subscribe({
        next: (evento) => {
          if (evento.type === 1 && evento.total) {
            this.progreso.set(Math.round((evento.loaded / evento.total) * 100));
          } else if (evento.type === 4) {
            this.subiendo.set(false);
            this.toast.mostrar({ tipo: 'exito', mensaje: `«${archivo.name}» cargado.` });
            this.cargarExpediente();
          }
        },
        error: (error: { status?: number; error?: { error?: { mensaje?: string } } }) => {
          this.subiendo.set(false);
          if (error.status === 409) {
            this.toast.mostrar({
              tipo: 'alerta',
              mensaje: `Ya existe un documento idéntico a «${archivo.name}».`,
            });
          } else {
            this.toast.mostrar({
              tipo: 'error',
              mensaje: error.error?.error?.mensaje ?? 'No se pudo cargar el archivo.',
            });
          }
        },
      });
  }

  protected subirNuevaVersion(documento: DocumentoExpediente, evento: Event): void {
    const input = evento.target as HTMLInputElement;
    const archivo = input.files?.[0];
    if (!archivo) return;
    this.documentosService.nuevaVersion(documento.id, archivo).subscribe({
      next: (e) => {
        if (e.type === 4) {
          this.toast.mostrar({ tipo: 'exito', mensaje: 'Nueva versión cargada.' });
          this.cargarExpediente();
        }
      },
      error: () => this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo subir la nueva versión.' }),
    });
    input.value = '';
  }

  protected descargar(documento: DocumentoExpediente): void {
    this.documentosService.descargar(documento.id).subscribe((blob) => {
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = documento.nombre_original;
      enlace.click();
      URL.revokeObjectURL(url);
    });
  }

  protected async eliminar(documento: DocumentoExpediente): Promise<void> {
    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Eliminar documento',
      mensaje: `¿Eliminar «${documento.nombre}»? Esta acción es reversible solo por un administrador.`,
      variante: 'peligro',
    });
    if (!confirmado) return;
    this.documentosService.eliminar(documento.id).subscribe({
      next: () => {
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Documento eliminado.' });
        this.cargarExpediente();
      },
      error: () => this.toast.mostrar({ tipo: 'error', mensaje: 'No se pudo eliminar el documento.' }),
    });
  }

  protected exportar(): void {
    this.proyectosService.exportarExpediente(this.proyectoId()).subscribe((blob) => {
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `expediente-${this.proyectoId()}.pdf`;
      enlace.click();
      URL.revokeObjectURL(url);
    });
  }

  protected formatoTamano(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}
