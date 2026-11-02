import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { HorasPipe } from '../../../shared/pipes';
import { Badge } from '../../../shared/ui/badge/badge';
import { Boton } from '../../../shared/ui/boton/boton';
import { Progreso } from '../../../shared/ui/progreso/progreso';
import { NodoArbolTarea } from '../../tareas/data/tareas.model';

/** Fila recursiva del árbol de tareas (pestaña Tareas del proyecto): se
 * referencia a sí misma en `imports` para pintar cada nivel de subtareas
 * sin un `ngTemplateOutlet` manual. Los manejadores de clic se reciben
 * como funciones (no `@Output`) para no tener que reemitirlos en cada
 * nivel de la recursión hasta llegar al componente de la pestaña. */
@Component({
  selector: 'app-nodo-arbol-tarea',
  templateUrl: './nodo-arbol-tarea.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Badge, Progreso, Boton, HorasPipe, NodoArbolTareaFila],
})
export class NodoArbolTareaFila {
  readonly nodo = input.required<NodoArbolTarea>();
  readonly nivel = input(0);
  readonly estaExpandido = input.required<(id: string) => boolean>();
  readonly alAlternar = input.required<(id: string) => void>();
  readonly alCrearSubtarea = input.required<(padreId: string) => void>();
  readonly alEditar = input.required<(id: string) => void>();

  protected numero(valor: string): number {
    return Number(valor);
  }
}
