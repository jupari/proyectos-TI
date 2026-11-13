import { Recurso } from '../../../core/models';

/** Forma de `RecursoSerializer` (backend): el modelo base más los campos
 * resueltos para la lista y el detalle. */
export interface RecursoLista extends Recurso {
  perfil_nombre: string | null;
  tarifa_vigente: string | null;
  proyectos_activos: number;
}

export interface RecursoEscritura {
  tipo: string;
  nombre: string;
  usuario: string | null;
  perfil: string | null;
  email: string | null;
  capacidad_horas_mes: number | string;
  fecha_ingreso: string | null;
  fecha_retiro: string | null;
  jira_account_id?: string | null;
}

export interface CargaMensual {
  anio: number;
  mes: number;
  horas_planeadas: number;
  horas_ejecutadas: number;
  capacidad: number;
  pct_ocupacion: number | null;
}

export interface FiltrosRecurso {
  search?: string;
  tipo?: string;
  perfil?: string;
  usuario?: string;
  sin_asignacion?: boolean;
  page?: number;
  page_size?: number;
  ordering?: string;
}
