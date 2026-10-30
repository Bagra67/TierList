import { cn } from 'cn';
import type { ReactNode } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { ItemSelection, ResultItem } from './resultsViews';

interface ResultItemButtonProps {
  resultItem: ResultItem;
  selection: ItemSelection;
  // true : le nom accessible dit l'action (« Voir les votes : Paprika ») ; false : il reste le nom
  // de l'item, quand le bouton nomme aussi autre chose (en-tête de ligne du tableau) et l'action
  // passe dans l'infobulle
  labelled: boolean;
  // Forme et survol selon la vue (puce, cellule du tableau)
  className?: string;
  children: ReactNode;
}

// Un item des résultats qu'on clique pour voir ses votes (ItemVotesPanel) ; aria-current désigne
// celui affiché, un seul à la fois
export function ResultItemButton({
  resultItem,
  selection,
  labelled,
  className,
  children,
}: ResultItemButtonProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const itemId: string = resultItem.item.id;
  const selected: boolean = selection.selectedItemId === itemId;
  const action: string = t('results.votes.open', { item: resultItem.name });
  return (
    <button
      type="button"
      aria-current={selected ? 'true' : undefined}
      aria-label={labelled ? action : undefined}
      title={labelled ? undefined : action}
      onClick={() => selection.onSelect(itemId)}
      className={cn(
        'cursor-pointer text-left outline-none',
        // Choisi : l'anneau de l'accent reste, et le focus s'y ajoute par un décalage
        selected
          ? 'ring-3 ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background'
          : 'focus-visible:ring-3 focus-visible:ring-ring',
        className,
      )}
    >
      {children}
    </button>
  );
}
