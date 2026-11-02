import { ModeloBase } from './comun.model';
import { TipoRecurso } from './enums';

export interface Recurso extends ModeloBase {
  tipo: TipoRecurso;
  nombre: string;
  usuario: string | null;
  perfil: string | null;
  email: string | null;
  capacidad_horas_mes: string;
  fecha_ingreso: string | null;
  fecha_retiro: string | null;
}

export interface TarifaRecurso extends ModeloBase {
  recurso: string;
  valor_hora: string;
  moneda: string;
  vigente_desde: string;
  vigente_hasta: string | null;
}

export interface AsignacionRecurso extends ModeloBase {
  proyecto: string;
  recurso: string;
  fase: string | null;
  rol_en_proyecto: string;
  fecha_desde: string;
  fecha_hasta: string;
  porcentaje_dedicacion: string;
  horas_planeadas: string;
  valor_hora_plan: string;
  /** Calculado (C): horas_planeadas * valor_hora_plan. */
  costo_planeado: string;
}
