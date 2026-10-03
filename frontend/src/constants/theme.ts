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
