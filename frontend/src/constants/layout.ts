export const PAGE_WIDTH_CLASS = {
  app: 'max-w-6xl',
  reading: 'max-w-3xl',
  form: 'max-w-sm',
} as const;

export type PageWidth = keyof typeof PAGE_WIDTH_CLASS;

export const CONTENT_COLUMN_CLASS = 'w-full max-w-2xl';
