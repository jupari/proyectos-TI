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

export type TamanoModal = 'sm' | 'md' | 'lg';

const CLASES_TAMANO: Record<TamanoModal, string> = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-3xl',
};

/** Tamaños, cierre con Esc, trampa de foco y bloqueo de scroll mientras
 * está abierto. `app-drawer` sigue el mismo contrato. */
@Component({
  selector: 'app-modal',
  templateUrl: './modal.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Modal {
  readonly abierto = input(false);
  readonly titulo = input('');
  readonly tamano = input<TamanoModal>('md');

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
