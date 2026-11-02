import { ModeloBase } from './comun.model';
import { EstadoAprobacion, Periodicidad } from './enums';

export interface RegistroEjecucion extends ModeloBase {
  proyecto: string;
  proyecto_codigo: string;
  tarea: string | null;
  tarea_codigo: string | null;
  recurso: string;
  recurso_nombre: string;
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
  aprobado_por_nombre: string | null;
  aprobado_en: string | null;
  registrado_por: string | null;
  registrado_por_nombre: string | null;
}

export interface GastoEjecutado extends ModeloBase {
  proyecto: string;
  proyecto_codigo: string;
  rubro: string;
  rubro_descripcion: string;
  fecha: string;
  monto: string;
  proveedor: string;
  numero_documento: string;
  descripcion: string;
  estado_aprobacion: EstadoAprobacion;
  aprobado_por: string | null;
  aprobado_por_nombre: string | null;
  aprobado_en: string | null;
}
