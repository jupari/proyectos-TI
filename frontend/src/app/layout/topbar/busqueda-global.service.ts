import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { catchError, firstValueFrom, of } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth/auth.service';
import { RespuestaPaginada } from '../../core/models';

export interface ResultadoBusqueda {
  tipo: 'Proyecto' | 'Tarea' | 'Recurso';
  titulo: string;
  detalle: string;
  ruta: string;
}

interface ItemApi {
  id: string;
  codigo?: string;
  nombre: string;
  email?: string;
}

const LIMITE_POR_TIPO = 5;

@Injectable({ providedIn: 'root' })
export class BusquedaGlobalService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  async buscar(texto: string): Promise<ResultadoBusqueda[]> {
    const [proyectos, tareas, recursos] = await Promise.all([
      this.consultar('proyectos', texto),
      this.consultar('tareas', texto),
      this.auth.tienePermiso('recursos.ver') ? this.consultar('recursos', texto) : Promise.resolve([]),
    ]);
    return [
      ...proyectos.map((p) => this.mapear('Proyecto', '/proyectos', p)),
      ...tareas.map((t) => this.mapear('Tarea', '/tareas', t)),
      ...recursos.map((r) => this.mapear('Recurso', '/recursos', r)),
    ];
  }

  private consultar(recurso: string, texto: string): Promise<ItemApi[]> {
    const params = new HttpParams().set('search', texto).set('page_size', LIMITE_POR_TIPO);
    const peticion = this.http
      .get<RespuestaPaginada<ItemApi>>(`${environment.apiBaseUrl}/${recurso}/`, { params })
      .pipe(catchError(() => of({ results: [] as ItemApi[] } as RespuestaPaginada<ItemApi>)));
    return firstValueFrom(peticion).then((r) => r.results.slice(0, LIMITE_POR_TIPO));
  }

  private mapear(tipo: ResultadoBusqueda['tipo'], base: string, item: ItemApi): ResultadoBusqueda {
    return {
      tipo,
      titulo: item.nombre,
      detalle: item.codigo ?? item.email ?? '',
      ruta: `${base}/${item.id}`,
    };
  }
}
