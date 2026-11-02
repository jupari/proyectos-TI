export type EstadoProyecto =
  | 'BORRADOR'
  | 'PLANEACION'
  | 'EJECUCION'
  | 'SUSPENDIDO'
  | 'CERRADO'
  | 'CANCELADO';

export const ETIQUETAS_ESTADO_PROYECTO: Record<EstadoProyecto, string> = {
  BORRADOR: 'Borrador',
  PLANEACION: 'Planeación',
  EJECUCION: 'Ejecución',
  SUSPENDIDO: 'Suspendido',
  CERRADO: 'Cerrado',
  CANCELADO: 'Cancelado',
};

export type Prioridad = 'BAJA' | 'MEDIA' | 'ALTA' | 'CRITICA';

export const ETIQUETAS_PRIORIDAD: Record<Prioridad, string> = {
  BAJA: 'Baja',
  MEDIA: 'Media',
  ALTA: 'Alta',
  CRITICA: 'Crítica',
};

export type EstadoTarea =
  | 'PENDIENTE'
  | 'EN_PROGRESO'
  | 'BLOQUEADA'
  | 'EN_REVISION'
  | 'COMPLETADA'
  | 'CANCELADA';

export const ETIQUETAS_ESTADO_TAREA: Record<EstadoTarea, string> = {
  PENDIENTE: 'Pendiente',
  EN_PROGRESO: 'En progreso',
  BLOQUEADA: 'Bloqueada',
  EN_REVISION: 'En revisión',
  COMPLETADA: 'Completada',
  CANCELADA: 'Cancelada',
};

export type TipoTarea = 'ACTIVIDAD' | 'TAREA' | 'INCIDENCIA' | 'CAMBIO' | 'REUNION';

export const ETIQUETAS_TIPO_TAREA: Record<TipoTarea, string> = {
  ACTIVIDAD: 'Actividad',
  TAREA: 'Tarea',
  INCIDENCIA: 'Incidencia',
  CAMBIO: 'Cambio',
  REUNION: 'Reunión',
};

export type Periodicidad = 'DIARIA' | 'SEMANAL' | 'MENSUAL';

export const ETIQUETAS_PERIODICIDAD: Record<Periodicidad, string> = {
  DIARIA: 'Diaria',
  SEMANAL: 'Semanal',
  MENSUAL: 'Mensual',
};

export type EstadoAprobacion = 'BORRADOR' | 'ENVIADO' | 'APROBADO' | 'RECHAZADO';

export const ETIQUETAS_ESTADO_APROBACION: Record<EstadoAprobacion, string> = {
  BORRADOR: 'Borrador',
  ENVIADO: 'Enviado',
  APROBADO: 'Aprobado',
  RECHAZADO: 'Rechazado',
};

export type Semaforo = 'VERDE' | 'AMARILLO' | 'ROJO';

export const ETIQUETAS_SEMAFORO: Record<Semaforo, string> = {
  VERDE: 'Verde',
  AMARILLO: 'Amarillo',
  ROJO: 'Rojo',
};

export type CategoriaRubro =
  | 'PERSONAL'
  | 'LICENCIAS'
  | 'INFRAESTRUCTURA'
  | 'SERVICIOS'
  | 'CAPACITACION'
  | 'OTROS';

export const ETIQUETAS_CATEGORIA_RUBRO: Record<CategoriaRubro, string> = {
  PERSONAL: 'Personal',
  LICENCIAS: 'Licencias',
  INFRAESTRUCTURA: 'Infraestructura',
  SERVICIOS: 'Servicios',
  CAPACITACION: 'Capacitación',
  OTROS: 'Otros',
};

export type TipoRecurso = 'INTERNO' | 'CONTRATISTA' | 'PROVEEDOR';

export const ETIQUETAS_TIPO_RECURSO: Record<TipoRecurso, string> = {
  INTERNO: 'Interno',
  CONTRATISTA: 'Contratista',
  PROVEEDOR: 'Proveedor',
};

export type CategoriaDocumento =
  | 'ACTA'
  | 'INFORME'
  | 'CONTRATO'
  | 'DISENO'
  | 'EVIDENCIA'
  | 'SOPORTE'
  | 'OTRO';

export const ETIQUETAS_CATEGORIA_DOCUMENTO: Record<CategoriaDocumento, string> = {
  ACTA: 'Acta',
  INFORME: 'Informe',
  CONTRATO: 'Contrato',
  DISENO: 'Diseño',
  EVIDENCIA: 'Evidencia',
  SOPORTE: 'Soporte',
  OTRO: 'Otro',
};

export type TipoEvento =
  | 'CREACION'
  | 'ACTUALIZACION'
  | 'CAMBIO_ESTADO'
  | 'APROBACION'
  | 'RECHAZO'
  | 'PUBLICACION'
  | 'CARGA_DOCUMENTO'
  | 'NUEVA_VERSION'
  | 'LOGIN'
  | 'ASIGNACION';

export const ETIQUETAS_TIPO_EVENTO: Record<TipoEvento, string> = {
  CREACION: 'Creación',
  ACTUALIZACION: 'Actualización',
  CAMBIO_ESTADO: 'Cambio de estado',
  APROBACION: 'Aprobación',
  RECHAZO: 'Rechazo',
  PUBLICACION: 'Publicación',
  CARGA_DOCUMENTO: 'Carga de documento',
  NUEVA_VERSION: 'Nueva versión',
  LOGIN: 'Inicio de sesión',
  ASIGNACION: 'Asignación',
};

export type EstadoCompromiso = 'ABIERTO' | 'CUMPLIDO' | 'VENCIDO' | 'CANCELADO';

export const ETIQUETAS_ESTADO_COMPROMISO: Record<EstadoCompromiso, string> = {
  ABIERTO: 'Abierto',
  CUMPLIDO: 'Cumplido',
  VENCIDO: 'Vencido',
  CANCELADO: 'Cancelado',
};

export type EstadoHito = 'PENDIENTE' | 'CUMPLIDO' | 'INCUMPLIDO' | 'REPROGRAMADO';

export const ETIQUETAS_ESTADO_HITO: Record<EstadoHito, string> = {
  PENDIENTE: 'Pendiente',
  CUMPLIDO: 'Cumplido',
  INCUMPLIDO: 'Incumplido',
  REPROGRAMADO: 'Reprogramado',
};

export type EstadoFase = 'PENDIENTE' | 'EN_PROGRESO' | 'COMPLETADA';

export const ETIQUETAS_ESTADO_FASE: Record<EstadoFase, string> = {
  PENDIENTE: 'Pendiente',
  EN_PROGRESO: 'En progreso',
  COMPLETADA: 'Completada',
};

export type TipoDependencia = 'FI' | 'II' | 'FF' | 'IF';

export const ETIQUETAS_TIPO_DEPENDENCIA: Record<TipoDependencia, string> = {
  FI: 'Fin–inicio',
  II: 'Inicio–inicio',
  FF: 'Fin–fin',
  IF: 'Inicio–fin',
};

export type ProveedorAuth = 'LOCAL' | 'GOOGLE';

export const ETIQUETAS_PROVEEDOR_AUTH: Record<ProveedorAuth, string> = {
  LOCAL: 'Local',
  GOOGLE: 'Google',
};

export type EstadoSeguimiento = 'BORRADOR' | 'PUBLICADO';

export const ETIQUETAS_ESTADO_SEGUIMIENTO: Record<EstadoSeguimiento, string> = {
  BORRADOR: 'Borrador',
  PUBLICADO: 'Publicado',
};
