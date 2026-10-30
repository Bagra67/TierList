import { TIER_COLOR_PRESETS } from './templates';

// Plateau d'exemple de la page d'accueil (components/home/HomeBoard.tsx) : quatre tiers aux
// couleurs par défaut, des éléments (textes dans home.board.items.*) et, sur certains, les
// initiales des joueurs qui les ont mis là. Les éléments apparaissent dans l'ordre de la liste

type HomeBoardItemKey =
  'pizza' | 'crepes' | 'sushi' | 'tacos' | 'ramen' | 'croissant' | 'burger' | 'salad';

export interface HomeBoardItem {
  key: HomeBoardItemKey;
  // Initiales des joueurs qui ont placé l'élément dans ce tier
  voters: readonly string[];
}

export interface HomeBoardRow {
  tier: string;
  color: string;
  items: readonly HomeBoardItem[];
}

export const HOME_BOARD: readonly HomeBoardRow[] = [
  {
    tier: 'S',
    color: TIER_COLOR_PRESETS[0],
    items: [
      { key: 'pizza', voters: ['A', 'B', 'C'] },
      { key: 'crepes', voters: [] },
    ],
  },
  {
    tier: 'A',
    color: TIER_COLOR_PRESETS[1],
    items: [
      { key: 'sushi', voters: ['A', 'C'] },
      { key: 'tacos', voters: [] },
      { key: 'ramen', voters: [] },
    ],
  },
  {
    tier: 'B',
    color: TIER_COLOR_PRESETS[2],
    items: [
      { key: 'croissant', voters: [] },
      { key: 'burger', voters: ['B'] },
    ],
  },
  { tier: 'C', color: TIER_COLOR_PRESETS[3], items: [{ key: 'salad', voters: [] }] },
];

// Couleur de la pastille de chaque joueur (initiale), prise dans la fin de la rampe des tiers
export const HOME_BOARD_PLAYER_COLORS: Readonly<Record<string, string>> = {
  A: TIER_COLOR_PRESETS[4],
  B: TIER_COLOR_PRESETS[5],
  C: TIER_COLOR_PRESETS[2],
};

// Rythme du plateau, en millisecondes : écart entre l'apparition de deux éléments, et durée de
// l'apparition d'un élément (plus lente que la révélation des résultats, 420 ms)
export const HOME_BOARD_STEP_MS: number = 240;
export const HOME_BOARD_ITEM_MS: number = 630;

// Nombre de modèles et de parties récents montrés à un joueur connecté
export const HOME_RECENT_COUNT: number = 3;
