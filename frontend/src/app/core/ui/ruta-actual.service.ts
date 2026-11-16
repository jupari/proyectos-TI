import { Injectable, inject, signal } from '@angular/core';
import { Event, EventType, NavigationEnd, Router } from '@angular/router';

/** URL vigente como señal, para el menú lateral y las migas de pan. */
@Injectable({ providedIn: 'root' })
export class RutaActualService {
  private readonly router = inject(Router);

  readonly url = signal(this.router.url);

  constructor() {
    this.router.events.subscribe((evento: Event) => {
      if (evento.type === EventType.NavigationEnd) {
        this.url.set((evento as NavigationEnd).urlAfterRedirects);
      }
    });
  }
}
