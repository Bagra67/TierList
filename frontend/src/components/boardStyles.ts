import type { CSSProperties } from 'react';

import { readableTextColor } from '../theme/contrast';

// Styles communs au plateau des tours, au cooldown et aux résultats

// Puce d'un item, la même partout : plateau, cooldown et résultats
export const ITEM_CHIP_CLASS: string =
  'flex min-h-14 items-center rounded-md border bg-card p-1 sm:min-h-16';

// Fond d'un tier et texte lisible dessus (encre ou blanc, selon la couleur choisie)
export function tierColorStyle(color: string): CSSProperties {
  return { backgroundColor: color, color: readableTextColor(color) };
}
