import { ModeloBase } from './comun.model';

export interface Area extends ModeloBase {
  codigo: string;
  nombre: string;
  responsable: string | null;
}

export interface Portafolio extends ModeloBase {
  codigo: string;
  nombre: string;
  descripcion: string;
  responsable: string | null;
}

export interface PerfilRecurso extends ModeloBase {
  codigo: string;
  nombre: string;
  tarifa_hora_referencia: string;
  moneda: string;
}
