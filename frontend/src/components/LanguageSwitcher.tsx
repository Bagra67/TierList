import { useId, type ChangeEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES } from '../constants/i18n';
import { changeLanguage, isSupportedLanguage } from '../i18n';
import { Label } from './ui/label';

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const id = useId();

  function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    const language = event.target.value;
    if (isSupportedLanguage(language)) {
      void changeLanguage(language);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Label htmlFor={id}>{t('common.language')}</Label>
      <select
        id={id}
        value={i18n.resolvedLanguage}
        onChange={handleChange}
        className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {SUPPORTED_LANGUAGES.map((language) => (
          // lang : chaque nom de langue est lu dans sa propre langue par les lecteurs d'écran
          <option key={language} value={language} lang={language}>
            {LANGUAGE_NAMES[language]}
          </option>
        ))}
      </select>
    </div>
  );
}
