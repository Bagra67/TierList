import type { CSSProperties } from 'react';

import { readableTextColor } from '../theme/contrast';

// Styles communs au plateau des tours, au cooldown et aux résultats

// Puce d'un item, la même partout : plateau, cooldown et résultats
export const ITEM_CHIP_CLASS: string =
  'flex min-h-14 items-center rounded-md border bg-card p-1 sm:min-h-16';

// Colonne de gauche d'une ligne de tier (bloc-lettre, ou ligne « en plus » des résultats)
export const TIER_LABEL_CLASS: string =
  'flex min-h-14 w-16 shrink-0 items-center justify-center self-stretch px-1 text-center sm:min-h-16 sm:w-20';

// Fond d'un tier et texte lisible dessus (encre ou blanc, selon la couleur choisie)
export function tierColorStyle(color: string): CSSProperties {
  return { backgroundColor: color, color: readableTextColor(color) };
}
