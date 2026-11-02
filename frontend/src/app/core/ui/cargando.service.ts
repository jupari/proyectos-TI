import { Injectable, computed, signal } from '@angular/core';

/** Cuenta peticiones HTTP activas para alimentar la barra de progreso superior. */
@Injectable({ providedIn: 'root' })
export class CargandoService {
  private readonly contador = signal(0);
  readonly activo = computed(() => this.contador() > 0);

  iniciar(): void {
    this.contador.update((valor) => valor + 1);
  }

  finalizar(): void {
    this.contador.update((valor) => Math.max(0, valor - 1));
  }
}
