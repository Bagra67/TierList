import { useTranslation } from 'react-i18next';
import { cn } from 'cn';

import type { TemplateVisibility } from '../api/templates';

export function OfficialTemplateStateBadge({ visibility }: { visibility: TemplateVisibility }) {
  const { t } = useTranslation();
  const published: boolean = visibility === 'public';
  return (
    <span
      className={cn(
        'shrink-0 rounded-md px-2 py-1 text-xs font-semibold',
        published ? 'bg-secondary text-secondary-foreground' : 'border border-border',
      )}
    >
      {published ? t('officialTemplates.state.published') : t('officialTemplates.state.draft')}
    </span>
  );
}
