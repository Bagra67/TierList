import { cn } from 'cn';
import type { ReactNode } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { ItemSelection, ResultItem } from './resultsViews';

interface ResultItemButtonProps {
  resultItem: ResultItem;
  selection: ItemSelection;
  accessibleNameIsAction: boolean;
  className?: string;
  children: ReactNode;
}

export function ResultItemButton({
  resultItem,
  selection,
  accessibleNameIsAction,
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
      aria-label={accessibleNameIsAction ? action : undefined}
      title={accessibleNameIsAction ? undefined : action}
      onClick={() => selection.onSelect(itemId)}
      className={cn(
        'cursor-pointer text-left outline-none',
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
