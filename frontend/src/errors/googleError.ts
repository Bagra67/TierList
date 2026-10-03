import type { TFunction } from 'i18next';

import { hasTranslation } from '../i18n/hasTranslation';
import { fr } from '../i18n/locales/fr';

// Message du retour de Google (backend : /auth/google/callback → /login?error=<code>) ;
// un code inconnu est présenté comme un échec.
export function translateGoogleError(t: TFunction, code: string): string {
  if (hasTranslation(fr.errors.google, code)) {
    return t(`errors.google.${code}`);
  }
  return t('errors.google.google_failed');
}
