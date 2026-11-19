import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';

import { Area, ErrorApi, PerfilRecurso, Portafolio } from '../../../core/models';
import { ConfirmacionService } from '../../../core/ui/confirmacion.service';
import { ToastService } from '../../../core/ui/toast.service';
import { Boton } from '../../../shared/ui/boton/boton';
import { CabeceraAdmin } from '../../../shared/ui/cabecera-admin/cabecera-admin';
import { FichaResumen } from '../../../shared/ui/ficha-resumen/ficha-resumen';
import { Input } from '../../../shared/ui/input/input';
import { Modal } from '../../../shared/ui/modal/modal';
import { Numero } from '../../../shared/ui/numero/numero';
import { OpcionSelect, Select } from '../../../shared/ui/select/select';
import { Textarea } from '../../../shared/ui/textarea/textarea';
import { PestanaTab, Tabs } from '../../../shared/ui/tabs/tabs';
import { AreasService, PerfilesRecursoService, PortafoliosService } from '../data/catalogos.service';
import { UsuariosService } from '../data/usuarios.service';

type TipoCatalogo = 'areas' | 'portafolios' | 'perfiles';

interface ServicioCatalogoGenerico {
  crear: (cuerpo: Record<string, unknown>) => Observable<unknown>;
  actualizar: (id: string, cuerpo: Record<string, unknown>) => Observable<unknown>;
  eliminar: (id: string) => Observable<unknown>;
}

interface FilaCatalogo {
  item: Area | Portafolio | PerfilRecurso;
  codigo: string;
  nombre: string;
  detalle: string;
}

interface TextosCatalogo {
  etiqueta: string;
  singular: string;
  ayuda: string;
  vacio: string;
  columnaDetalle: string;
}

/** Textos de cada catálogo: nombre de la pestaña, botón de alta, ayuda y columna extra. */
const TEXTOS: Record<TipoCatalogo, TextosCatalogo> = {
  areas: {
    etiqueta: 'Áreas',
    singular: 'Nueva área',
    ayuda: 'Dependencias que solicitan proyectos y a las que se les mide el portafolio.',
    vacio: 'Sin áreas registradas.',
    columnaDetalle: 'Responsable',
  },
  portafolios: {
    etiqueta: 'Portafolios',
    singular: 'Nuevo portafolio',
    ayuda: 'Agrupaciones de proyectos para reportar a la gerencia.',
    vacio: 'Sin portafolios registrados.',
    columnaDetalle: 'Descripción',
  },
  perfiles: {
    etiqueta: 'Perfiles de recurso',
    singular: 'Nuevo perfil',
    ayuda: 'Cargos con una tarifa por hora de referencia para estimar costos.',
    vacio: 'Sin perfiles registrados.',
    columnaDetalle: 'Tarifa por hora',
  },
};

@Component({
  selector: 'app-catalogos',
  templateUrl: './catalogos.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Tabs, Boton, CabeceraAdmin, FichaResumen, Input, Textarea, Numero, Select, Modal],
})
export class Catalogos {
  private readonly areasService = inject(AreasService);
  private readonly portafoliosService = inject(PortafoliosService);
  private readonly perfilesService = inject(PerfilesRecursoService);
  private readonly usuariosService = inject(UsuariosService);
  private readonly confirmacion = inject(ConfirmacionService);
  private readonly toast = inject(ToastService);

  protected readonly textos = TEXTOS;
  protected readonly pestanas = computed<PestanaTab[]>(() => [
    { id: 'areas', etiqueta: `${TEXTOS.areas.etiqueta} · ${this.areas().length}` },
    { id: 'portafolios', etiqueta: `${TEXTOS.portafolios.etiqueta} · ${this.portafolios().length}` },
    { id: 'perfiles', etiqueta: `${TEXTOS.perfiles.etiqueta} · ${this.perfiles().length}` },
  ]);
  protected readonly pestanaActiva = signal<TipoCatalogo>('areas');

  protected readonly areas = signal<Area[]>([]);
  protected readonly portafolios = signal<Portafolio[]>([]);
  protected readonly perfiles = signal<PerfilRecurso[]>([]);
  protected readonly opcionesResponsables = signal<OpcionSelect[]>([]);

  /** Filas de la pestaña activa con la misma forma, para pintarlas con una sola tabla. */
  protected readonly filas = computed<FilaCatalogo[]>(() => {
    const tipo = this.pestanaActiva();
    if (tipo === 'areas') {
      return this.areas().map((a) => ({
        item: a,
        codigo: a.codigo,
        nombre: a.nombre,
        detalle: this.nombreResponsable(a.responsable),
      }));
    }
    if (tipo === 'portafolios') {
      return this.portafolios().map((p) => ({
        item: p,
        codigo: p.codigo,
        nombre: p.nombre,
        detalle: p.descripcion || '—',
      }));
    }
    return this.perfiles().map((p) => ({
      item: p,
      codigo: p.codigo,
      nombre: p.nombre,
      detalle: `${Number(p.tarifa_hora_referencia).toLocaleString('es-CO')} ${p.moneda}`,
    }));
  });

  protected readonly modalAbierto = signal(false);
  protected readonly tipoEnEdicion = signal<TipoCatalogo>('areas');
  protected readonly idEnEdicion = signal<string | null>(null);
  protected readonly guardando = signal(false);
  protected readonly erroresPorCampo = signal<Record<string, string[]>>({});

  protected readonly codigo = signal('');
  protected readonly nombre = signal('');
  protected readonly descripcion = signal('');
  protected readonly responsable = signal<string | null>(null);
  protected readonly tarifaHoraReferencia = signal<number | null>(null);
  protected readonly moneda = signal('COP');

  constructor() {
    this.cargarTodo();
  }

  private cargarTodo(): void {
    this.areasService.listar({ page_size: 200 }).subscribe((r) => this.areas.set(r.results));
    this.portafoliosService
      .listar({ page_size: 200 })
      .subscribe((r) => this.portafolios.set(r.results));
    this.perfilesService.listar({ page_size: 200 }).subscribe((r) => this.perfiles.set(r.results));
    this.usuariosService
      .listar({ page_size: 200, ordering: 'nombres' })
      .subscribe((r) =>
        this.opcionesResponsables.set(
          r.results.map((u) => ({ valor: u.id, etiqueta: `${u.nombres} ${u.apellidos}` })),
        ),
      );
  }

  private nombreResponsable(id: string | null): string {
    if (!id) return 'Sin responsable';
    return this.opcionesResponsables().find((o) => o.valor === id)?.etiqueta ?? '—';
  }

  protected cambiarPestana(id: string): void {
    this.pestanaActiva.set(id as TipoCatalogo);
  }

  protected abrirNuevo(tipo: TipoCatalogo): void {
    this.tipoEnEdicion.set(tipo);
    this.idEnEdicion.set(null);
    this.codigo.set('');
    this.nombre.set('');
    this.descripcion.set('');
    this.responsable.set(null);
    this.tarifaHoraReferencia.set(null);
    this.moneda.set('COP');
    this.erroresPorCampo.set({});
    this.modalAbierto.set(true);
  }

  protected abrirEditar(tipo: TipoCatalogo, item: Area | Portafolio | PerfilRecurso): void {
    this.tipoEnEdicion.set(tipo);
    this.idEnEdicion.set(item.id);
    this.codigo.set(item.codigo);
    this.nombre.set(item.nombre);
    this.descripcion.set('descripcion' in item ? item.descripcion : '');
    this.responsable.set('responsable' in item ? item.responsable : null);
    this.tarifaHoraReferencia.set(
      'tarifa_hora_referencia' in item ? Number(item.tarifa_hora_referencia) : null,
    );
    this.moneda.set('moneda' in item ? item.moneda : 'COP');
    this.erroresPorCampo.set({});
    this.modalAbierto.set(true);
  }

  protected cerrarModal(): void {
    this.modalAbierto.set(false);
  }

  /** Las tres clases concretas de `ApiService<T>` no son intercambiables en
   * TypeScript (cada una fija un `T` distinto), así que se exponen aquí
   * tras un único tipo estructural; el tipo real de cada respuesta no
   * importa porque este componente solo recarga la lista al terminar. */
  private servicioDe(tipo: TipoCatalogo): ServicioCatalogoGenerico {
    const servicio =
      tipo === 'areas'
        ? this.areasService
        : tipo === 'portafolios'
          ? this.portafoliosService
          : this.perfilesService;
    return servicio as unknown as ServicioCatalogoGenerico;
  }

  private cuerpoDe(tipo: TipoCatalogo): Record<string, unknown> {
    if (tipo === 'areas') {
      return { codigo: this.codigo(), nombre: this.nombre(), responsable: this.responsable() };
    }
    if (tipo === 'portafolios') {
      return {
        codigo: this.codigo(),
        nombre: this.nombre(),
        descripcion: this.descripcion(),
        responsable: this.responsable(),
      };
    }
    return {
      codigo: this.codigo(),
      nombre: this.nombre(),
      tarifa_hora_referencia: this.tarifaHoraReferencia() ?? 0,
      moneda: this.moneda(),
    };
  }

  protected guardar(): void {
    if (!this.codigo() || !this.nombre()) {
      this.toast.mostrar({ tipo: 'error', mensaje: 'Complete el código y el nombre.' });
      return;
    }

    const tipo = this.tipoEnEdicion();
    const id = this.idEnEdicion();
    const servicio = this.servicioDe(tipo);
    const cuerpo = this.cuerpoDe(tipo);

    this.guardando.set(true);
    this.erroresPorCampo.set({});
    const peticion = id ? servicio.actualizar(id, cuerpo) : servicio.crear(cuerpo);

    peticion.subscribe({
      next: () => {
        this.guardando.set(false);
        this.modalAbierto.set(false);
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Guardado correctamente.' });
        this.cargarTodo();
      },
      error: (error: unknown) => {
        this.guardando.set(false);
        if (error instanceof HttpErrorResponse) {
          const cuerpoError = error.error as Partial<ErrorApi> | null;
          this.erroresPorCampo.set(cuerpoError?.error?.detalles ?? {});
          this.toast.mostrar({
            tipo: 'error',
            mensaje: cuerpoError?.error?.mensaje ?? 'No se pudo guardar.',
          });
        }
      },
    });
  }

  protected async eliminar(tipo: TipoCatalogo, item: Area | Portafolio | PerfilRecurso): Promise<void> {
    const confirmado = await this.confirmacion.confirmar({
      titulo: 'Desactivar',
      mensaje: `¿Desactivar «${item.nombre}»?`,
      variante: 'peligro',
      textoConfirmar: 'Desactivar',
    });
    if (!confirmado) return;

    this.servicioDe(tipo).eliminar(item.id).subscribe({
      next: () => {
        this.toast.mostrar({ tipo: 'exito', mensaje: 'Desactivado correctamente.' });
        this.cargarTodo();
      },
      error: (error: unknown) => {
        let mensaje = 'No se pudo desactivar.';
        if (error instanceof HttpErrorResponse && error.status === 409) {
          const cuerpo = error.error as Partial<ErrorApi> | null;
          const referencias = (cuerpo?.error?.detalles as { referencias?: Record<string, string> })
            ?.referencias;
          const detalle = referencias
            ? Object.entries(referencias)
                .map(([clave, conteo]) => `${conteo} ${clave}`)
                .join(', ')
            : '';
          mensaje = `Está en uso${detalle ? ` (${detalle})` : ''} y no se puede desactivar.`;
        }
        this.toast.mostrar({ tipo: 'error', mensaje });
      },
    });
  }
}
