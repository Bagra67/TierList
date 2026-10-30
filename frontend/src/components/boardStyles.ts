import type { CSSProperties } from 'react';

import { readableTextColor } from '../theme/contrast';

// Styles communs au plateau des tours, au cooldown et aux résultats

// Puce d'un item, la même partout : plateau, cooldown et résultats
export const ITEM_CHIP_CLASS: string =
  'flex min-h-14 items-center rounded-md border bg-card p-1 sm:min-h-16';

// Bordure d'accent de l'élément à placer maintenant (tour en cours), sur sa puce et son aperçu
export const EMPHASIZED_BORDER_CLASS: string = 'border-2 border-primary';

// Carte de l'élément en cours, posée de biais comme une carte de jeu (sous motion-safe) ; sur le
// plateau, c'est aussi elle qu'on glisse. Sans bordure ici : la carte glissable prend la bordure
// d'accent, la carte posée la sienne. L'ombre « projecteur » reste réservée à ce qu'on déplace
export const CURRENT_CARD_CLASS: string =
  'flex w-full max-w-56 flex-col items-center justify-center gap-2 rounded-panel bg-card p-3 shadow-md motion-safe:-rotate-2';

// Dans la colonne de 12rem du plateau, la carte en prend toute la largeur
export const CURRENT_CARD_IN_BOARD_CLASS: string = 'lg:max-w-none';

// Colonne de gauche d'une ligne de tier (bloc-lettre, ou ligne « en plus » des résultats)
export const TIER_LABEL_CLASS: string =
  'flex min-h-14 w-16 shrink-0 items-center justify-center self-stretch px-1 text-center sm:min-h-16 sm:w-20';

// Fond d'un tier et texte lisible dessus (encre ou blanc, selon la couleur choisie)
export function tierColorStyle(color: string): CSSProperties {
  return { backgroundColor: color, color: readableTextColor(color) };
}
