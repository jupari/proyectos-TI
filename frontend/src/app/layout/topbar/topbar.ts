import { ChangeDetectionStrategy, Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { PantallaService } from '../../core/ui/pantalla.service';
import { SelectorTema } from './selector-tema';
import { BusquedaGlobalService, ResultadoBusqueda } from './busqueda-global.service';

const MIN_CARACTERES = 2;
const ESPERA_MS = 300;

@Component({
  selector: 'app-topbar',
  templateUrl: './topbar.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, SelectorTema],
  host: {
    '(document:click)': 'alClicFuera($event)',
  },
})
export class Topbar {
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly busquedaGlobal = inject(BusquedaGlobalService);

  protected readonly texto = signal('');
  protected readonly resultados = signal<ResultadoBusqueda[]>([]);
  protected readonly buscando = signal(false);
  protected readonly panelBusquedaAbierto = signal(false);
  protected readonly indiceActivo = signal(-1);
  private temporizador?: ReturnType<typeof setTimeout>;
  private consultaVigente = 0;

  protected readonly pantalla = inject(PantallaService);
  protected readonly menuAbierto = signal(false);
  protected readonly busquedaMovilAbierta = signal(false);
  private readonly campoBusqueda = viewChild<ElementRef<HTMLInputElement>>('campoBusqueda');

  protected alternarMenu(): void {
    this.menuAbierto.update((valor) => !valor);
  }

  protected alClicFuera(evento: MouseEvent): void {
    const objetivo = evento.target as HTMLElement;
    if (!objetivo.closest('[data-menu-usuario]')) {
      this.menuAbierto.set(false);
    }
    if (!objetivo.closest('[data-busqueda]') && !objetivo.closest('[data-lupa]')) {
      this.panelBusquedaAbierto.set(false);
      this.busquedaMovilAbierta.set(false);
    }
  }

  protected abrirBusquedaMovil(): void {
    this.busquedaMovilAbierta.set(true);
    setTimeout(() => this.campoBusqueda()?.nativeElement.focus());
  }

  protected alEscribir(valor: string): void {
    this.texto.set(valor);
    this.indiceActivo.set(-1);
    clearTimeout(this.temporizador);
    const consulta = valor.trim();
    if (consulta.length < MIN_CARACTERES) {
      this.consultaVigente++;
      this.resultados.set([]);
      this.buscando.set(false);
      this.panelBusquedaAbierto.set(false);
      return;
    }
    this.panelBusquedaAbierto.set(true);
    this.buscando.set(true);
    this.temporizador = setTimeout(() => void this.ejecutarBusqueda(consulta), ESPERA_MS);
  }

  private async ejecutarBusqueda(consulta: string): Promise<void> {
    const numero = ++this.consultaVigente;
    const resultados = await this.busquedaGlobal.buscar(consulta);
    if (numero !== this.consultaVigente) return;
    this.resultados.set(resultados);
    this.buscando.set(false);
  }

  protected alTeclaBusqueda(evento: KeyboardEvent): void {
    const total = this.resultados().length;
    if (evento.key === 'Escape') {
      this.panelBusquedaAbierto.set(false);
      this.busquedaMovilAbierta.set(false);
    } else if (evento.key === 'ArrowDown' && total > 0) {
      evento.preventDefault();
      this.indiceActivo.update((i) => (i + 1) % total);
    } else if (evento.key === 'ArrowUp' && total > 0) {
      evento.preventDefault();
      this.indiceActivo.update((i) => (i <= 0 ? total - 1 : i - 1));
    } else if (evento.key === 'Enter') {
      const elegido = this.resultados()[this.indiceActivo()] ?? this.resultados()[0];
      if (elegido) {
        evento.preventDefault();
        void this.irA(elegido);
      }
    }
  }

  protected async irA(resultado: ResultadoBusqueda): Promise<void> {
    this.panelBusquedaAbierto.set(false);
    this.busquedaMovilAbierta.set(false);
    this.texto.set('');
    this.resultados.set([]);
    await this.router.navigateByUrl(resultado.ruta);
  }

  protected async salir(): Promise<void> {
    await this.auth.logout();
    await this.router.navigate(['/auth/login']);
  }
}
