import { cn } from 'cn';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { useTemplates } from '../api/templates';
import { CreateRoomButton } from '../components/CreateRoomButton';
import { CreateTemplateDialog } from '../components/CreateTemplateDialog';
import { DeleteTemplateDialog } from '../components/DeleteTemplateDialog';
import { EmptyState } from '../components/EmptyState';
import { ErrorMessage } from '../components/ErrorMessage';
import { templateEditorPath } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { panelVariants } from '../components/ui/panel';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { PageContainer } from '../components/PageContainer';
import { CONTENT_COLUMN_CLASS } from '../constants/layout';

// Templates de l'utilisateur (US-1.5) : création (US-1.1), suppression (US-1.6) et création
// d'une salle pour jouer avec (US-2.1)
export function TemplatesPage() {
  const { data: templates, isPending, isError, error } = useTemplates();
  const { t } = useTranslation();

  return (
    <PageContainer width="app">
      <div className={cn(CONTENT_COLUMN_CLASS, 'flex flex-col items-start gap-6')}>
        <div className="flex w-full flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold">{t('templates.title')}</h1>
          <CreateTemplateDialog />
        </div>
        {isPending && <LoadingSkeleton shape="list" />}
        {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
        {templates?.length === 0 && <EmptyState message={t('templates.empty')} />}
        {templates !== undefined && templates.length > 0 && (
          <ul className={panelVariants({ variant: 'list' })}>
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
                <div className="flex items-start gap-2">
                  <CreateRoomButton templateId={template.id} templateName={template.name} />
                  <DeleteTemplateDialog template={template} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </PageContainer>
  );
}
