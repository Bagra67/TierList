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

export function setSystemDark(dark: boolean): void {
  systemDark = dark;
  listeners.forEach((listener) => listener());
}

export function resetSystemTheme(): void {
  systemDark = false;
}
