import { afterEach, describe, expect, it, vi } from 'vitest';

import { DARK_CLASS, THEME_COLORS, THEME_STORAGE_KEY } from '../constants/theme';
import { setSystemDark } from '../test/matchMedia';
import { readRepositoryFile } from '../test/repositoryFile';
import { applyTheme, changeTheme, getTheme } from '.';

const indexHtml: string = readRepositoryFile('frontend/index.html');
const indexCss: string = readRepositoryFile('frontend/src/index.css');

const LIGHT_BACKGROUND_RULE: RegExp =
  /^:root \{[^}]*?--background: oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)/m;
const DARK_BACKGROUND_RULE: RegExp =
  /^\.dark \{[^}]*?--background: oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)/m;

function isDark(): boolean {
  return document.documentElement.classList.contains(DARK_CLASS);
}

function metaThemeColor(colorScheme: 'light' | 'dark'): string | undefined {
  const metaTag: RegExp = new RegExp(
    `name="theme-color" content="([^"]*)" media="\\(prefers-color-scheme: ${colorScheme}\\)"`,
  );
  return indexHtml.match(metaTag)?.[1];
}

function srgbByte(linearChannel: number): string {
  const clamped: number = Math.min(1, Math.max(0, linearChannel));
  const encoded: number =
    clamped <= 0.0031308 ? 12.92 * clamped : 1.055 * clamped ** (1 / 2.4) - 0.055;
  return Math.round(encoded * 255)
    .toString(16)
    .padStart(2, '0')
    .toUpperCase();
}

function oklchToHex(lightness: number, chroma: number, hueDegrees: number): string {
  const hue: number = (hueDegrees * Math.PI) / 180;
  const a: number = chroma * Math.cos(hue);
  const b: number = chroma * Math.sin(hue);
  const l: number = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m: number = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s: number = (lightness - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const red: string = srgbByte(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s);
  const green: string = srgbByte(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s);
  const blue: string = srgbByte(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s);
  return `#${red}${green}${blue}`;
}

function cssBackgroundAsHex(backgroundRule: RegExp): string {
  const declaration: RegExpMatchArray | null = indexCss.match(backgroundRule);
  if (declaration === null) throw new Error('No --background in index.css');
  return oklchToHex(Number(declaration[1]), Number(declaration[2]), Number(declaration[3]));
}

describe('theme', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('follows the system theme in system mode, live', () => {
    applyTheme('system');
    expect(isDark()).toBe(false);

    setSystemDark(true);
    expect(isDark()).toBe(true);

    setSystemDark(false);
    expect(isDark()).toBe(false);
  });

  it('ignores the system theme once a theme is chosen', () => {
    changeTheme('light');

    setSystemDark(true);

    expect(isDark()).toBe(false);
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');
  });

  it('gives the browser bar the color of the chosen theme', () => {
    const lightSystemMeta: HTMLMetaElement = document.createElement('meta');
    lightSystemMeta.name = 'theme-color';
    lightSystemMeta.media = '(prefers-color-scheme: light)';
    document.head.append(lightSystemMeta);

    changeTheme('dark');
    expect(lightSystemMeta.content).toBe(THEME_COLORS.dark);

    changeTheme('light');
    expect(lightSystemMeta.content).toBe(THEME_COLORS.light);

    lightSystemMeta.remove();
  });

  it('stores the choice under the key read by the early script of index.html', () => {
    expect(indexHtml).toContain(`localStorage.getItem('${THEME_STORAGE_KEY}')`);
  });

  it('gives the browser bar the colors of the meta tags of index.html', () => {
    expect(metaThemeColor('light')).toBe(THEME_COLORS.light);
    expect(metaThemeColor('dark')).toBe(THEME_COLORS.dark);
  });

  it('gives the browser bar the background color of each theme of index.css', () => {
    expect(cssBackgroundAsHex(LIGHT_BACKGROUND_RULE)).toBe(THEME_COLORS.light);
    expect(cssBackgroundAsHex(DARK_BACKGROUND_RULE)).toBe(THEME_COLORS.dark);
  });

  it('falls back to the system theme for an unknown stored value', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'purple');

    expect(getTheme()).toBe('system');
  });

  it('still applies the theme when localStorage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });

    changeTheme('dark');

    expect(isDark()).toBe(true);
    expect(getTheme()).toBe('system');
  });
});
