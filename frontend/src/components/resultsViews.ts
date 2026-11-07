import type { GameItem } from '../api/rooms';

export type ResultsView = 'median' | 'overall' | 'players';
export const RESULTS_VIEWS: readonly ResultsView[] = ['median', 'overall', 'players'];

export function resultsTabId(view: ResultsView): string {
  return `results-tab-${view}`;
}

export function resultsPanelId(view: ResultsView): string {
  return `results-panel-${view}`;
}

export interface ResultItem {
  item: GameItem;
  imageLabel: string;
  name: string;
}

export type ResultItems = ReadonlyMap<string, ResultItem>;

export interface ItemSelection {
  selectedItemId: string | null;
  onSelect: (itemId: string) => void;
}
