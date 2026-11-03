import { afterEach, describe, expect, it, vi } from 'vitest';

import { LANGUAGE_STORAGE_KEY } from '../constants/i18n';
import i18n, { changeLanguage, detectLanguage } from '.';
import { en } from './locales/en';
import { fr } from './locales/fr';

function translationTextsByKeyPath(tree: object, prefix = ''): [string, unknown][] {
  return Object.entries(tree).flatMap(([key, value]): [string, unknown][] =>
    typeof value === 'object' && value !== null
      ? translationTextsByKeyPath(value as object, `${prefix}${key}.`)
      : [[`${prefix}${key}`, value]],
  );
}

const keyPaths = (tree: object) => translationTextsByKeyPath(tree).map(([path]) => path);

function stubBrowserLanguages(languages: string[]) {
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(languages);
}

describe('translations', () => {
  it('have exactly the same keys in every language', () => {
    expect(keyPaths(en).sort()).toEqual(keyPaths(fr).sort());
  });

  it('have a non-empty text for every key', () => {
    for (const translation of [fr, en]) {
      const invalid = translationTextsByKeyPath(translation).filter(
        ([, text]) => typeof text !== 'string' || text.trim() === '',
      );
      expect(invalid).toEqual([]);
    }
  });
});

describe('detectLanguage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uses the browser language when it is supported', () => {
    stubBrowserLanguages(['en-US', 'fr']);

    expect(detectLanguage()).toBe('en');
  });

  it('uses the first supported browser language', () => {
    stubBrowserLanguages(['de-DE', 'en']);

    expect(detectLanguage()).toBe('en');
  });

  it('falls back to French when no browser language is supported', () => {
    stubBrowserLanguages(['de']);

    expect(detectLanguage()).toBe('fr');
  });

  it('uses the browser language when localStorage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    stubBrowserLanguages(['en-US']);

    expect(detectLanguage()).toBe('en');
  });

  it('prefers the language chosen earlier', () => {
    stubBrowserLanguages(['en-US']);
    localStorage.setItem(LANGUAGE_STORAGE_KEY, 'fr');

    expect(detectLanguage()).toBe('fr');
  });

  it('ignores an unsupported stored value', () => {
    stubBrowserLanguages(['en-US']);
    localStorage.setItem(LANGUAGE_STORAGE_KEY, 'xx');

    expect(detectLanguage()).toBe('en');
  });
});

describe('changeLanguage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('translates, remembers the choice and sets the page language', async () => {
    await changeLanguage('en');

    expect(i18n.t('auth.login.submit')).toBe('Sign in');
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('en');
    expect(document.documentElement.lang).toBe('en');
  });

  it('still changes the language for this visit when localStorage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });

    await changeLanguage('en');

    expect(i18n.t('auth.login.submit')).toBe('Sign in');
  });

  it('interpolates values', async () => {
    await changeLanguage('en');

    expect(i18n.t('home.signedIn.title', { name: 'Alice' })).toBe('Ready for a game, Alice?');
  });
});
