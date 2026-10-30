import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { environment } from '../environments/environment';

interface RespuestaSalud {
  estado: string;
  version: string;
  base_datos: string;
  hora: string;
}

@Component({
  imports: [RouterOutlet],
  selector: 'app-root',
  styleUrl: './app.css',
  templateUrl: './app.html',
})
export class App {
  private readonly http = inject(HttpClient);

  protected readonly salud = signal<RespuestaSalud | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    this.http.get<RespuestaSalud>(`${environment.apiBaseUrl}/salud/`).subscribe({
      next: (respuesta) => this.salud.set(respuesta),
      error: () => this.error.set('No se pudo conectar con la API.'),
    });
  }
}
