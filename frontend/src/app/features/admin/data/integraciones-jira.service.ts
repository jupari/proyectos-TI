import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';

export interface ProyectoJira {
  clave: string;
  nombre: string;
}

export interface ConfiguracionImportacionJira {
  auto_aprobar_importados: boolean;
}

export interface ImportarHorasJiraCuerpo {
  desde: string;
  hasta: string;
  dry_run?: boolean;
  auto_aprobar?: boolean;
}

export interface OmisionImportacion {
  id_externo?: string;
  motivo: string;
  detalle?: string;
}

export interface FilaDetalleImportacion {
  fecha: string;
  recurso_nombre: string;
  proyecto_codigo: string;
  proyecto_nombre: string;
  horas: string;
  accion: 'creado' | 'actualizado';
}

export interface ResumenImportacionJira {
  creados: number;
  actualizados: number;
  detalle: FilaDetalleImportacion[];
  omitidos: OmisionImportacion[];
  errores: OmisionImportacion[];
}

export interface PersonaJiraSinMapear {
  jira_account_id: string;
  nombre: string;
  worklogs: number;
}

export interface EstadoJiraResumen {
  nombre: string;
  categoria: string;
  estado_app: string;
  cantidad: number;
}

export interface SprintJiraResumen {
  id: number;
  nombre: string;
  estado: string;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  incidencias: number;
}

export interface FilaMuestraTareaJira {
  clave: string;
  resumen: string;
  tipo: string;
  tipo_jira: string;
  estado_jira: string;
  estado_app: string;
  responsable: string;
  horas_estimadas: number | null;
  sprint: string | null;
  epica: string;
  padre: string | null;
}

/** Fase 14: lo que traería la importación de tareas, historias y sprints (solo lectura). */
export interface ResumenTareasJira {
  clave_proyecto: string;
  total_incidencias: number;
  truncado: boolean;
  por_tipo: Record<string, number>;
  estados: EstadoJiraResumen[];
  sprints: SprintJiraResumen[];
  epicas: { clave: string; nombre: string }[];
  sin_estimacion: number;
  sin_responsable: number;
  sin_sprint: number;
  responsables_sin_recurso: { jira_account_id: string; nombre: string; incidencias: number }[];
  advertencias: string[];
  detalle: FilaMuestraTareaJira[];
}

export interface ResumenImportacionTareasJira {
  clave_proyecto: string;
  proyecto: string;
  creadas: number;
  actualizadas: number;
  sprints_creados: number;
  sprints_actualizados: number;
  sin_responsable_asociado: string[];
  advertencias: string[];
  errores: { clave: string; motivo: string; detalle?: string }[];
  detalle: { clave: string; codigo: string; nombre: string; tipo: string; estado: string; accion: string }[];
}

/** Fase 12: no son recursos CRUD paginados (uno es una lista en vivo desde
 * Jira, el otro una fila única de configuración), así que no extiende
 * `ApiService<T>` — mismo criterio que `DocumentosService`. */
@Injectable({ providedIn: 'root' })
export class IntegracionesJiraService {
  private readonly http = inject(HttpClient);

  listarProyectosJira(): Observable<ProyectoJira[]> {
    return this.http.get<ProyectoJira[]>(`${environment.apiBaseUrl}/integraciones/jira/proyectos/`);
  }

  obtenerConfiguracion(): Observable<ConfiguracionImportacionJira> {
    return this.http.get<ConfiguracionImportacionJira>(
      `${environment.apiBaseUrl}/configuracion-importacion-jira/`,
    );
  }

  actualizarConfiguracion(
    cuerpo: Partial<ConfiguracionImportacionJira>,
  ): Observable<ConfiguracionImportacionJira> {
    return this.http.patch<ConfiguracionImportacionJira>(
      `${environment.apiBaseUrl}/configuracion-importacion-jira/`,
      cuerpo,
    );
  }

  importarHoras(cuerpo: ImportarHorasJiraCuerpo): Observable<ResumenImportacionJira> {
    return this.http.post<ResumenImportacionJira>(
      `${environment.apiBaseUrl}/integraciones/jira/importar/`,
      cuerpo,
    );
  }

  simularImportacionTareas(clave_proyecto: string, desde?: string): Observable<ResumenTareasJira> {
    return this.http.post<ResumenTareasJira>(
      `${environment.apiBaseUrl}/integraciones/jira/tareas/simular/`,
      { clave_proyecto, ...(desde ? { desde } : {}) },
    );
  }

  importarTareas(clave_proyecto: string, desde?: string): Observable<ResumenImportacionTareasJira> {
    return this.http.post<ResumenImportacionTareasJira>(
      `${environment.apiBaseUrl}/integraciones/jira/tareas/importar/`,
      { clave_proyecto, ...(desde ? { desde } : {}) },
    );
  }

  listarPersonasSinMapear(desde: string, hasta: string): Observable<PersonaJiraSinMapear[]> {
    return this.http.get<PersonaJiraSinMapear[]>(
      `${environment.apiBaseUrl}/integraciones/jira/personas-sin-mapear/`,
      { params: { desde, hasta } },
    );
  }
}
