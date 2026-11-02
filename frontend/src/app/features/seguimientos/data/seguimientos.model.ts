import { Hito } from '../../../core/models';
import { TareaLista } from '../../tareas/data/tareas.model';

export interface SeguimientoEscritura {
  proyecto: string;
  periodicidad: string;
  periodo_inicio: string;
  fecha_corte?: string;
  avance_reportado: number | string;
  semaforo: string;
  justificacion_semaforo?: string;
  logros?: string;
  dificultades?: string;
  riesgos?: string;
  acciones_siguientes?: string;
}

export interface FiltrosSeguimiento {
  proyecto?: string;
  periodicidad?: string;
  estado?: string;
  fecha_corte__gte?: string;
  fecha_corte__lte?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

/** Respuesta de `POST /seguimientos/precargar/`: borrador sin guardar más
 * las listas informativas de apoyo (docs/plan/fase-09 §9.1.1). */
export interface PrecargaSeguimiento {
  proyecto: string;
  periodicidad: string;
  periodo_inicio: string;
  periodo_fin: string;
  fecha_corte: string;
  horas_periodo: string;
  costo_periodo: string;
  horas_acumuladas: string;
  costo_acumulado: string;
  semaforo_calculado: string;
  avance_reportado: string;
  tareas_completadas_en_periodo: TareaLista[];
  tareas_vencidas: TareaLista[];
  hitos_del_periodo: Hito[];
  tareas_creadas_en_periodo: TareaLista[];
}
