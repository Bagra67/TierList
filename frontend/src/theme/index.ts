import {
  DARK_CLASS,
  DARK_MEDIA_QUERY,
  DEFAULT_THEME,
  THEME_COLOR_META_SELECTOR,
  THEME_COLORS,
  THEME_STORAGE_KEY,
  THEMES,
  type Theme,
} from '../constants/theme';

export function isTheme(value: unknown): value is Theme {
  return THEMES.includes(value as Theme);
}

function readStoredTheme(): string | null {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    return;
  }
}

export function getTheme(): Theme {
  const stored = readStoredTheme();
  return isTheme(stored) ? stored : DEFAULT_THEME;
}

function prefersDark(): boolean {
  return window.matchMedia(DARK_MEDIA_QUERY).matches;
}

export function applyTheme(theme: Theme): void {
  const dark = theme === 'dark' || (theme === 'system' && prefersDark());
  document.documentElement.classList.toggle(DARK_CLASS, dark);
  const color: string = dark ? THEME_COLORS.dark : THEME_COLORS.light;
  document
    .querySelectorAll<HTMLMetaElement>(THEME_COLOR_META_SELECTOR)
    .forEach((meta: HTMLMetaElement) => {
      meta.content = color;
    });
}

export function changeTheme(theme: Theme): void {
  applyTheme(theme);
  storeTheme(theme);
}

window.matchMedia(DARK_MEDIA_QUERY).addEventListener('change', () => {
  const theme = getTheme();
  if (theme === 'system') applyTheme(theme);
});

applyTheme(getTheme());
