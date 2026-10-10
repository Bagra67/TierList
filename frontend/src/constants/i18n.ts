// Langues de l'interface : ajouter une langue demande aussi son fichier dans src/i18n/locales/
export const SUPPORTED_LANGUAGES = ['fr', 'en'] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

// Langue utilisée quand ni le choix mémorisé ni le navigateur n'indiquent une langue gérée
export const DEFAULT_LANGUAGE: Language = 'fr';

// Choix fait avec le sélecteur de langue (localStorage)
export const LANGUAGE_STORAGE_KEY = 'tierlist.language';

// Formateur i18next qui affiche en Mo une taille reçue en octets : {{max_bytes, megabytes}}
export const MEGABYTES_FORMAT = 'megabytes';
export const BYTES_PER_MEGABYTE = 1024 * 1024;

// Nom de chaque langue dans cette langue : il ne se traduit pas
export const LANGUAGE_NAMES: Readonly<Record<Language, string>> = {
  fr: 'Français',
  en: 'English',
};
