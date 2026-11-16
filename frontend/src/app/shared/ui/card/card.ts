import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  host: { class: 'block h-full' },
  selector: 'app-card',
  templateUrl: './card.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Card {
  readonly titulo = input('');
}
