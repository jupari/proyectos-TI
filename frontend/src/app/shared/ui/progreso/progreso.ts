import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

@Component({
  selector: 'app-progreso',
  templateUrl: './progreso.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Progreso {
  readonly valor = input.required<number>();
  readonly etiqueta = input('');

  protected readonly porcentaje = computed(() => Math.min(100, Math.max(0, this.valor())));

  protected readonly clase = computed(() => {
    const valor = this.porcentaje();
    if (valor >= 85) return 'bg-exito';
    if (valor >= 50) return 'bg-alerta';
    return 'bg-peligro';
  });
}
