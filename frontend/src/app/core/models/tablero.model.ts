import { EstadoProyecto } from './enums';
import { ResumenEjecucion } from './comun.model';

/** docs/api-contrato.md §7. Los mismos filtros que `/proyectos/`, más los
 * propios de cada vista del tablero (fase 10 §10.1.2). */
export interface FiltrosTablero {
  estado?: string;
  prioridad?: string;
  portafolio?: string;
  area_solicitante?: string;
  gerente?: string;
  lider_tecnico?: string;
  semaforo?: string;
  mis_proyectos?: boolean;
  proyecto?: string;
  desde?: string;
  hasta?: string;
  perfil?: string;
  refrescar?: boolean;
}

export interface ResumenGlobalTablero {
  total_proyectos: number;
  por_estado: Record<string, number>;
  por_semaforo: Record<string, number>;
  proyectos_en_riesgo: number;
  horas_planeadas: number;
  horas_ejecutadas: number;
  pct_horas: number | null;
  costo_planeado: number;
  costo_ejecutado: number;
  pct_dinero: number | null;
  horas_pendientes_aprobacion: number;
  compromisos_vencidos: number;
  hitos_incumplidos: number;
  calculado_en: string;
}

export interface FilaTableroProyecto {
  id: string;
  codigo: string;
  nombre: string;
  gerente: string | null;
  estado: EstadoProyecto;
  resumen_ejecucion: ResumenEjecucion;
}

export interface TablaProyectosTablero {
  filas: FilaTableroProyecto[];
  calculado_en: string;
}

export interface FilaTableroProyectoPeriodo {
  id: string;
  codigo: string;
  nombre: string;
  horas_plan: number;
  horas_ejec: number;
  pct_horas: number | null;
}

export interface TotalesTableroProyectoPeriodo {
  horas_plan: number;
  horas_ejec: number;
  pct_horas: number | null;
}

export interface TablaProyectosPorPeriodoTablero {
  filas: FilaTableroProyectoPeriodo[];
  totales: TotalesTableroProyectoPeriodo;
  calculado_en: string;
}

export interface PuntoEjecucionMensual {
  mes: string;
  horas_plan: number;
  horas_ejec: number;
  costo_plan: number;
  costo_ejec: number;
  horas_ejec_acum: number;
  costo_ejec_acum: number;
}

export interface EjecucionMensualTablero {
  serie: PuntoEjecucionMensual[];
  calculado_en: string;
}

export interface OcupacionRecurso {
  recurso: string;
  recurso_nombre: string;
  anio: number;
  mes: number;
  horas_planeadas: number;
  horas_ejecutadas: number;
  capacidad: number;
  pct_ocupacion: number | null;
}

export interface RecursosTablero {
  recursos: OcupacionRecurso[];
  calculado_en: string;
}

/** Un mes de `PlanCostosProyecto` (fase 15): `horas_*` solo existen en el
 * bloque "Personal" — en los demás bloques (licencias, infraestructura,
 * servicios, capacitación, otros) el costo es derivado de `RubroPresupuesto`/
 * `GastoEjecutado`, sin concepto de horas. */
export interface ValoresPlanCostosMes {
  horas_plan?: number;
  valor_plan: number;
  horas_ejec?: number;
  valor_ejec: number;
}

export interface FilaPlanCostos {
  id: string;
  nombre: string;
  perfil?: string | null;
  rol?: string;
  valor_hora?: number;
  dedicacion_pct?: number;
  por_mes: Record<string, ValoresPlanCostosMes>;
  total: ValoresPlanCostosMes;
}

export interface BloquePlanCostos {
  categoria: string;
  etiqueta: string;
  filas: FilaPlanCostos[];
  subtotal: {
    por_mes: Record<string, ValoresPlanCostosMes>;
    total: ValoresPlanCostosMes;
  };
}

export interface PlanCostosProyecto {
  meses: string[];
  bloques: BloquePlanCostos[];
  total_general: {
    por_mes: Record<string, ValoresPlanCostosMes>;
    total: ValoresPlanCostosMes;
  };
  calculado_en: string;
}

export interface ResumenTareasTablero {
  por_estado: Record<string, number>;
  total: number;
  vencidas: number;
  creadas_durante_ejecucion: number;
  promedio_dias_atraso: number | null;
  calculado_en: string;
}
