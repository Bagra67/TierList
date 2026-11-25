import { useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { type Template, type TemplateChange, useSetForksAllowed } from '../api/templates';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';

export function TemplateForksField({ template }: { template: Template }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const forksMutation: TemplateChange<boolean> = useSetForksAllowed(template.id);
  const helpId: string = useId();
  return (
    <div className="flex flex-col gap-1">
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          checked={template.forks_allowed}
          aria-describedby={helpId}
          onChange={(event) => forksMutation.mutate(event.target.checked)}
          className="mt-0.5 size-4 shrink-0 accent-foreground"
        />
        {t('templates.forks.label')}
      </label>
      <p id={helpId} className="pl-6 text-sm text-muted-foreground">
        {template.forks_allowed ? t('templates.forks.allowed') : t('templates.forks.notAllowed')}
      </p>
      {forksMutation.isError && (
        <ErrorMessage>{translateError(t, forksMutation.error)}</ErrorMessage>
      )}
    </div>
  );
}
