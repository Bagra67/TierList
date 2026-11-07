import { useTranslation } from 'react-i18next';

import { useRemovedTemplates } from '../api/templates';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { panelVariants } from './ui/panel';

export function RemovedTemplates() {
  const { data: removedTemplates, isError, error } = useRemovedTemplates();
  const { t } = useTranslation();

  if (isError) {
    return <ErrorMessage>{translateError(t, error)}</ErrorMessage>;
  }
  if (removedTemplates === undefined || removedTemplates.length === 0) {
    return null;
  }
  return (
    <section className="flex w-full flex-col gap-3">
      <h2 className="text-lg font-semibold">{t('templates.removed.title')}</h2>
      <ul className={panelVariants({ variant: 'list' })}>
        {removedTemplates.map((template) => (
          <li key={template.id} className="flex flex-col gap-1 px-4 py-3">
            <span className="font-medium break-words">{template.name}</span>
            <span className="text-sm text-muted-foreground">
              {t('templates.removed.date', { date: new Date(template.removed_at) })}
            </span>
            <span className="text-sm break-words">
              {t('templates.hidden.reason', { reason: template.reason })}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
