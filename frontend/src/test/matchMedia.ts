// Faux window.matchMedia (absent de jsdom) : simule le thème clair / sombre du système.
// Seule la requête prefers-color-scheme: dark est utilisée par l'application.
type Listener = () => void;

const listeners = new Set<Listener>();
let systemDark = false;

export function installMatchMedia(): void {
  window.matchMedia = (query: string) =>
    ({
      get matches() {
        return systemDark;
      },
      media: query,
      onchange: null,
      addEventListener: (_type: string, listener: Listener) => listeners.add(listener),
      removeEventListener: (_type: string, listener: Listener) => listeners.delete(listener),
      dispatchEvent: () => true,
    }) as unknown as MediaQueryList;
}

// Change le thème du système et prévient les écouteurs, comme le navigateur
export function setSystemDark(dark: boolean): void {
  systemDark = dark;
  listeners.forEach((listener) => listener());
}

// Retour au thème clair entre deux tests, sans prévenir les écouteurs
export function resetSystemTheme(): void {
  systemDark = false;
}
