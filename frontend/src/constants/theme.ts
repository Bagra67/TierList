// Préférences de thème : « system » suit le réglage clair / sombre du système d'exploitation
export const THEMES = ['system', 'light', 'dark'] as const;
export type Theme = (typeof THEMES)[number];

export const DEFAULT_THEME: Theme = 'system';

// Choix fait avec le sélecteur de thème (localStorage). Repris tel quel par le script de
// index.html, qui applique le thème avant le chargement de l'application : garder les deux égaux.
export const THEME_STORAGE_KEY = 'tierlist.theme';

// Classe posée sur <html> : active les couleurs du bloc .dark de index.css et les classes dark:
export const DARK_CLASS = 'dark';

export const DARK_MEDIA_QUERY = '(prefers-color-scheme: dark)';

// Couleur de la barre du navigateur mobile (balises meta theme-color de index.html) : le
// --background de chaque thème de index.css, garder les trois égaux
export const THEME_COLORS = { light: '#F4F5FA', dark: '#140F2B' } as const;

export const THEME_COLOR_META_SELECTOR = 'meta[name="theme-color"]';
