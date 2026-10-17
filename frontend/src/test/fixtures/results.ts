import type { GameResults } from '../../api/results';

const S: string = '8e2f3a4b-0000-4000-8000-000000000001';
const A: string = '8e2f3a4b-0000-4000-8000-000000000002';
const PAPRIKA: string = '7c1d2e3f-0000-4000-8000-000000000001';
const CHORIZO: string = '7c1d2e3f-0000-4000-8000-000000000002';
const CURRY: string = '7c1d2e3f-0000-4000-8000-000000000003';

export const RESULTS_TOKEN: string = 'k9Xq2LmZ7rT4vB1nW8sY3a';

// Résultats d'une partie close, avec les votes absents : Alice et Lou ont joué. Paprika : Alice
// en S, Lou en A ; Chorizo : Alice en A, Lou absente ; Curry : personne
export const closedGameResults: GameResults = {
  template_name: 'Épices',
  closed_at: '2026-10-17T18:30:00Z',
  include_absent_votes: true,
  tiers: [
    { id: S, name: 'S', color: '#FF7F7F' },
    { id: A, name: 'A', color: '#FFBF7F' },
  ],
  items: [
    { id: PAPRIKA, text: 'Paprika', image_url: null },
    { id: CHORIZO, text: 'Chorizo', image_url: null },
    { id: CURRY, text: 'Curry', image_url: null },
  ],
  median_ranking: [
    { tier_id: S, item_ids: [] },
    { tier_id: A, item_ids: [PAPRIKA, CHORIZO] },
  ],
  unranked_item_ids: [CURRY],
  distribution: [
    { item_id: PAPRIKA, votes_per_tier: [1, 1], absent_count: 0, median_tier_id: A },
    { item_id: CHORIZO, votes_per_tier: [0, 1], absent_count: 1, median_tier_id: A },
    { item_id: CURRY, votes_per_tier: [0, 0], absent_count: 2, median_tier_id: null },
  ],
  players: [
    {
      display_name: 'Alice',
      tiers: [
        { tier_id: S, item_ids: [PAPRIKA] },
        { tier_id: A, item_ids: [CHORIZO] },
      ],
      unplaced_item_ids: [CURRY],
    },
    {
      display_name: 'Lou',
      tiers: [
        { tier_id: S, item_ids: [] },
        { tier_id: A, item_ids: [PAPRIKA] },
      ],
      unplaced_item_ids: [CHORIZO, CURRY],
    },
  ],
};

// Les mêmes résultats sans les votes absents : plus de colonne des absents
export const closedGameResultsWithoutAbsents: GameResults = {
  ...closedGameResults,
  include_absent_votes: false,
  distribution: closedGameResults.distribution.map((entry) => ({ ...entry, absent_count: 0 })),
};
