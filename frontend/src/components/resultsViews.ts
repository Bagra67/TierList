// Les trois vues des résultats (screens.md §8), et les identifiants qui relient chaque onglet à
// son panneau (motif ARIA tabs)
export type ResultsView = 'median' | 'overall' | 'players';
export const RESULTS_VIEWS: readonly ResultsView[] = ['median', 'overall', 'players'];

export function resultsTabId(view: ResultsView): string {
  return `results-tab-${view}`;
}

export function resultsPanelId(view: ResultsView): string {
  return `results-panel-${view}`;
}
