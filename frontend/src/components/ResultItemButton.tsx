import { cn } from 'cn';
import type { ReactNode } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { ItemSelection } from './resultsViews';

interface ResultItemButtonProps {
  itemId: string;
  // Nom lu par les lecteurs d'écran : le texte de l'item, ou le nom de son image
  name: string;
  selection: ItemSelection;
  className?: string;
  children: ReactNode;
}

// Un item des résultats qu'on clique pour voir ses votes (ItemVotesPanel) ; aria-pressed dit s'il
// est celui affiché
export function ResultItemButton({
  itemId,
  name,
  selection,
  className,
  children,
}: ResultItemButtonProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const selected: boolean = selection.selectedItemId === itemId;
  return (
    <button
      type="button"
      aria-pressed={selected}
      aria-label={t('results.votes.open', { item: name })}
      onClick={() => selection.onSelect(itemId)}
      className={cn(
        'cursor-pointer text-left outline-none hover:border-primary focus-visible:ring-3 focus-visible:ring-ring',
        selected && 'ring-3 ring-primary',
        className,
      )}
    >
      {children}
    </button>
  );
}
