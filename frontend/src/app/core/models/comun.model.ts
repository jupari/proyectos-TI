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

/** docs/api-contrato.md §9 */
export interface ErrorApi {
  error: {
    codigo: string;
    mensaje: string;
    detalles: Record<string, string[]> | null;
    traza_id: string;
  };
}
