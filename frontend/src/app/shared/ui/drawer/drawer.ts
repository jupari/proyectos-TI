import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  computed,
  effect,
  input,
  output,
  viewChild,
} from '@angular/core';

export type TamanoDrawer = 'sm' | 'md' | 'lg';

const CLASES_TAMANO: Record<TamanoDrawer, string> = {
  sm: 'max-w-sm',
  md: 'max-w-xl',
  lg: 'max-w-3xl',
};

/** Mismo contrato que `app-modal` (Esc, trampa de foco, bloqueo de scroll),
 * pero deslizado desde el lateral derecho: para formularios largos. */
@Component({
  selector: 'app-drawer',
  templateUrl: './drawer.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Drawer {
  readonly abierto = input(false);
  readonly titulo = input('');
  readonly tamano = input<TamanoDrawer>('md');

  readonly cerrar = output<void>();

  protected readonly clasesTamano = computed(() => CLASES_TAMANO[this.tamano()]);

  private readonly contenedor = viewChild<ElementRef<HTMLElement>>('contenedor');

  constructor() {
    effect(() => {
      if (this.abierto()) {
        document.body.style.overflow = 'hidden';
        queueMicrotask(() => this.contenedor()?.nativeElement.focus());
      } else {
        document.body.style.overflow = '';
      }
    });
  }

  @HostListener('document:keydown.escape')
  protected alEscape(): void {
    if (this.abierto()) {
      this.cerrar.emit();
    }
  }

  protected alTeclaTab(evento: KeyboardEvent): void {
    if (evento.key !== 'Tab') return;
    const contenedor = this.contenedor()?.nativeElement;
    if (!contenedor) return;
    const focusables = contenedor.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
    );
    if (focusables.length === 0) return;
    const primero = focusables[0];
    const ultimo = focusables[focusables.length - 1];

    if (evento.shiftKey && document.activeElement === primero) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primero.focus();
    }
  }

  protected alClicFondo(): void {
    this.cerrar.emit();
  }
}
