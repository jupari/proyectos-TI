import { Injectable, signal } from '@angular/core';

export interface OpcionesConfirmacion {
  titulo: string;
  mensaje: string;
  textoConfirmar?: string;
  textoCancelar?: string;
  variante?: 'normal' | 'peligro';
}

export interface SolicitudConfirmacion extends OpcionesConfirmacion {
  resolver: (confirmado: boolean) => void;
}

@Injectable({ providedIn: 'root' })
export class ConfirmacionService {
  readonly solicitud = signal<SolicitudConfirmacion | null>(null);

  confirmar(opciones: OpcionesConfirmacion): Promise<boolean> {
    return new Promise<boolean>((resolver) => {
      this.solicitud.set({ ...opciones, resolver });
    });
  }

  responder(confirmado: boolean): void {
    this.solicitud()?.resolver(confirmado);
    this.solicitud.set(null);
  }
}
