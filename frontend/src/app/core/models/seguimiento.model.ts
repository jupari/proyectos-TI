import { ModeloBase } from './comun.model';
import { EstadoCompromiso, EstadoSeguimiento, Periodicidad, Semaforo } from './enums';

export interface Seguimiento extends ModeloBase {
  proyecto: string;
  proyecto_codigo: string;
  periodicidad: Periodicidad;
  periodo_inicio: string;
  periodo_fin: string;
  fecha_corte: string;
  avance_reportado: string;
  semaforo: Semaforo;
  /** Calculado (C). Si difiere del declarado exige justificacion_semaforo. */
  semaforo_calculado: Semaforo;
  justificacion_semaforo: string;
  logros: string;
  dificultades: string;
  riesgos: string;
  acciones_siguientes: string;
  /** Calculado (C): horas aprobadas del periodo. */
  horas_periodo: string;
  /** Calculado (C): costo aprobado del periodo. */
  costo_periodo: string;
  /** Calculado (C): desde el inicio del proyecto hasta fecha_corte. */
  horas_acumuladas: string;
  /** Calculado (C). */
  costo_acumulado: string;
  estado: EstadoSeguimiento;
  publicado_en: string | null;
  publicado_por: string | null;
  publicado_por_nombre: string | null;
}

export interface CompromisoSeguimiento extends ModeloBase {
  seguimiento: string;
  descripcion: string;
  responsable: string;
  responsable_nombre: string;
  fecha_compromiso: string;
  estado: EstadoCompromiso;
  fecha_cumplimiento: string | null;
  esta_vencido: boolean;
}
