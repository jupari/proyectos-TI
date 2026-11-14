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
  is_active: boolean;
  roles: string[];
  permisos_ui: string[];
}

/** Cuerpo de `UsuarioAdminEscrituraSerializer`: `clave_temporal` solo viaja
 * en la respuesta de creación (no hay envío de correo en esta versión). */
export interface UsuarioEscritura {
  email: string;
  nombres: string;
  apellidos: string;
  cargo: string;
  telefono: string;
  is_active: boolean;
  roles: string[];
}

export interface UsuarioCreado extends UsuarioEscritura {
  clave_temporal: string;
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

/** Respuesta del paso 1 del login local (fase 13): credenciales válidas,
 * falta confirmar el código que se envió por correo. */
export interface RespuestaSolicitarCodigo {
  requiere_codigo: true;
  login_token: string;
}

export interface RolMeta {
  id: string;
  codigo: string;
  descripcion: string;
  es_sistema: boolean;
  orden: number;
  activo: boolean;
}
