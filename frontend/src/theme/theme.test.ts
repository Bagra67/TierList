import { afterEach, describe, expect, it, vi } from 'vitest';

import { DARK_CLASS, THEME_STORAGE_KEY } from '../constants/theme';
import { setSystemDark } from '../test/matchMedia';
import { applyTheme, changeTheme, getTheme } from '.';

function isDark(): boolean {
  return document.documentElement.classList.contains(DARK_CLASS);
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
