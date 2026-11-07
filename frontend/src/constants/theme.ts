export const THEMES = ['system', 'light', 'dark'] as const;
export type Theme = (typeof THEMES)[number];

export const DEFAULT_THEME: Theme = 'system';

export const THEME_STORAGE_KEY = 'tierlist.theme';

export const DARK_CLASS = 'dark';

export const DARK_MEDIA_QUERY = '(prefers-color-scheme: dark)';

export const THEME_COLORS = { light: '#F4F5FA', dark: '#140F2B' } as const;

export const THEME_COLOR_META_SELECTOR = 'meta[name="theme-color"]';
