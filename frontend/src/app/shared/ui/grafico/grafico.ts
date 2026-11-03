import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  effect,
  input,
  viewChild,
} from '@angular/core';
import { Chart, ChartData, ChartOptions, ChartType, registerables } from 'chart.js';

Chart.register(...registerables);

// Tokens de `tailwind.config.js` (fase 04), no los valores por defecto de
// Chart.js: texto en `neutro-700`, rejilla en `neutro-200`, tipografía `Inter`.
Chart.defaults.color = '#334155';
Chart.defaults.borderColor = '#e2e8f0';
Chart.defaults.font.family = "'Inter', ui-sans-serif, system-ui, sans-serif";
// Especificaciones de marca de la skill `dataviz`: barras finas con esquina
// redondeada solo en el extremo del dato, líneas de 2px, marcadores >= 8px.
Chart.defaults.elements.bar.borderRadius = 4;
Chart.defaults.elements.bar.borderSkipped = 'bottom' as const;
Chart.defaults.elements.line.borderWidth = 2;
Chart.defaults.elements.point.radius = 4;
Chart.defaults.elements.point.hoverRadius = 6;
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.boxHeight = 12;

/**
 * Único componente que importa `chart.js` (fase 10 §10.2): envuelve un
 * `<canvas>` con su tabla de datos equivalente, oculta visualmente pero
 * accesible a lector de pantalla, y destruye/recrea la instancia cada vez
 * que cambian `tipo`, `datos` u `opciones` para no dejar fugas ni gráficos
 * a medio actualizar.
 */
@Component({
  selector: 'app-grafico',
  templateUrl: './grafico.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Grafico implements AfterViewInit, OnDestroy {
  readonly tipo = input.required<ChartType>();
  readonly datos = input.required<ChartData>();
  readonly opciones = input<ChartOptions>({});
  /** Descripción del gráfico para `aria-label` y para el título de la
   * tabla equivalente: la información nunca depende solo del `<canvas>`. */
  readonly etiqueta = input.required<string>();
  readonly columnasTabla = input<string[]>([]);
  readonly filasTabla = input<readonly (readonly (string | number)[])[]>([]);
  readonly aspectRatio = input('16 / 9');

  private readonly lienzo = viewChild<ElementRef<HTMLCanvasElement>>('lienzo');
  private instancia: Chart | null = null;
  private vistaLista = false;

  constructor() {
    effect(() => {
      // Se suscribe a `tipo`/`datos`/`opciones` leyéndolos dentro de
      // `redibujar`; se vuelve a ejecutar cada vez que cualquiera cambia.
      this.redibujar();
    });
  }

  ngAfterViewInit(): void {
    this.vistaLista = true;
    this.redibujar();
  }

  ngOnDestroy(): void {
    this.instancia?.destroy();
    this.instancia = null;
  }

  private redibujar(): void {
    const tipo = this.tipo();
    const datos = this.datos();
    const opciones = this.opciones();
    if (!this.vistaLista) return;
    const lienzo = this.lienzo()?.nativeElement;
    if (!lienzo) return;

    this.instancia?.destroy();
    this.instancia = new Chart(lienzo, {
      type: tipo,
      data: datos,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        ...opciones,
      },
    });
  }
}
