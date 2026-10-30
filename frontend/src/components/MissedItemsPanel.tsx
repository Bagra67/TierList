import { useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { GameItem } from '../api/rooms';
import { ChoosableTile } from './gameBoardParts';
import { panelVariants } from './ui/panel';

interface MissedItemsPanelProps {
  items: GameItem[];
  labelOf: (itemId: string) => string;
  chosenId: string | null;
  pending: boolean;
  onChoose: (itemId: string) => void;
}

// Les éléments manqués (votes absents, arrivée en retard), à placer avant la fin des retouches
// (US-4.6) : on les glisse dans un tier, ou on les choisit puis « Déplacer ici »
export function MissedItemsPanel({
  items,
  labelOf,
  chosenId,
  pending,
  onChoose,
}: MissedItemsPanelProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const headingId: string = useId();
  return (
    <section aria-labelledby={headingId} className={panelVariants()}>
      <h3 id={headingId} className="font-semibold">
        {t('rooms.game.cooldown.missed')}
      </h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('rooms.game.cooldown.missedNone')}</p>
      ) : (
        <ul className="flex flex-wrap gap-3">
          {items.map((item) => (
            <li key={item.id} className="flex flex-col items-center gap-1">
              <ChoosableTile
                item={item}
                label={labelOf(item.id)}
                chosen={chosenId === item.id}
                pending={pending}
                onChoose={onChoose}
              />
              {/* Le mot accompagne la couleur, qui ne suffirait pas seule */}
              <span className="rounded-sm bg-destructive/10 px-1.5 text-sm font-semibold text-destructive">
                {t('rooms.game.cooldown.absent')}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
