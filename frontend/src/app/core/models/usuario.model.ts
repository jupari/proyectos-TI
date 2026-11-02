import { ProveedorAuth } from './enums';

/** Forma de `usuario` en /auth/login/ y /auth/google/callback/ (api-contrato.md §2). */
export interface Usuario {
  id: string;
  email: string;
  nombres: string;
  apellidos: string;
  cargo: string;
  telefono: string;
  avatar_url: string | null;
  proveedor_auth: ProveedorAuth;
  debe_cambiar_clave: boolean;
  roles: string[];
  permisos_ui: string[];
}

/** GET /auth/yo/ añade `proyectos_liderados` a la forma de `Usuario`. */
export interface UsuarioActual extends Usuario {
  proyectos_liderados: ProyectoResumido[];
}

export interface ProyectoResumido {
  id: string;
  codigo: string;
  nombre: string;
}

export interface RespuestaLogin {
  access: string;
  refresh: string;
  usuario: Usuario;
}

export interface RolMeta {
  id: string;
  codigo: string;
  descripcion: string;
  es_sistema: boolean;
  orden: number;
  activo: boolean;
}
