import { Injectable, signal } from '@angular/core';

export type TipoToast = 'exito' | 'alerta' | 'error' | 'info';

export interface ToastMensaje {
  id: number;
  tipo: TipoToast;
  mensaje: string;
  duracionMs: number;
}

let siguienteId = 0;

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly mensajes = signal<ToastMensaje[]>([]);

  mostrar(opciones: { tipo: TipoToast; mensaje: string; duracionMs?: number }): void {
    const id = siguienteId++;
    const duracionMs = opciones.duracionMs ?? 5000;
    this.mensajes.update((actuales) => [
      ...actuales,
      { id, tipo: opciones.tipo, mensaje: opciones.mensaje, duracionMs },
    ]);
    setTimeout(() => this.cerrar(id), duracionMs);
  }

  cerrar(id: number): void {
    this.mensajes.update((actuales) => actuales.filter((m) => m.id !== id));
  }
}
