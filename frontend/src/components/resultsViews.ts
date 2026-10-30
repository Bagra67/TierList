import type { GameItem } from '../api/rooms';

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

// Un item des résultats, avec le nom de son image quand il n'a pas de texte : numéroté dans
// l'ordre du template, pour que deux items sans texte ne portent pas le même nom
export interface ResultItem {
  item: GameItem;
  imageLabel: string;
}

export type ResultItems = ReadonlyMap<string, ResultItem>;

// L'élément dont le panneau des votes est ouvert, partagé par les vues : cliquer une tuile le choisit
export interface ItemSelection {
  selectedItemId: string | null;
  onSelect: (itemId: string) => void;
}
