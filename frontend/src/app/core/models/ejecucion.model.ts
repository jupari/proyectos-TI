import { ModeloBase } from './comun.model';
import { EstadoAprobacion, Periodicidad } from './enums';

export interface RegistroEjecucion extends ModeloBase {
  proyecto: string;
  tarea: string | null;
  recurso: string;
  periodicidad: Periodicidad;
  periodo_inicio: string;
  periodo_fin: string;
  horas: string;
  /** Calculado (C) al crear, con valor_hora_vigente(recurso, periodo_inicio); queda congelado. */
  valor_hora_aplicado: string;
  /** Calculado (C): horas * valor_hora_aplicado. */
  costo: string;
  descripcion: string;
  estado_aprobacion: EstadoAprobacion;
  motivo_rechazo: string;
  aprobado_por: string | null;
  aprobado_en: string | null;
  registrado_por: string | null;
}

export interface GastoEjecutado extends ModeloBase {
  proyecto: string;
  rubro: string;
  fecha: string;
  monto: string;
  proveedor: string;
  numero_documento: string;
  descripcion: string;
  estado_aprobacion: EstadoAprobacion;
  aprobado_por: string | null;
  aprobado_en: string | null;
}
