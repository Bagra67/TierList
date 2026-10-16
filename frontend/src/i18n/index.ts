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
import { fr } from './locales/fr';

export function isSupportedLanguage(value: unknown): value is Language {
  return SUPPORTED_LANGUAGES.includes(value as Language);
}

// localStorage peut être indisponible (navigation privée, stockage bloqué) : le choix de
// langue n'est alors simplement pas mémorisé.
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
    // choix non mémorisé, la langue change quand même pour cette visite
  }
}

// Choix mémorisé, sinon la première langue gérée parmi celles du navigateur (en-US → en),
// sinon la langue par défaut.
export function detectLanguage(): Language {
  const stored = readStoredLanguage();
  if (isSupportedLanguage(stored)) return stored;
  for (const tag of navigator.languages) {
    const base = tag.toLowerCase().split('-')[0];
    if (isSupportedLanguage(base)) return base;
  }
  return DEFAULT_LANGUAGE;
}

// Langue de l'interface, transmise au backend pour rédiger les emails dans la même langue
export function currentLanguage(): Language {
  const language = i18next.resolvedLanguage;
  return isSupportedLanguage(language) ? language : DEFAULT_LANGUAGE;
}

// Choix de l'utilisateur (sélecteur de langue) : appliqué puis mémorisé
export async function changeLanguage(language: Language): Promise<void> {
  await i18next.changeLanguage(language);
  storeLanguage(language);
}

i18next.on('languageChanged', (language) => {
  // Lecteurs d'écran, césure, correcteur : la langue de la page suit celle de l'interface
  document.documentElement.lang = language;
});

void i18next.use(initReactI18next).init({
  resources: { fr: { translation: fr }, en: { translation: en } },
  lng: detectLanguage(),
  fallbackLng: DEFAULT_LANGUAGE,
  supportedLngs: [...SUPPORTED_LANGUAGES],
  // Ressources incluses dans le bundle : initialisation synchrone, sans premier rendu vide
  initAsync: false,
  // React échappe déjà les valeurs affichées
  interpolation: { escapeValue: false },
});

// Le backend envoie les tailles en octets (ex. max_bytes) : affichées en Mo, au format de la
// langue (« 10 Mo », « 10 MB »), sans recopier la limite dans les traductions
i18next.services.formatter?.add(MEGABYTES_FORMAT, (value: number, language: string | undefined) =>
  new Intl.NumberFormat(language, {
    style: 'unit',
    unit: 'megabyte',
    maximumFractionDigits: 1,
  }).format(value / BYTES_PER_MEGABYTE),
);

export default i18next;
