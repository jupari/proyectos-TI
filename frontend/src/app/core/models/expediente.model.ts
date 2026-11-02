import { ModeloBase } from './comun.model';
import { CategoriaDocumento, TipoEvento } from './enums';

export interface DocumentoExpediente extends ModeloBase {
  proyecto: string;
  proyecto_codigo: string;
  seguimiento: string | null;
  tarea: string | null;
  categoria: CategoriaDocumento;
  nombre: string;
  archivo: string;
  nombre_original: string;
  mime: string;
  tamano_bytes: number;
  hash_sha256: string;
  version: number;
  documento_padre: string | null;
  es_version_vigente: boolean;
  descripcion: string;
  creado_por: string | null;
  creado_por_nombre: string | null;
  creado_en: string;
}

export interface EntradaBitacora extends ModeloBase {
  proyecto: string | null;
  tipo_evento: TipoEvento;
  entidad: string;
  entidad_id: string;
  descripcion: string;
  datos_antes: Record<string, unknown> | null;
  datos_despues: Record<string, unknown> | null;
  usuario: string | null;
  usuario_nombre: string | null;
  ocurrido_en: string;
}
