import { useId, type ChangeEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES } from '../constants/i18n';
import { changeLanguage, isSupportedLanguage } from '../i18n';
import { Label } from './ui/label';
import { NativeSelect } from './ui/native-select';

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
      <NativeSelect id={id} value={i18n.resolvedLanguage} onChange={handleChange}>
        {SUPPORTED_LANGUAGES.map((language) => (
          <option key={language} value={language} lang={language}>
            {LANGUAGE_NAMES[language]}
          </option>
        ))}
      </NativeSelect>
    </div>
  );
}
