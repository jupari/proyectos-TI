import { ModeloBase } from './comun.model';
import { CategoriaRubro, EstadoFase, EstadoHito, EstadoProyecto, Prioridad, Semaforo } from './enums';

export interface Proyecto extends ModeloBase {
  codigo: string;
  nombre: string;
  descripcion: string;
  objetivo: string;
  portafolio: string | null;
  area_solicitante: string;
  gerente: string;
  lider_tecnico: string | null;
  estado: EstadoProyecto;
  prioridad: Prioridad;
  fecha_inicio_plan: string;
  fecha_fin_plan: string;
  fecha_inicio_real: string | null;
  fecha_fin_real: string | null;
  moneda: string;
  presupuesto_horas: string;
  presupuesto_dinero: string;
  avance_reportado: string;
  /** Calculado (C): nunca se escribe desde la API. */
  semaforo: Semaforo;
  observaciones: string;
}

export interface FaseProyecto extends ModeloBase {
  proyecto: string;
  nombre: string;
  orden: number;
  peso: string;
  fecha_inicio_plan: string;
  fecha_fin_plan: string;
  fecha_inicio_real: string | null;
  fecha_fin_real: string | null;
  estado: EstadoFase;
}

export interface Hito extends ModeloBase {
  proyecto: string;
  nombre: string;
  descripcion: string;
  fecha_plan: string;
  fecha_real: string | null;
  estado: EstadoHito;
  criterio_cumplimiento: string;
  es_entregable: boolean;
}

export interface RubroPresupuesto extends ModeloBase {
  proyecto: string;
  categoria: CategoriaRubro;
  descripcion: string;
  monto_planeado: string;
  /** Calculado (C): suma de GastoEjecutado aprobados. */
  monto_ejecutado: string;
}
