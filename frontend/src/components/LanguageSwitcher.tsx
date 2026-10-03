import { useId, type ChangeEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES } from '../constants/i18n';
import { changeLanguage, isSupportedLanguage } from '../i18n';

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
    <p>
      <label htmlFor={id}>{t('common.language')}</label>{' '}
      <select id={id} value={i18n.resolvedLanguage} onChange={handleChange}>
        {SUPPORTED_LANGUAGES.map((language) => (
          // lang : chaque nom de langue est lu dans sa propre langue par les lecteurs d'écran
          <option key={language} value={language} lang={language}>
            {LANGUAGE_NAMES[language]}
          </option>
        ))}
      </select>
    </p>
  );
}
