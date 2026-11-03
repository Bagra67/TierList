export const SUPPORTED_LANGUAGES = ['fr', 'en'] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_LANGUAGE: Language = 'fr';

export const LANGUAGE_STORAGE_KEY = 'tierlist.language';

export const MEGABYTES_FORMAT = 'megabytes';
export const BYTES_PER_MEGABYTE = 1024 * 1024;

export const LANGUAGE_ENDONYMS: Readonly<Record<Language, string>> = {
  fr: 'Français',
  en: 'English',
};
