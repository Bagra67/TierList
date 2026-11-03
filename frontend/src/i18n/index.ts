import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';

import {
  BYTES_PER_MEGABYTE,
  DEFAULT_LANGUAGE,
  LANGUAGE_STORAGE_KEY,
  MEGABYTES_FORMAT,
  SUPPORTED_LANGUAGES,
  type Language,
} from '../constants/i18n';
import { en } from './locales/en';
import { fr, type Translation } from './locales/fr';

export function isSupportedLanguage(value: unknown): value is Language {
  return SUPPORTED_LANGUAGES.includes(value as Language);
}

function readStoredLanguage(): string | null {
  try {
    return localStorage.getItem(LANGUAGE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeLanguage(language: Language): void {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    return;
  }
}

export function detectLanguage(): Language {
  const stored = readStoredLanguage();
  if (isSupportedLanguage(stored)) return stored;
  for (const tag of navigator.languages) {
    const base = tag.toLowerCase().split('-')[0];
    if (isSupportedLanguage(base)) return base;
  }
  return DEFAULT_LANGUAGE;
}

export function currentLanguage(): Language {
  const language = i18next.resolvedLanguage;
  return isSupportedLanguage(language) ? language : DEFAULT_LANGUAGE;
}

export async function changeLanguage(language: Language): Promise<void> {
  await i18next.changeLanguage(language);
  storeLanguage(language);
}

i18next.on('languageChanged', (language) => {
  document.documentElement.lang = language;
});

const resources: Record<Language, { translation: Translation }> = {
  fr: { translation: fr },
  en: { translation: en },
};

void i18next.use(initReactI18next).init({
  resources,
  lng: detectLanguage(),
  fallbackLng: DEFAULT_LANGUAGE,
  supportedLngs: [...SUPPORTED_LANGUAGES],
  initAsync: false,
  interpolation: { escapeValue: false },
});

i18next.services.formatter?.add(MEGABYTES_FORMAT, (value: number, language: string | undefined) =>
  new Intl.NumberFormat(language, {
    style: 'unit',
    unit: 'megabyte',
    maximumFractionDigits: 1,
  }).format(value / BYTES_PER_MEGABYTE),
);

export default i18next;
