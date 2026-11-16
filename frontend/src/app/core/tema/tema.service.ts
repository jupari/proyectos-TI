import { Injectable, computed, signal } from '@angular/core';

export type ModoColor = 'claro' | 'oscuro' | 'sistema';

export interface TemaColor {
  id: string;
  nombre: string;
  /** Color de vista previa (nivel 600 de la escala). */
  muestra: string;
}

export const TEMAS: readonly TemaColor[] = [
  { id: 'turquesa', nombre: 'Turquesa', muestra: '#0d9488' },
  { id: 'azul', nombre: 'Azul', muestra: '#2563eb' },
  { id: 'violeta', nombre: 'Violeta', muestra: '#7c3aed' },
  { id: 'rosa', nombre: 'Rosa', muestra: '#e11d48' },
  { id: 'naranja', nombre: 'Naranja', muestra: '#ea580c' },
  { id: 'grafito', nombre: 'Grafito', muestra: '#475569' },
];

export const CLAVE_TEMA = 'sp_tema';
export const CLAVE_MODO = 'sp_modo';

function leer(clave: string): string | null {
  try {
    return localStorage.getItem(clave);
  } catch {
    return null;
  }
}

function guardar(clave: string, valor: string): void {
  try {
    localStorage.setItem(clave, valor);
  } catch {
    // almacenamiento no disponible: la preferencia solo dura la sesión
  }
}

/**
 * Tema de color + modo claro/oscuro. Aplica `data-tema` y `data-modo` en
 * `<html>` (ver src/styles.css) y recuerda la elección en `localStorage`.
 * `version` cambia con cada aplicación para que los gráficos (canvas, que no
 * heredan CSS) se redibujen con los colores nuevos.
 */
@Injectable({ providedIn: 'root' })
export class TemaService {
  private readonly consultaOscuro = window.matchMedia?.('(prefers-color-scheme: dark)');

  readonly temas = TEMAS;
  readonly tema = signal(this.temaInicial());
  readonly modo = signal<ModoColor>(this.modoInicial());
  readonly sistemaOscuro = signal(this.consultaOscuro?.matches ?? false);
  readonly modoEfectivo = computed<'claro' | 'oscuro'>(() => {
    const modo = this.modo();
    if (modo === 'sistema') return this.sistemaOscuro() ? 'oscuro' : 'claro';
    return modo;
  });
  readonly version = signal(0);

  constructor() {
    this.consultaOscuro?.addEventListener('change', (evento) => {
      this.sistemaOscuro.set(evento.matches);
      this.aplicar();
    });
    this.aplicar();
  }

  elegirTema(id: string): void {
    if (!TEMAS.some((tema) => tema.id === id)) return;
    this.tema.set(id);
    guardar(CLAVE_TEMA, id);
    this.aplicar();
  }

  elegirModo(modo: ModoColor): void {
    this.modo.set(modo);
    guardar(CLAVE_MODO, modo);
    this.aplicar();
  }

  /** Color del tema actual, resuelto desde las variables CSS (para canvas). */
  color(variable: string): string {
    const canal = getComputedStyle(document.documentElement).getPropertyValue(`--${variable}`).trim();
    return canal ? `rgb(${canal})` : '#64748b';
  }

  private aplicar(): void {
    const raiz = document.documentElement;
    raiz.setAttribute('data-tema', this.tema());
    raiz.setAttribute('data-modo', this.modoEfectivo());
    this.version.update((v) => v + 1);
  }

  private temaInicial(): string {
    const guardado = leer(CLAVE_TEMA);
    return TEMAS.some((tema) => tema.id === guardado) ? (guardado as string) : TEMAS[0].id;
  }

  private modoInicial(): ModoColor {
    const guardado = leer(CLAVE_MODO);
    return guardado === 'claro' || guardado === 'oscuro' || guardado === 'sistema' ? guardado : 'sistema';
  }
}
