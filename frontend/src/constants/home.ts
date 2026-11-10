import { TIER_COLOR_PRESETS } from './templates';

export type HomeBoardVoter = 'A' | 'B' | 'C';

type HomeBoardItemKey =
  'pizza' | 'crepes' | 'sushi' | 'tacos' | 'ramen' | 'croissant' | 'burger' | 'salad';

export interface HomeBoardItem {
  key: HomeBoardItemKey;
  voterInitials: readonly HomeBoardVoter[];
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
      { key: 'pizza', voterInitials: ['A', 'B', 'C'] },
      { key: 'crepes', voterInitials: [] },
    ],
  },
  {
    tier: 'A',
    color: TIER_COLOR_PRESETS[1],
    items: [
      { key: 'sushi', voterInitials: ['A', 'C'] },
      { key: 'tacos', voterInitials: [] },
      { key: 'ramen', voterInitials: [] },
    ],
  },
  {
    tier: 'B',
    color: TIER_COLOR_PRESETS[2],
    items: [
      { key: 'croissant', voterInitials: [] },
      { key: 'burger', voterInitials: ['B'] },
    ],
  },
  { tier: 'C', color: TIER_COLOR_PRESETS[3], items: [{ key: 'salad', voterInitials: [] }] },
];

export const HOME_BOARD_PLAYER_COLORS: Readonly<Record<HomeBoardVoter, string>> = {
  A: TIER_COLOR_PRESETS[4],
  B: TIER_COLOR_PRESETS[5],
  C: TIER_COLOR_PRESETS[2],
};

export const HOME_BOARD_ITEM_STAGGER_MS: number = 240;
export const HOME_BOARD_ITEM_APPEAR_MS: number = 630;

export const HOME_RECENT_COUNT: number = 3;
