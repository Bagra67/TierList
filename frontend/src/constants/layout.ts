export const PAGE_WIDTH_CLASS = {
  app: 'max-w-6xl',
  reading: 'max-w-3xl',
  form: 'max-w-sm',
} as const;

export type PageWidth = keyof typeof PAGE_WIDTH_CLASS;

export const CONTENT_COLUMN_CLASS = 'w-full max-w-2xl';

export const FOCUS_RING_ROOM_IN_SCROLL_AREA_CLASS = 'lg:p-1';

export const FILL_HEIGHT_UNDER_HEADER_ON_LARGE_SCREEN_CLASS = 'lg:min-h-0 lg:flex-1';

export const EDITOR_COLUMNS_FITTING_FULL_TIER_ROW_CLASS = 'lg:grid-cols-[22rem_minmax(0,1fr)]';
