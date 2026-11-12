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
}
