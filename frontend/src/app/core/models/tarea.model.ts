import { ModeloBase } from './comun.model';
import { EstadoTarea, Prioridad, TipoDependencia, TipoTarea } from './enums';

export interface Tarea extends ModeloBase {
  proyecto: string;
  fase: string | null;
  tarea_padre: string | null;
  codigo: string;
  nombre: string;
  descripcion: string;
  tipo: TipoTarea;
  estado: EstadoTarea;
  prioridad: Prioridad;
  responsable: string | null;
  fecha_inicio_plan: string;
  fecha_fin_plan: string;
  fecha_inicio_real: string | null;
  fecha_fin_real: string | null;
  horas_estimadas: string;
  /** Calculado (C): suma de RegistroEjecucion aprobados de la tarea. */
  horas_ejecutadas: string;
  avance: string;
  orden: number;
  creada_durante_ejecucion: boolean;
  motivo_creacion: string;
  /** Clave del issue en Jira (p. ej. `PROY-123`); vacío si no está asociada (fase 12). */
  clave_jira: string | null;
  /** Datos de Jira (fase 14); solo lectura. */
  sprint?: string | null;
  sprint_nombre?: string | null;
  epica_clave?: string;
  epica_nombre?: string;
}

export interface DependenciaTarea extends ModeloBase {
  tarea_origen: string;
  tarea_destino: string;
  tipo: TipoDependencia;
  dias_desfase: number;
}
