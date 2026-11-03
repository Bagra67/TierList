import type { TFunction } from 'i18next';

import { hasTranslation } from '../i18n/hasTranslation';
import { fr } from '../i18n/locales/fr';

export function translateGoogleError(t: TFunction, code: string): string {
  if (hasTranslation(fr.errors.google, code)) {
    return t(`errors.google.${code}`);
  }
  return t('errors.google.google_failed');
}
