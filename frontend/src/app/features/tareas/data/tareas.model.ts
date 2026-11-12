import { DependenciaTarea, Tarea } from '../../../core/models';

/** Forma de `TareaListaSerializer` (backend): el modelo base más los
 * nombres ya resueltos y los indicadores calculados para la bandeja. */
export interface TareaLista extends Tarea {
  proyecto_codigo: string;
  fase_nombre: string | null;
  responsable_nombre: string | null;
  dias_atraso: number | null;
  tiene_subtareas: boolean;
  numero_dependencias: number;
}

/** Un nivel de subtarea anidada (`TareaSubtareaSerializer`). */
export interface TareaSubtarea {
  id: string;
  codigo: string;
  nombre: string;
  estado: string;
  prioridad: string;
  responsable: string | null;
  responsable_nombre: string | null;
  horas_estimadas: string;
  horas_ejecutadas: string;
  avance: string;
  fecha_inicio_plan: string;
  fecha_fin_plan: string;
}

export interface DependenciaTareaDetalle extends DependenciaTarea {
  tarea_origen_codigo: string;
  tarea_destino_codigo: string;
}

/** Forma de `TareaDetalleSerializer`: lo anterior más subtareas (un nivel)
 * y las dependencias entrantes/salientes. */
export interface TareaDetalle extends TareaLista {
  descripcion: string;
  subtareas: TareaSubtarea[];
  dependencias_entrantes: DependenciaTareaDetalle[];
  dependencias_salientes: DependenciaTareaDetalle[];
}

/** Cuerpo aceptado por `TareaEscrituraSerializer`: sin `codigo`,
 * `horas_ejecutadas` ni `creada_durante_ejecucion` (los resuelve el servidor). */
export interface TareaEscritura {
  proyecto: string;
  fase: string | null;
  tarea_padre: string | null;
  nombre: string;
  descripcion: string;
  tipo: string;
  prioridad: string;
  responsable: string | null;
  fecha_inicio_plan: string;
  fecha_fin_plan: string;
  fecha_inicio_real: string | null;
  fecha_fin_real: string | null;
  horas_estimadas: number | string;
  avance?: number | string;
  orden?: number;
  motivo_creacion?: string;
  clave_jira?: string | null;
}

export interface FiltrosTarea {
  search?: string;
  proyecto?: string;
  fase?: string;
  estado?: string;
  tipo?: string;
  prioridad?: string;
  responsable?: string;
  tarea_padre?: string;
  vencidas?: boolean;
  creada_durante_ejecucion?: boolean;
  mis_tareas?: boolean;
  ordering?: string;
  page?: number;
  page_size?: number;
}

/** Nodo de `GET /tareas/arbol/?proyecto=` (recursivo). */
export interface NodoArbolTarea {
  id: string;
  codigo: string;
  nombre: string;
  tipo: string;
  estado: string;
  prioridad: string;
  responsable: string | null;
  responsable_nombre: string | null;
  fecha_inicio_plan: string;
  fecha_fin_plan: string;
  horas_estimadas: string;
  horas_ejecutadas: string;
  avance: string;
  orden: number;
  subtareas: NodoArbolTarea[];
}

export interface FechasSugeridas {
  fecha_inicio_sugerida: string | null;
  fecha_fin_sugerida: string | null;
}

/** Fila de `GET /proyectos/{id}/cronograma/`, lista para el Gantt. */
export interface FilaCronograma {
  tarea_id: string;
  codigo: string;
  nombre: string;
  nivel: number;
  fase: string | null;
  inicio_plan: string;
  fin_plan: string;
  inicio_real: string | null;
  fin_real: string | null;
  avance: string;
  estado: string;
  responsable: string | null;
  dependencias: { tarea_id: string; tipo: string; dias_desfase: number }[];
}
