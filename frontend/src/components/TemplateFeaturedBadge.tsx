import { Star } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export function TemplateFeaturedBadge() {
  const { t } = useTranslation();
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-md bg-secondary px-2 py-1 text-xs font-semibold text-secondary-foreground">
      <Star aria-hidden="true" className="size-3 fill-current" />
      {t('officialTemplates.featuredBadge')}
    </span>
  );
}
