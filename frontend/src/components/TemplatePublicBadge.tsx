import { useTranslation } from 'react-i18next';

export function TemplatePublicBadge() {
  const { t } = useTranslation();
  return (
    <span className="shrink-0 rounded-md bg-secondary px-2 py-1 text-xs font-semibold text-secondary-foreground">
      {t('templates.visibility.badge')}
    </span>
  );
}
