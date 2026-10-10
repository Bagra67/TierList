import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { useTemplates } from '../api/templates';
import { CreateTemplateDialog } from '../components/CreateTemplateDialog';
import { DeleteTemplateDialog } from '../components/DeleteTemplateDialog';
import { ErrorMessage } from '../components/ErrorMessage';
import { templateEditorPath } from '../constants/routes';
import { translateError } from '../errors/apiError';

// Templates de l'utilisateur (US-1.5) : création (US-1.1) et suppression (US-1.6)
export function TemplatesPage() {
  const { data: templates, isPending, isError, error } = useTemplates();
  const { t } = useTranslation();

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col items-start gap-6 px-4 py-10">
      <div className="flex w-full flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">{t('templates.title')}</h1>
        <CreateTemplateDialog />
      </div>
      {isPending && <p className="text-muted-foreground">{t('common.loading')}</p>}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {templates?.length === 0 && <p className="text-muted-foreground">{t('templates.empty')}</p>}
      {templates !== undefined && templates.length > 0 && (
        <ul className="flex w-full flex-col divide-y rounded-xl border">
          {templates.map((template) => (
            <li key={template.id} className="flex items-center justify-between gap-4 px-4 py-3">
              <div className="flex min-w-0 flex-col gap-1">
                <Link
                  to={templateEditorPath(template.id)}
                  className="truncate font-medium underline-offset-4 hover:underline"
                >
                  {template.name}
                </Link>
                <p className="flex flex-wrap gap-x-3 text-sm text-muted-foreground">
                  <span>{t('templates.tileCount', { count: template.tile_count })}</span>
                  <span>{t('templates.updatedAt', { date: new Date(template.updated_at) })}</span>
                </p>
              </div>
              <DeleteTemplateDialog template={template} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
