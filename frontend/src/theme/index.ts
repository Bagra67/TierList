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

// localStorage peut être indisponible (navigation privée, stockage bloqué) : le choix de
// thème n'est alors simplement pas mémorisé.
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
    // choix non mémorisé, le thème change quand même pour cette visite
  }
}

// Choix mémorisé, sinon le thème par défaut
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
  // index.html a une balise par thème du système, pour le premier affichage ; ensuite, la barre
  // du navigateur suit le thème choisi dans l'application : les deux reçoivent sa couleur
  const color: string = dark ? THEME_COLORS.dark : THEME_COLORS.light;
  document
    .querySelectorAll<HTMLMetaElement>(THEME_COLOR_META_SELECTOR)
    .forEach((meta: HTMLMetaElement) => {
      meta.content = color;
    });
}

// Choix de l'utilisateur (sélecteur de thème) : appliqué puis mémorisé
export function changeTheme(theme: Theme): void {
  applyTheme(theme);
  storeTheme(theme);
}

// En mode « system », la page suit en direct un changement de thème du système d'exploitation
window.matchMedia(DARK_MEDIA_QUERY).addEventListener('change', () => {
  const theme = getTheme();
  if (theme === 'system') applyTheme(theme);
});

applyTheme(getTheme());
