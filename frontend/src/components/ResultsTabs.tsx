import { type KeyboardEvent, useRef } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { cn } from 'cn';

import { RESULTS_VIEWS, type ResultsView, resultsPanelId, resultsTabId } from './resultsViews';

interface ResultsTabsProps {
  selected: ResultsView;
  onSelect: (view: ResultsView) => void;
}

// Onglets des vues (motif ARIA tabs) : un seul onglet dans l'ordre de tabulation, les flèches,
// Début et Fin passent d'un onglet à l'autre et l'activent
export function ResultsTabs({ selected, onSelect }: ResultsTabsProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const tabRefs = useRef<Map<ResultsView, HTMLButtonElement>>(new Map());

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const index: number = RESULTS_VIEWS.indexOf(selected);
    const last: number = RESULTS_VIEWS.length - 1;
    const targets: Record<string, number> = {
      ArrowRight: index === last ? 0 : index + 1,
      ArrowLeft: index === 0 ? last : index - 1,
      Home: 0,
      End: last,
    };
    const target: number | undefined = targets[event.key];
    if (target === undefined) return;
    event.preventDefault();
    const view: ResultsView = RESULTS_VIEWS[target];
    onSelect(view);
    tabRefs.current.get(view)?.focus();
  }

  return (
    <div role="tablist" aria-label={t('results.tabsLabel')} className="flex w-full gap-1 border-b">
      {RESULTS_VIEWS.map((view: ResultsView) => (
        <button
          key={view}
          ref={(element: HTMLButtonElement | null) => {
            if (element === null) tabRefs.current.delete(view);
            else tabRefs.current.set(view, element);
          }}
          type="button"
          role="tab"
          id={resultsTabId(view)}
          aria-selected={view === selected}
          aria-controls={resultsPanelId(view)}
          tabIndex={view === selected ? 0 : -1}
          onClick={() => onSelect(view)}
          onKeyDown={handleKeyDown}
          className={cn(
            '-mb-px border-b-2 px-3 py-2 text-sm font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
            view === selected
              ? 'border-primary text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground',
          )}
        >
          {t(`results.tabs.${view}`)}
        </button>
      ))}
    </div>
  );
}
