import { useId, useState, type ChangeEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { THEMES, type Theme } from '../constants/theme';
import { changeTheme, getTheme, isTheme } from '../theme';
import { Label } from './ui/label';

export function ThemeSwitcher() {
  const { t } = useTranslation();
  const id = useId();
  const [theme, setTheme] = useState<Theme>(getTheme);

  function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    const selected = event.target.value;
    if (isTheme(selected)) {
      changeTheme(selected);
      setTheme(selected);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Label htmlFor={id}>{t('common.theme')}</Label>
      <select
        id={id}
        value={theme}
        onChange={handleChange}
        className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {THEMES.map((option) => (
          <option key={option} value={option}>
            {t(`theme.${option}`)}
          </option>
        ))}
      </select>
    </div>
  );
}
