import { useTranslation } from 'react-i18next';

export function TemplateHiddenBadge() {
  const { t } = useTranslation();
  return (
    <span className="shrink-0 rounded-md border border-destructive/40 px-2 py-1 text-xs font-semibold">
      {t('templates.hidden.badge')}
    </span>
  );
}
