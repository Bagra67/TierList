import { afterEach, describe, expect, it, vi } from 'vitest';

import { LANGUAGE_STORAGE_KEY } from '../constants/i18n';
import i18n, { changeLanguage, detectLanguage } from '.';
import { en } from './locales/en';
import { fr } from './locales/fr';

// Textes de toutes les clés, par chemin : « auth.login.title » → « Connexion »…
function flatten(tree: object, prefix = ''): [string, unknown][] {
  return Object.entries(tree).flatMap(([key, value]): [string, unknown][] =>
    typeof value === 'object' && value !== null
      ? flatten(value as object, `${prefix}${key}.`)
      : [[`${prefix}${key}`, value]],
  );
}

const keyPaths = (tree: object) => flatten(tree).map(([path]) => path);

function stubBrowserLanguages(languages: string[]) {
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(languages);
}

describe('translations', () => {
  it('have exactly the same keys in every language', () => {
    expect(keyPaths(en).sort()).toEqual(keyPaths(fr).sort());
  });

  it('have a non-empty text for every key', () => {
    for (const translation of [fr, en]) {
      const invalid = flatten(translation).filter(
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
  it('translates, remembers the choice and sets the page language', async () => {
    await changeLanguage('en');

    expect(i18n.t('auth.login.submit')).toBe('Sign in');
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('en');
    expect(document.documentElement.lang).toBe('en');
  });

  it('interpolates values', async () => {
    await changeLanguage('en');

    expect(i18n.t('auth.signedInAs', { name: 'Alice' })).toBe('Signed in as Alice');
  });
});
