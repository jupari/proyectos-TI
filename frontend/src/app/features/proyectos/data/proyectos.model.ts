import {
  DocumentoExpediente,
  EntradaBitacora,
  FaseProyecto,
  Hito,
  Proyecto,
  ResumenEjecucion,
  ResumenEjecucionReducido,
  RubroPresupuesto,
} from '../../../core/models';

/** Forma de `ProyectoListaSerializer` (backend): el modelo base más los
 * nombres ya resueltos y un `resumen_ejecucion` reducido para la tabla. */
export interface ProyectoLista extends Proyecto {
  area_nombre: string;
  portafolio_nombre: string | null;
  gerente_nombre: string;
  resumen_ejecucion: ResumenEjecucionReducido;
}

/** Forma de `ProyectoDetalleSerializer`: lo anterior más los sub-recursos
 * anidados y el `resumen_ejecucion` completo. */
export interface ProyectoDetalle extends Omit<ProyectoLista, 'resumen_ejecucion'> {
  resumen_ejecucion: ResumenEjecucion;
  fases: FaseProyecto[];
  hitos: Hito[];
  rubros: RubroPresupuesto[];
  /** Clave del proyecto en Jira (p. ej. `PROY`); vacío si no está mapeado (fase 12). */
  clave_jira: string;
}

/** Cuerpo aceptado por `ProyectoEscrituraSerializer`: sin `codigo` (lo
 * genera el servidor) ni `estado` (se cambia solo con `cambiarEstado`). */
export interface ProyectoEscritura {
  nombre: string;
  descripcion: string;
  objetivo: string;
  portafolio: string | null;
  area_solicitante: string;
  gerente: string;
  lider_tecnico: string | null;
  prioridad: string;
  fecha_inicio_plan: string;
  fecha_fin_plan: string;
  fecha_inicio_real: string | null;
  fecha_fin_real: string | null;
  moneda: string;
  presupuesto_horas: number | string;
  presupuesto_dinero: number | string;
  avance_reportado: number | string;
  observaciones: string;
  clave_jira?: string;
  avance_desde_tareas?: boolean;
  en_produccion?: boolean;
  en_soporte?: boolean;
}

/** Fila de `comparativo_por_recurso`/`comparativo_por_mes`
 * (docs/plan/fase-08-ejecucion-ingesta.md §8.2.4). */
export interface FilaComparativoEjecucion {
  recurso?: string;
  recurso_nombre?: string;
  anio?: number;
  mes?: number;
  horas_plan: number;
  horas_ejec: number;
  costo_plan: number;
  costo_ejec: number;
  pct_horas: number | null;
  pct_dinero: number | null;
}

export interface ComparativoEjecucion {
  por_recurso: FilaComparativoEjecucion[];
  por_mes: FilaComparativoEjecucion[];
}

/** `GET /proyectos/{id}/expediente/` (docs/plan/fase-09-seguimiento-expediente.md §9.2.4). */
export interface ExpedienteProyecto {
  documentos_por_categoria: Record<string, DocumentoExpediente[]>;
  linea_tiempo: EntradaBitacora[];
  total_eventos_linea_tiempo: number;
  totales: {
    documentos: number;
    seguimientos_publicados: number;
    horas_acumuladas: number;
    costo_acumulado: number;
    tareas_cerradas: number;
  };
}

export interface FiltrosProyecto {
  search?: string;
  estado?: string;
  en_produccion?: boolean;
  en_soporte?: boolean;
  prioridad?: string;
  portafolio?: string;
  area_solicitante?: string;
  semaforo?: string;
  mis_proyectos?: boolean;
  fecha_inicio_plan__gte?: string;
  fecha_fin_plan__lte?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}
