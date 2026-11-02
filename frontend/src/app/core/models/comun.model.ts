import { Semaforo } from './enums';

/** Campos comunes a todo modelo que herede de `ModeloBase` en el backend. */
export interface ModeloBase {
  id: string;
  creado_en: string;
  actualizado_en: string;
  creado_por: string | null;
  actualizado_por: string | null;
  activo: boolean;
}

/** docs/api-contrato.md §1 */
export interface RespuestaPaginada<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Bloque reutilizado en varias respuestas (docs/api-contrato.md §7).
 * Todo índice o porcentaje puede venir en `null`: el denominador era 0 y no
 * hay nada que mostrar, nunca un 0% engañoso (docs/modelo-datos.md §10). */
export interface ResumenEjecucion {
  fecha_corte: string;
  horas_planeadas: number;
  horas_ejecutadas: number;
  pct_horas: number | null;
  costo_planeado: number;
  costo_ejecutado: number;
  pct_dinero: number | null;
  pct_tiempo: number | null;
  avance: string;
  spi: number | null;
  cpi: number | null;
  desviacion_presupuestal: number;
  semaforo: Semaforo;
  horas_pendientes_aprobacion: number;
  hitos_cumplidos: number;
  hitos_incumplidos: number;
  tareas_abiertas: number;
  tareas_vencidas: number;
}

/** Versión reducida que trae el listado de proyectos (docs/plan/fase-05 §5.3.7). */
export interface ResumenEjecucionReducido {
  pct_horas: number | null;
  pct_dinero: number | null;
  avance: string;
}

/** docs/api-contrato.md §9 */
export interface ErrorApi {
  error: {
    codigo: string;
    mensaje: string;
    detalles: Record<string, string[]> | null;
    traza_id: string;
  };
}
