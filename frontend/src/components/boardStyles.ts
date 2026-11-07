import type { CSSProperties } from 'react';

import { readableTextColor } from '../theme/wcagContrast';

export const ITEM_CHIP_CLASS: string =
  'flex min-h-14 items-center rounded-md border bg-card p-1 sm:min-h-16';

export const ITEM_CHIP_IMAGE_SIZE_CLASS: string = 'size-11 sm:size-13';

export const EMPHASIZED_BORDER_CLASS: string = 'border-2 border-primary';

export const CURRENT_CARD_CLASS: string =
  'flex w-full max-w-56 flex-col items-center justify-center gap-2 rounded-panel bg-card p-3 shadow-md motion-safe:-rotate-2';

export const CURRENT_CARD_IN_BOARD_CLASS: string = 'lg:max-w-none';

export const TIER_LABEL_CLASS: string =
  'flex min-h-14 w-16 shrink-0 items-center justify-center self-stretch px-1 text-center sm:min-h-16 sm:w-20';

export function tierColorStyle(color: string): CSSProperties {
  return { backgroundColor: color, color: readableTextColor(color) };
}
